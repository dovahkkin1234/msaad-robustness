"""Commit the latest results to git and push them to GitHub, with a journal entry in RUNS.md.

Run it after every experiment, or let experiments\\run_grid.py call it with --push. It
  1. finds what is new since the last commit: the grid runs that run_grid.py recorded in
     results\\grid_runs.jsonl, and every new, changed or deleted file;
  2. appends an entry to RUNS.md: when, what ran (the exact command), on which code version,
     which runs succeeded or failed, which result files changed, and your note;
  3. rebuilds the run-history table at the end of RUNS.md from every result JSON;
  4. commits all of it and pushes it to the GitHub remote (origin).

Safety: datasets (data\\) are never committed (see .gitignore); it refuses to commit any file
over 50 MB, anything under data\\ or anything that looks like a private key; it never rewrites
or force-pushes history. If the push fails (offline, key not added yet), the commit stays on
your laptop and the next run of this script sends it.

Usage (repo root, msaad environment active; one-time setup in SETUP.md, Step 15):
    python scripts\\push_run.py                              # after a grid: the entry is written for you
    python scripts\\push_run.py -m "checked the IW results"  # add a note to the entry
    python scripts\\push_run.py "Quick look: RADP, IoTID20, --limit 3000"   # a run outside run_grid
    python scripts\\push_run.py --no-push                    # commit only; the next run sends it
    python scripts\\push_run.py --dry-run                    # show the entry and the files; change nothing
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "RUNS.md"
GRID_LOG = "results/grid_runs.jsonl"
MAX_MB = 50
HIST_START, HIST_END = "<!-- history:start -->", "<!-- history:end -->"
JOURNAL_HDR = "## Journal"
HISTORY_HDR = "## Run history"
SECRET = re.compile(r"(^|/)(id_(rsa|dsa|ecdsa|ed25519)(_sk)?|[^/]*_deploy|[^/]*\.(pem|key|ppk|pfx|p12))$", re.I)
EXP_NAMES = {"grid": "repro grid", "attack_grid": "attack grid", "radp_grid": "RADP grid",
             "loop_grid": "loop grid", "under_attack": "attack", "radp": "RADP", "loop": "loop",
             "results": "repro"}
TEMPLATE = f"""# Run journal

Every experiment run, newest last: what ran, the exact command, the code version, what came out,
and a note. `scripts/push_run.py` writes the entries, commits the results and pushes them (SETUP.md,
Step 15). The table at the end is rebuilt from the result JSONs on every push. Findings and their
numbers live in PLAN.md.

{JOURNAL_HDR}

{HISTORY_HDR} (rebuilt from the result files on every push)

