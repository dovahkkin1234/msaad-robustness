"""Build the paper's Tables II-VII from the per-seed result JSONs (not the rounded summary CSVs),
so no value is rounded twice. Writes one LaTeX body per table plus values.json for checking.
Usage: python build_tables.py <repo>/scripts <results dir> <out dir>"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import make_figures as mf  # noqa: E402
import numpy as np  # noqa: E402

RES, OUT = Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
DS = ["iotid20", "ciciot2023", "cicids2017"]
NAME = {"iotid20": "IoTID20", "ciciot2023": "CICIoT2023", "cicids2017": "CIC-IDS2017"}
PGD = "pgd/attack_only/feasible"
VALUES = {}
_cache = {}


def runs(grid, tag):
    key = (grid, tag)
    if key not in _cache:
        _cache[key] = mf.seed_runs(RES / grid, tags={tag})
    return _cache[key]


def vals(grid, tags, metric, **kw):
    """Per-seed values from the first tag that has them."""
    for t in tags:
        v = mf.per_seed(runs(grid, t), metric, **kw)
        if v:
            return v
    return []


def ms(v):
    if not v:
        return None
    return float(np.mean(v)), (statistics.stdev(v) if len(v) > 1 else 0.0), len(v)


def cell(v, d=2, name=None, pm=True):
    r = ms(v)
    if name:
        VALUES[name] = None if r is None else {"mean": r[0], "std": r[1], "n": r[2]}
    if r is None:
        return "--"
    m, s, _ = r
    return f"{m:.{d}f}" if not pm else f"{m:.{d}f}$\\pm${s:.{d}f}"


def write(name, lines):
    (OUT / f"{name}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- Table II: reproduction
PAPER = {"iotid20": "99.50", "ciciot2023": "99.28", "cicids2017": "--"}
rows = []
for d in DS:
    # the 50,000-flow reproduction grid: one flat JSON per seed (grid/<dataset>_seed<k>.json)
    rep = [json.load(open(f))["accuracy"] for f in sorted((RES / "grid").glob(f"{d}_seed*.json"))]
    acc = vals("loop_grid", ["s15"], "accuracy", dataset=d, policy="vanilla", scenario="clean", learning="true")
    fpr = vals("loop_grid", ["s15"], "fpr", dataset=d, policy="vanilla", scenario="clean", learning="true")
    maj = vals("loop_grid", ["s15"], "majority_accuracy", dataset=d, policy="vanilla", scenario="clean",
               learning="true")
    rows.append(f"{NAME[d]} & {PAPER[d]} & {cell(rep, name=f'II/{d}/repro_acc')} & "
                f"{cell(acc, name=f'II/{d}/acc')} & {cell(fpr, name=f'II/{d}/fpr')} & "
                f"{cell(maj, d=1, name=f'II/{d}/always_ddos', pm=False)} \\\\")
write("tab2_body", rows)

# ---------------------------------------------------------------- Table III: label modes
A = "attack_grid"
modes = [
    ("Instant (Alg.~1), PGD", ["s15"], "pgd/attack_only", "online"),
    ("Instant (Alg.~1), repaired PGD", ["s15"], PGD, "online"),
    ("Delay 1{,}000 flows", ["s15"], "pgd/attack_only", "delay:1000"),
    ("Delay 5{,}000 flows", ["s15"], "pgd/attack_only", "delay:5000"),
    ("Delay 60\\,s", ["s15"], "pgd/attack_only", "delaysec:60"),
    ("Delay 300\\,s", ["s15"], "pgd/attack_only", "delaysec:300"),
    ("No labels, PGD", ["s15"], "pgd/attack_only", "frozen"),
    ("No labels, repaired PGD", ["s15"], PGD, "frozen"),
    ("No labels, repaired C\\&W", ["s15"], "cw/attack_only/feasible", "frozen"),
    ("Self-labels, PGD$^\\dagger$", ["labels"], "pgd/attack_only", "self"),
]
rows = []
for lab, tags, sc, learn in modes:
    cells = [cell(vals(A, tags, "asr", dataset=d, scenario=sc, learning=learn), name=f"III/{d}/{lab}") for d in DS]
    rows.append(f"{lab} & " + " & ".join(cells) + " \\\\")
    if lab == "No labels, repaired PGD":
        med = []
        for d in DS:
            v = vals(A, tags, "asr", dataset=d, scenario=sc, learning=learn)
            VALUES[f"III/{d}/median repaired PGD"] = float(np.median(v)) if v else None
            med.append(f"{np.median(v):.2f}" if v else "--")
        rows.append("\\quad median & " + " & ".join(med) + " \\\\")
write("tab3_body", rows)

# ---------------------------------------------------------------- Table IV: policies under poisoning
L = "loop_grid"
pols = [("No labels (frozen)", "frozen"), ("Vanilla (base paper)", "vanilla"), ("Audit (selector only)", "audit:0.1"),
        ("Guard", "guard:0.1"), ("Strict", "strict:0.1"), ("IW-strict", "iwstrict:0.1"),
        ("IW-strict, 20\\% audits", "iwstrict:0.2"), ("IW-consensus", "iwconsensus:0.1")]
rows = []
for lab, p in pols:
    cells = []
    for d in DS:
        if p == "frozen":
            asr = vals(L, ["s15"], "asr", dataset=d, policy=p, scenario=PGD, learning="frozen")
            fc = vals(L, ["s15"], "fpr", dataset=d, policy=p, scenario="clean", learning="frozen")
            fa = vals(L, ["s15"], "fpr", dataset=d, policy=p, scenario=PGD, learning="frozen")
        elif p == "iwconsensus:0.1":
            asr = vals(L, ["s15"], "asr", dataset=d, policy="iwstrict:0.1", scenario=PGD, learning="poison:1.0")
            fc = vals(L, ["oprand", "frame"], "fpr", dataset=d, policy=p, scenario="clean", learning="true")
            fa = vals(L, ["oprand", "frame"], "fpr", dataset=d, policy=p, scenario=PGD, learning="true")
        else:
            asr = vals(L, ["s15"], "asr", dataset=d, policy=p, scenario=PGD, learning="poison:1.0")
            fc = vals(L, ["s15"], "fpr", dataset=d, policy=p, scenario="clean", learning="true")
            fa = vals(L, ["s15"], "fpr", dataset=d, policy=p, scenario=PGD, learning="true")
        a = cell(asr, name=f"IV/{d}/{p}/asr_q1")
        if p == "iwconsensus:0.1":
            a = a + "$^\\ddagger$"
        cells += [a, cell(fc, name=f"IV/{d}/{p}/fpr_clean"), cell(fa, name=f"IV/{d}/{p}/fpr_attack")]
    rows.append(f"{lab} & " + " & ".join(cells) + " \\\\")
write("tab4_body", rows)

# ---------------------------------------------------------------- Table V: audits, matched detection
MODE_TAGS = {  # (tags for ASR under q=1, tags for FPR/n_audited with true labels, tags for operating points)
    "random": (["s15"], ["frame", "oprand"], ["oprand"]),
    "uncertain": (["audits", "frameunc"], ["audits", "frameunc", "opunc"], ["opunc"]),
    "mixed": (["auditsmix"], ["auditsmix", "opmix"], ["opmix"]),
}
MODE_NAME = {"random": "random", "uncertain": "uncert.", "mixed": "mixed"}
plan = [("Vanilla", "vanilla", [None]), ("Strict", "strict:0.1", ["random", "uncertain"]),
        ("IW-strict", "iwstrict:0.1", ["random", "uncertain", "mixed"]),
        ("IW-consensus", "iwconsensus:0.1", ["random", "uncertain"])]
rows = []
for d in DS:
    rows.append(f"\\multicolumn{{9}}{{@{{}}l}}{{\\textit{{{NAME[d]}}}}} \\\\")
    for lab, p, modes in plan:
        for m in modes:
            key = f"V/{d}/{p}/{m}"
            if p == "vanilla":
                asr = vals(L, ["s15"], "asr", dataset=d, policy=p, scenario=PGD, learning="poison:1.0")
                fa = vals(L, ["s15"], "fpr", dataset=d, policy=p, scenario=PGD, learning="true")
                na = []
                op = ["oprand"]
            else:
                ta, tt, op = MODE_TAGS[m]
                pa = "iwstrict:0.1" if p == "iwconsensus:0.1" else p      # identical under q = 1 (no DDoS labels)
                asr = vals(L, ta, "asr", dataset=d, policy=pa, scenario=PGD, learning="poison:1.0")
                fa = vals(L, tt, "fpr", dataset=d, policy=p, scenario=PGD, learning="true")
                na = vals(L, tt, "n_audited", dataset=d, policy=p, scenario=PGD, learning="true")
            f999a = vals(L, op, "fpr_at_tpr999", dataset=d, policy=p, scenario=PGD, learning="true")
            auca = vals(L, op, "auc", dataset=d, policy=p, scenario=PGD, learning="true")
            f999c = vals(L, op, "fpr_at_tpr999", dataset=d, policy=p, scenario="clean", learning="true")
            aucc = vals(L, op, "auc", dataset=d, policy=p, scenario="clean", learning="true")
            a = cell(asr, name=key + "/asr_q1")
            if p == "iwconsensus:0.1" and a != "--":
                a += "$^\\ddagger$"
            rows.append(" & ".join([lab, "--" if m is None else MODE_NAME[m], a, cell(fa, name=key + "/fpr_attack"),
                                    cell(na, d=0, name=key + "/n_audited"),
                                    cell(f999a, name=key + "/fpr999_attack"), cell(auca, name=key + "/auc_attack"),
                                    cell(f999c, name=key + "/fpr999_clean"), cell(aucc, name=key + "/auc_clean")])
                        + " \\\\")
write("tab5_body", rows)

# check the "identical by construction" claim wherever both runs exist
same = []
for d in DS:
    for t in ("frameunc", "frame", "s15"):
        a = vals(L, [t], "asr", dataset=d, policy="iwstrict:0.1", scenario=PGD, learning="poison:1.0")
        b = vals(L, [t], "asr", dataset=d, policy="iwconsensus:0.1", scenario=PGD, learning="poison:1.0")
        if a and b:
            same.append((d, t, a == b))
VALUES["V/iwconsensus_equals_iwstrict_q1"] = same

# ---------------------------------------------------------------- Table VI: combined attack (two scenarios)
C3 = "poison:1.0+frame:0.05"
plan = [("Vanilla", "vanilla", [None]), ("Strict", "strict:0.1", ["random", "uncertain"]),
        ("IW-strict", "iwstrict:0.1", ["random", "uncertain"]),
        ("IW-consensus", "iwconsensus:0.1", ["random", "uncertain"])]
rows = []
for sc, title in ((PGD, "Evasion (repaired PGD) + full poisoning + 5\\% framing"),
                  ("clean", "Full poisoning + 5\\% framing, no evasion")):
    rows.append(f"\\multicolumn{{8}}{{@{{}}l}}{{\\textit{{{title}}}}} \\\\")
    ref = []
    for d in DS:
        ref += [cell(vals(L, ["s15"], "asr", dataset=d, policy="vanilla", scenario=sc, learning="true"),
                     name=f"VI/{d}/{sc}/reference/asr"),
                cell(vals(L, ["s15"], "fpr", dataset=d, policy="vanilla", scenario=sc, learning="true"),
                     name=f"VI/{d}/{sc}/reference/fpr")]
    rows.append("Vanilla, true labels & -- & " + " & ".join(ref) + " \\\\")
    for lab, p_, modes in plan:
        for m in modes:
            tags = {None: ["frame", "combounc"], "random": ["frame"], "uncertain": ["combounc"]}[m]
            cells = []
            for d in DS:
                key = f"VI/{d}/{sc}/{p_}/{m}"
                cells += [cell(vals(L, tags, "asr", dataset=d, policy=p_, scenario=sc, learning=C3), name=key + "/asr"),
                          cell(vals(L, tags, "fpr", dataset=d, policy=p_, scenario=sc, learning=C3), name=key + "/fpr")]
            rows.append(" & ".join([lab, "--" if m is None else MODE_NAME[m]] + cells) + " \\\\")
write("tab6_body", rows)

(OUT / "values.json").write_text(json.dumps(VALUES, indent=1), encoding="utf-8")
print("wrote", sorted(p.name for p in OUT.glob("*")))
