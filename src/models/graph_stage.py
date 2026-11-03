"""Stage 3 of the detector chain: a host-graph neural network over a sliding window.

Why a graph stage. The evasion attacks perturb each DDoS flow's own features. A flood still
needs many flows from its bots to its victim, so the *traffic pattern* around those hosts
(how many flows, to how many peers, what the neighbouring flows look like) stays. A model
that reads each flow together with that context should catch flows a per-flow detector
misses -- unless the attacker also changes the pattern (spreads over more sources, slows
down), which costs attack volume. experiments/cascade_eval.py measures both.

Design (borrowed from the FANET routing project's graph-attention policy):
  * Per-window host graph: nodes = hosts (IP addresses) seen in the last W flows, plus the
    hosts of the flows being scored; directed edges = host pairs with flows in the window.
    Node features: log-counts of outgoing / incoming flows and distinct peers, a "new host"
    flag, and the mean (scaled) feature vector of the host's outgoing and incoming flows.
    Edge features: log-count and mean feature vector of the pair's flows. No labels and no
    IP identities are ever used as features (no memorisation shortcut).
  * Encoder: node MLP, then L = 2 layers of dense multi-head attention restricted to graph
    neighbours (both directions), with edge features entering as per-head attention biases
    (one projection for the outgoing, one for the incoming edge). Graphs are small (tens to a
    few hundred hosts), so dense attention is simpler and faster than a sparse GNN library.
  * Encode once per frame (B flows), then score every flow of the frame from
    [h_src, h_dst, flow features, log pair count] -- "per-frame encode, per-decision score".
    The window ends BEFORE the frame: strictly causal.
  * Matched control (mixer="mlp"): the same node features and scorer, but the attention
    layers are replaced by per-node MLP blocks of about the same size: no message passing.
    If the control matches the GNN, the gain comes from the hand-computed host aggregates,
    not from message passing (the substitution effect seen in the FANET study).
  * Drift focus ("drifting nodes' graphs"): every host has a change detector on its activity
    per frame (its share of the frame's flows). Hosts that drifted in the last K frames (or
    are new) define the focus; only their 2-hop neighbourhood is encoded and only flows
    touching it are scored (the rest abstain). Training is the same as the full variant: the
    focus is an inference-time choice, so full vs drift isolates the effect of focusing.
    Detector: "ewma" (default) flags a host when a fast EWMA of its activity leaves a slow
    EWMA by more than 3 running standard deviations and 0.05 in absolute terms; ADWIN
    (detector="adwin", clock 1) is available but reacts 20-40 frames late on per-frame
    activity shares, measured on a 0.15 -> 0.7 step.
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np
import torch
from river import drift as rdrift
from torch import nn


class EWMADrift:
    """Fast change detector for one host's activity: fast vs slow EWMA, in running SDs."""

    def __init__(self, fast: float = 0.3, slow: float = 0.03, k: float = 3.0, floor: float = 0.05,
                 warmup: int = 5) -> None:
        self.f, self.s, self.k, self.floor, self.warm = fast, slow, k, floor, warmup
        self.mf = self.ms = None
        self.var = 0.0
        self.n = 0
        self.drift_detected = False

    def update(self, x: float) -> None:
        """Test the new value against the baseline as it was BEFORE it, then update."""
        self.n += 1
        x = float(x)
        if self.mf is None:
            self.mf = self.ms = x
            self.drift_detected = False
            return
        mf = self.mf + self.f * (x - self.mf)
        gap = abs(mf - self.ms)
        self.drift_detected = (self.n > self.warm and gap > self.floor
                               and gap > self.k * (self.var ** 0.5 + 1e-9))
        self.mf = mf
        if self.drift_detected:          # restart both averages at the new level
            self.mf = self.ms = x
            self.var = 0.0
        else:
            lim = self.k * self.var ** 0.5 + self.floor
            d = min(max(x - self.ms, -lim), lim)        # winsorised: one jump cannot inflate the SD
            self.ms += self.s * d
            self.var = (1 - self.s) * (self.var + self.s * d * d)