{HIST_START}
{HIST_END}
"""


class GitError(RuntimeError):
    pass


def git(*args, check=True) -> str:
    try:
        p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except FileNotFoundError:
        raise SystemExit("[push] git is not installed or not on PATH: see SETUP.md, Step 15")
    if check and p.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed:\n{(p.stderr or p.stdout).strip()}")
    return p.stdout


def git_live(*args) -> int:
    """Run git with the terminal attached (push may ask to trust GitHub's host key)."""
    return subprocess.run(["git", *args], cwd=ROOT).returncode


def check_repo() -> None:
    try:
        top = git("rev-parse", "--show-toplevel").strip()
    except GitError:
        raise SystemExit("[push] this folder is not a git repository yet: do SETUP.md, Step 15 first")
    if os.path.normcase(str(Path(top).resolve())) != os.path.normcase(str(ROOT)):
        raise SystemExit(f"[push] the git repository root is {top}, expected {ROOT}")
    for key in ("user.name", "user.email"):
        if not git("config", key, check=False).strip():
            raise SystemExit(f"[push] git does not know who you are yet: set {key} (SETUP.md, Step 15)")


def changed_files():
    """[(status, path)] for every new, changed or deleted file git does not ignore."""
    out = git("status", "--porcelain=v1", "-uall", "-z")
    items, files, i = out.split("\0"), [], 0
    while i < len(items):
        e = items[i]
        i += 1
        if not e:
            continue
        xy, path = e[:2], e[3:]
        files.append((xy, path))
        if "R" in xy or "C" in xy:
            i += 1                       # renames carry the old path as an extra field
    return files


def kind_of(xy: str) -> str:
    return "new" if xy == "??" or "A" in xy else ("deleted" if "D" in xy else "changed")


def problems_in(paths) -> list:
    bad = []
    for p in paths:
        if p.startswith("data/"):
            bad.append(f"{p}: datasets are never committed (check .gitignore)")
        elif SECRET.search(p):
            bad.append(f"{p}: looks like a private key or certificate")
        else:
            f = ROOT / p
            if f.is_file() and f.stat().st_size > MAX_MB * 1_000_000:
                bad.append(f"{p}: {f.stat().st_size / 1e6:.0f} MB, over the {MAX_MB} MB limit")
    return bad


def new_grid_records() -> list:
    """Grid runs recorded since the last commit (lines of grid_runs.jsonl not yet in HEAD)."""
    p = ROOT / GRID_LOG
    if not p.exists():
        return []
    now = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    try:
        old = [ln for ln in git("show", f"HEAD:{GRID_LOG}").splitlines() if ln.strip()]
    except GitError:
        old = []
    recs = []
    for ln in now[len(old):]:
        try:
            recs.append(json.loads(ln))
        except ValueError:
            pass
    return recs


def grid_title(r: dict) -> str:
    tag = f" [{r['tag']}]" if r.get("tag") else ""
    seeds = ", ".join(str(s) for s in r.get("seeds", []))
    return f"{r.get('exp', '?')} grid{tag}: {', '.join(r.get('datasets', []))} x seeds {seeds}"


def results_summary(files) -> list:
    """One line per results folder: counts of new/changed/deleted JSON, CSV, logs, figures."""
    groups = {}
    for xy, path in files:
        if not path.startswith("results/"):
            continue
        parts = path.split("/")
        folder = "/".join(parts[:2]) if len(parts) > 2 else "results"
        groups.setdefault(folder, []).append((kind_of(xy), path))
    lines = []
    for folder in sorted(groups):
        cnt = Counter()
        named = []
        for k, path in groups[folder]:
            name = path.rsplit("/", 1)[-1]
            if "/logs/" in path:
                cnt[(k, "log")] += 1
            elif name.startswith(("summary", "inspect_", "grid_runs")) or folder in ("results/paper", "results/provenance"):
                named.append(f"{name} ({k})")
            else:
                cnt[(k, name.rsplit(".", 1)[-1].upper() if "." in name else "file")] += 1
        parts = [f"{n} {k} {ext}" for (k, ext), n in sorted(cnt.items())]
        if named:
            parts.append(", ".join(named[:12]) + (f" and {len(named) - 12} more" if len(named) > 12 else ""))
        lines.append(f"`{folder}`: " + "; ".join(parts))
    return lines


def history_table() -> str:
    rows = []
    for p in sorted((ROOT / "results").rglob("*.json")):
        mt = re.fullmatch(r"(.+?)_seed(\d+)(?:_(.+))?\.json", p.name)
        if not mt or "provenance" in p.parts:
            continue
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(r, dict):
            continue
        el = r.get("elapsed_s")
        rows.append((str(r.get("finished_at") or ""), EXP_NAMES.get(p.parent.name, p.parent.name),
                     str(r.get("dataset", mt.group(1))), str(r.get("seed", mt.group(2))), mt.group(3) or "",
                     "" if r.get("n") is None else f"{r['n']:,}", "" if el is None else f"{el / 60:.1f}",
                     p.relative_to(ROOT).as_posix()))
    rows.sort()
    out = ["| Finished | Experiment | Dataset | Seed | Tag | Rows | Minutes | Result file |",
           "|---|---|---|---|---|---|---|---|"]
    out += [f"| {a.replace('T', ' ')} | {b} | {c} | {d} | {e} | {f} | {g} | `{h}` |" for a, b, c, d, e, f, g, h in rows]
    reports = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "results").glob("inspect_*.txt"))
    if reports:
        out += ["", "Dataset reports: " + ", ".join(f"`{x}`" for x in reports)]
    return "\n".join(out) if rows or reports else "(no result files yet)"


def build_entry(what, note, recs, files, head) -> tuple:
    now = dt.datetime.now().astimezone()
    stamp = now.strftime("%Y-%m-%d %H:%M") + f" (UTC{now.strftime('%z')[:3]}:{now.strftime('%z')[3:]})"
    title = what or ("; ".join(grid_title(r) for r in recs) if recs else (note or "Files updated"))
    lines = [f"### {stamp} - {title}", ""]
    for r in recs:
        runs = r.get("runs", [])
        ok = sum(1 for x in runs if x.get("status") == "ok")
        skipped = sum(1 for x in runs if str(x.get("status", "")).startswith("skipped"))
        failed = [x for x in runs if str(x.get("status", "")).startswith("FAILED")]
        lines.append(f"- **Command:** `{r.get('command', '?')}`")
        state = f"{ok} ok, {len(failed)} failed" + (f", {skipped} already done" if skipped else "")
        lines.append(f"- **Runs:** {state}; {r.get('minutes', 0):.1f} min "
                     f"({r.get('started_at', '?').replace('T', ' ')} to {r.get('finished_at', '?').replace('T', ' ')})")
        for x in failed:
            lines.append(f"  - FAILED: {x.get('data')} seed {x.get('seed')} ({x.get('status')})")
    code = [p for xy, p in files if not p.startswith("results/") and p != "RUNS.md"]
    lines.append(f"- **Code version:** {head or 'first commit'}"
                 + (f"; this commit also changes {len(code)} code/document file(s)"
                    + (": " + ", ".join(f"`{p}`" for p in code[:8]) + (" ..." if len(code) > 8 else "") if code else "")
                    if code else ""))
    res = results_summary(files)
    if res:
        lines.append("- **Results:**")
        lines += [f"  - {x}" for x in res]
    if note:
        lines.append(f"- **Note:** {note}")
    return title, "\n".join(lines) + "\n"