# ---------------------------------------------------------------------------------------
class HostGraphs:
    """Builds window graphs from stream arrays (features X, integer host codes src/dst)."""

    def __init__(self, X: np.ndarray, src: np.ndarray, dst: np.ndarray, window: int = 800) -> None:
        self.X = np.nan_to_num(np.asarray(X, dtype=np.float32), nan=0.0)
        self.src = np.asarray(src, dtype=np.int64)
        self.dst = np.asarray(dst, dtype=np.int64)
        self.W = int(window)
        self.d = self.X.shape[1]

    def build(self, start: int, query: np.ndarray) -> Dict[str, np.ndarray]:
        """Graph of rows [start - W, start) plus the hosts of the query rows."""
        lo = max(0, start - self.W)
        s, t, Xw = self.src[lo:start], self.dst[lo:start], self.X[lo:start]
        qs, qt = self.src[query], self.dst[query]
        hosts = np.unique(np.concatenate([s, t, qs, qt]))
        N, d, w = len(hosts), self.d, len(s)
        si, ti = np.searchsorted(hosts, s), np.searchsorted(hosts, t)
        if w:
            oh_s = np.zeros((N, w), np.float32)
            oh_s[si, np.arange(w)] = 1.0
            oh_t = np.zeros((N, w), np.float32)
            oh_t[ti, np.arange(w)] = 1.0
            out_cnt, in_cnt = oh_s.sum(1), oh_t.sum(1)
            mean_out = (oh_s @ Xw) / np.maximum(out_cnt, 1.0)[:, None]
            mean_in = (oh_t @ Xw) / np.maximum(in_cnt, 1.0)[:, None]
            key = si * N + ti
            uk, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
            ps, pt = uk // N, uk % N
            oh_p = np.zeros((len(uk), w), np.float32)
            oh_p[inv, np.arange(w)] = 1.0
            pair_mean = (oh_p @ Xw) / cnt[:, None].astype(np.float32)
            n_out_peers = np.bincount(ps, minlength=N).astype(np.float32)
            n_in_peers = np.bincount(pt, minlength=N).astype(np.float32)
        else:
            out_cnt = in_cnt = n_out_peers = n_in_peers = np.zeros(N, np.float32)
            mean_out = mean_in = np.zeros((N, d), np.float32)
            uk = np.zeros(0, np.int64)
            ps = pt = np.zeros(0, np.int64)
            cnt = np.zeros(0, np.int64)
            pair_mean = np.zeros((0, d), np.float32)
        new = ((out_cnt + in_cnt) == 0).astype(np.float32)
        node_feat = np.concatenate([np.log1p(np.stack([out_cnt, in_cnt, n_out_peers, n_in_peers], 1)),
                                    new[:, None], mean_out, mean_in], axis=1).astype(np.float32)
        pair_feat = np.concatenate([np.log1p(cnt.astype(np.float32))[:, None], pair_mean], axis=1).astype(np.float32)
        qsi, qti = np.searchsorted(hosts, qs), np.searchsorted(hosts, qt)
        qkey = qsi * N + qti
        pos = np.searchsorted(uk, qkey)
        hit = (pos < len(uk)) & (uk[np.minimum(pos, max(len(uk) - 1, 0))] == qkey) if len(uk) else np.zeros(len(qkey), bool)
        qcnt = np.where(hit, cnt[np.minimum(pos, max(len(cnt) - 1, 0))] if len(cnt) else 0, 0).astype(np.float32)
        return {"hosts": hosts, "node_feat": node_feat, "ps": ps, "pt": pt, "pair_feat": pair_feat,
                "qsi": qsi, "qti": qti, "qx": self.X[query], "qcnt": np.log1p(qcnt), "activity": None,
                "n": N}

    @property
    def node_dim(self) -> int:
        return 5 + 2 * self.d

    @property
    def edge_dim(self) -> int:
        return 1 + self.d


# ---------------------------------------------------------------------------------------
class AttnLayer(nn.Module):
    """Dense multi-head attention over graph neighbours with edge-feature biases."""

    def __init__(self, H: int, heads: int, edge_dim: int) -> None:
        super().__init__()
        self.h, self.dh = heads, H // heads
        self.q, self.k, self.v, self.o = (nn.Linear(H, H) for _ in range(4))
        self.e_out, self.e_in = nn.Linear(edge_dim, heads), nn.Linear(edge_dim, heads)
        self.ln1, self.ln2 = nn.LayerNorm(H), nn.LayerNorm(H)
        self.ff = nn.Sequential(nn.Linear(H, 2 * H), nn.ReLU(), nn.Linear(2 * H, H))

    def forward(self, h, ps, pt, pf):
        N, H = h.shape
        bias = torch.zeros(N, N, self.h)
        allowed = torch.eye(N, dtype=torch.bool)
        if len(ps):
            bias_out = torch.zeros(N, N, self.h)
            bias_out[ps, pt] = self.e_out(pf)
            bias_in = torch.zeros(N, N, self.h)
            bias_in[pt, ps] = self.e_in(pf)
            bias = bias_out + bias_in
            allowed[ps, pt] = True
            allowed[pt, ps] = True
        q = self.q(h).view(N, self.h, self.dh).transpose(0, 1)          # heads x N x dh
        k = self.k(h).view(N, self.h, self.dh).transpose(0, 1)
        v = self.v(h).view(N, self.h, self.dh).transpose(0, 1)
        sc = q @ k.transpose(1, 2) / math.sqrt(self.dh) + bias.permute(2, 0, 1)
        sc = sc.masked_fill(~allowed.unsqueeze(0), float("-inf"))
        a = torch.softmax(sc, dim=-1)
        out = (a @ v).transpose(0, 1).reshape(N, H)
        h = self.ln1(h + self.o(out))
        return self.ln2(h + self.ff(h))


class MLPBlock(nn.Module):
    """The matched control's layer: per-node MLP of about the same size, no neighbours."""

    def __init__(self, H: int, edge_dim: int, heads: int) -> None:
        super().__init__()
        self.mix = nn.Sequential(nn.Linear(H, 2 * H), nn.ReLU(), nn.Linear(2 * H, H))
        self.pad = nn.Linear(edge_dim, heads)          # parameter parity with the attention biases
        self.ln1, self.ln2 = nn.LayerNorm(H), nn.LayerNorm(H)
        self.ff = nn.Sequential(nn.Linear(H, 2 * H), nn.ReLU(), nn.Linear(2 * H, H))
        self.pad2 = nn.Linear(edge_dim, heads)

    def forward(self, h, ps, pt, pf):
        h = self.ln1(h + self.mix(h))
        return self.ln2(h + self.ff(h))


class GraphNet(nn.Module):
    def __init__(self, node_dim: int, edge_dim: int, flow_dim: int, H: int = 64, heads: int = 4,
                 layers: int = 2, mixer: str = "attention") -> None:
        super().__init__()
        self.mixer = mixer
        self.enc = nn.Sequential(nn.Linear(node_dim, H), nn.ReLU(), nn.Linear(H, H))
        blk = AttnLayer if mixer == "attention" else MLPBlock
        self.layers = nn.ModuleList([blk(H, heads, edge_dim) if mixer == "attention" else blk(H, edge_dim, heads)
                                     for _ in range(layers)])
        self.score = nn.Sequential(nn.Linear(2 * H + flow_dim + 1, H), nn.ReLU(), nn.Linear(H, 1))

    def encode(self, g):
        h = self.enc(torch.from_numpy(g["node_feat"]))
        ps, pt = torch.from_numpy(g["ps"]), torch.from_numpy(g["pt"])
        pf = torch.from_numpy(g["pair_feat"])
        for lay in self.layers:
            h = lay(h, ps, pt, pf)
        return h

    def forward(self, g, rows: Optional[np.ndarray] = None):
        """Logits for the query flows (all, or the subset `rows`)."""
        h = self.encode(g)
        qsi, qti = torch.from_numpy(g["qsi"]), torch.from_numpy(g["qti"])
        z = torch.cat([h[qsi], h[qti], torch.from_numpy(g["qx"]), torch.from_numpy(g["qcnt"])[:, None]], 1)
        if rows is not None:
            z = z[torch.from_numpy(rows)]
        return self.score(z).squeeze(1)


def subgraph(g: Dict[str, np.ndarray], keep: np.ndarray) -> Dict[str, np.ndarray]:
    """The graph induced by the node mask `keep`; query flows outside it are dropped
    (the returned "qmask" says which of the original query flows remain)."""
    idx = np.flatnonzero(keep)
    remap = -np.ones(g["n"], dtype=np.int64)
    remap[idx] = np.arange(len(idx))
    em = keep[g["ps"]] & keep[g["pt"]]
    qm = keep[g["qsi"]] & keep[g["qti"]]
    return {"hosts": g["hosts"][idx], "node_feat": g["node_feat"][idx], "ps": remap[g["ps"][em]],
            "pt": remap[g["pt"][em]], "pair_feat": g["pair_feat"][em], "qsi": remap[g["qsi"][qm]],
            "qti": remap[g["qti"][qm]], "qx": g["qx"][qm], "qcnt": g["qcnt"][qm], "n": len(idx), "qmask": qm}