def update_journal(entry: str) -> None:
    text = JOURNAL.read_text(encoding="utf-8") if JOURNAL.exists() else TEMPLATE
    if HISTORY_HDR in text:
        i = text.index(HISTORY_HDR)
        text = text[:i].rstrip() + "\n\n" + entry + "\n" + text[i:]
    else:
        text = text.rstrip() + "\n\n" + entry
    block = f"{HIST_START}\n{history_table()}\n{HIST_END}"
    if HIST_START in text and HIST_END in text:
        text = re.sub(re.escape(HIST_START) + r".*?" + re.escape(HIST_END), lambda _m: block, text, flags=re.S)
    else:
        text = text.rstrip() + f"\n\n{HISTORY_HDR} (rebuilt from the result files on every push)\n\n{block}\n"
    JOURNAL.write_text(text, encoding="utf-8")


def upstream() -> str:
    return git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False).strip()


def waiting() -> bool:
    """Are there commits on this laptop that GitHub does not have yet?"""
    if not git("rev-parse", "--verify", "-q", "HEAD", check=False).strip() or not git("remote").split():
        return False
    if not upstream():
        return True
    return git("rev-list", "--count", "@{u}..HEAD", check=False).strip() not in ("", "0")


def push() -> int:
    if not git("remote").split():
        print("[push] no GitHub remote yet (git remote add origin ...): the commit stays local")
        return 1
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    rc = git_live("push") if upstream() else git_live("push", "-u", "origin", branch)
    if rc != 0:
        print("[push] the push did not go through; the commit is safe on this laptop. Fix the cause "
              "(network, deploy key) and run this script again: it sends whatever is waiting.")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="Journal, commit and push the latest results.")
    ap.add_argument("what", nargs="?", default=None, help="what ran, if it was not a run_grid.py grid")
    ap.add_argument("-m", "--note", default=None, help="a note for the journal entry")
    ap.add_argument("--no-push", action="store_true", help="commit only")
    ap.add_argument("--dry-run", action="store_true", help="show the entry and the files; change nothing")
    args = ap.parse_args()
    check_repo()

    files = [f for f in changed_files() if f[1] != "RUNS.md"]
    recs = new_grid_records()
    if not files and not recs:
        print("[push] nothing new to commit")
        if not args.no_push and not args.dry_run and waiting():
            print("[push] earlier commit(s) are not on GitHub yet: pushing them")
            return push()
        return 0
    bad = problems_in([p for xy, p in files if kind_of(xy) != "deleted"])
    if bad:
        print("[push] refusing to commit:")
        for b in bad:
            print("  -", b)
        print("[push] move those files out of the repository folder (or add them to .gitignore), then re-run")
        return 1
    head = git("rev-parse", "--short", "HEAD", check=False).strip()
    title, entry = build_entry(args.what, args.note, recs, files, head)
    if args.dry_run:
        print(entry)
        print(f"[push] dry run: {len(files)} file(s) would be committed (data\\ is never among them); "
              "nothing was changed")
        return 0

    update_journal(entry)
    git("add", "-A")
    staged = [p for p in git("diff", "--cached", "--name-only", "-z").split("\0") if p]
    bad = problems_in(staged)
    if bad:                                 # belt and braces: never commit what slipped through
        git("reset", "-q")
        print("[push] refusing to commit (nothing was committed):")
        for b in bad:
            print("  -", b)
        return 1
    git("commit", "-q", "-m", title[:100], "-m", entry)
    sha = git("rev-parse", "--short", "HEAD").strip()
    print(f"[push] committed {sha}: {len(staged)} file(s); journal entry added to RUNS.md")
    if args.no_push:
        print("[push] not pushed (--no-push); run this script again later to send it")
        return 0
    rc = push()
    if rc == 0:
        print(f"[push] pushed {sha} to GitHub")
    return rc


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GitError as exc:
        print(f"[push] {exc}")
        raise SystemExit(1)