# ---------------------------------------------------------------------------------------
class GraphStage:
    """Trainable stage-3 detector: a GraphNet plus per-host drift detectors."""

    def __init__(self, graphs: HostGraphs, mixer: str = "attention", frame: int = 64, H: int = 64,
                 lr: float = 1e-3, seed: int = 0, drift_hold: int = 20, detector: str = "ewma") -> None:
        torch.manual_seed(int(seed))
        self.net = GraphNet(graphs.node_dim, graphs.edge_dim, graphs.d, H=H, mixer=mixer)
        self.opt = torch.optim.Adam(self.net.parameters(), lr=lr)
        self.graphs = graphs
        self.B = int(frame)
        self.counts = np.ones(2)
        self.adwin: Dict[int, object] = {}
        self.last_drift: Dict[int, int] = {}
        self.first_seen: Dict[int, int] = {}
        self.hold = int(drift_hold)
        self.detector = detector
        self.frame_no = 0

    def n_params(self) -> int:
        return int(sum(p.numel() for p in self.net.parameters()))

    def bind(self, graphs: HostGraphs) -> None:
        """Point the stage at a scenario's stream arrays (train rows + perturbed test rows)."""
        self.graphs = graphs

    # -- learning ----------------------------------------------------------------------
    def _loss(self, g, y: np.ndarray, w: np.ndarray):
        logit = self.net(g)
        yt = torch.from_numpy(y.astype(np.float32))
        cw = np.where(y == 1, self.counts.sum() / (2 * self.counts[1]), self.counts.sum() / (2 * self.counts[0]))
        wt = torch.from_numpy(np.clip(cw, 0.1, 10.0).astype(np.float32) * w.astype(np.float32))
        return (nn.functional.binary_cross_entropy_with_logits(logit, yt, reduction="none") * wt).sum() / max(len(y), 1)

    def step(self, start: int, rows: np.ndarray, y: np.ndarray, w: Optional[np.ndarray] = None) -> None:
        """One Adam step on labelled flows `rows` (absolute indices) of the frame at `start`."""
        if len(rows) == 0:
            return
        for c in (0, 1):
            self.counts[c] += float((y == c).sum())
        g = self.graphs.build(start, rows)
        self.opt.zero_grad()
        loss = self._loss(g, y, np.ones(len(rows)) if w is None else w)
        loss.backward()
        self.opt.step()

    def fit(self, n_tr: int, y: np.ndarray, epochs: int = 2):
        """Train on the training stream frame by frame. The first pass is prequential (each
        frame is scored before the step on it); its scores (NaN before the first frame) are
        returned to calibrate the cascade threshold. Later passes only train."""
        pre = np.full(n_tr, np.nan)
        starts = list(range(self.B, n_tr, self.B))
        for ep in range(epochs):
            for st in starts:
                rows = np.arange(st, min(st + self.B, n_tr))
                if ep == 0:              # first pass: score before learning (prequential), warm the drift detectors
                    pre[rows] = self.score_frame(st, rows, focus=("full",), update_drift=True)["full"]
                self.step(st, rows, y[rows])
        return pre

    # -- inference ---------------------------------------------------------------------
    def _update_drift(self, g, rows: np.ndarray) -> None:
        """Feed each host's activity in this frame to its ADWIN (after scoring: causal)."""
        hosts = g["hosts"]
        act = np.zeros(len(hosts))
        np.add.at(act, g["qsi"], 1.0)
        np.add.at(act, g["qti"], 1.0)
        act /= max(len(rows), 1)
        for h, a in zip(hosts.tolist(), act.tolist()):
            det = self.adwin.get(h)
            if det is None:
                det = self.adwin[h] = (rdrift.ADWIN(clock=1) if self.detector == "adwin" else EWMADrift())
                self.first_seen[h] = self.frame_no
            det.update(a)
            if det.drift_detected:
                self.last_drift[h] = self.frame_no
        self.frame_no += 1

    def drifting(self, hosts: np.ndarray) -> np.ndarray:
        f = self.frame_no
        return np.array([(f - self.last_drift.get(h, -10**9) <= self.hold)
                         or (f - self.first_seen.get(h, f) <= self.hold) or (h not in self.first_seen)
                         for h in hosts.tolist()], dtype=bool)

    def score_frame(self, start: int, rows: np.ndarray, focus=("full",), update_drift: bool = True):
        """P(DDoS) for the flows `rows` of the frame at `start`, per focus in ("full", "drift"):
        a dict focus -> scores, NaN = abstained (drift focus: flow outside the 2-hop
        neighbourhood of every drifting or new host). Drift detectors are updated afterwards."""
        g = self.graphs.build(start, rows)
        res = {}
        with torch.no_grad():
            if "full" in focus:
                res["full"] = torch.sigmoid(self.net(g)).numpy().astype(float)
            if "drift" in focus:
                out = np.full(len(rows), np.nan)
                seed = self.drifting(g["hosts"])
                if seed.any():
                    adj = np.zeros((g["n"], g["n"]), bool)
                    adj[g["ps"], g["pt"]] = True
                    adj |= adj.T
                    reach = seed | adj[seed].any(0)
                    reach = reach | adj[reach].any(0)
                    sg = subgraph(g, reach)
                    if sg["qmask"].any():
                        out[sg["qmask"]] = torch.sigmoid(self.net(sg)).numpy()
                res["drift"] = out
        if update_drift:
            self._update_drift(g, rows)
        return res
