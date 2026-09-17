#!/usr/bin/env python3
"""check — the checker ladder (SPEC §6): reject-authorized, strongest
rung first. A failure is a fact no model opinion overturns; a pass proves
only what that rung states. "not available" is NEVER a pass: a brief that
names a rung this host cannot run fails its definition-of-done (no
checker gets installed mid-run — a host decision).

Rungs:  R1 proof (Lean / SMT)      — not available on this host
        R2 compile / types         — py_compile over the scope's .py files
        R3 lint / static           — ruff or pyflakes; not available here
        R4 tests                   — the command the brief names, else
                                     `python3 -m unittest discover -q`;
                                     "no tests ran" is a FAIL — unittest
                                     exits 5 for it only on Python ≥ 3.12,
                                     so "Ran 0 tests" in the output is
                                     checked too (the kit allows ≥ 3.10)
        R5 diffs / exit codes /    — the expected files the brief names
           expected files             exist in the scope (non-empty)

The brief names rungs in its definition-of-done: `R4: python3 test_x.py;
R5: fizz.py, test_x.py; R2` (an argument after the colon, rungs separated
by `;`). The adapter runs them after the worker's final report and before
filing; `/check <worker_id> [rungs]` re-runs them on demand and re-stamps
the report and the registry state.

Usage:  python3 plumbing/check.py <worker_id> [R2;R4: cmd;R5: a.py]
"""

import json
import py_compile
import re
import shutil
import subprocess
import sys
from pathlib import Path

RUNGS = ("R1", "R2", "R3", "R4", "R5")
RUNG_TIMEOUT_S = 300
DEFAULT_TEST_CMD = "python3 -m unittest discover -q"
_RUNG = re.compile(r"\bR([1-5])\b(?:\s*:\s*([^;\n]+))?")


def parse_rungs(text: str) -> dict:
    """`R2; R4: python3 test_x.py; R5: a.py, b.py` -> {"R2": None, "R4": "…", "R5": "…"}."""
    found = {}
    for m in _RUNG.finditer(text or ""):
        found[f"R{m.group(1)}"] = (m.group(2) or "").strip() or None
    return dict(sorted(found.items()))


def available(rung: str) -> bool:
    if rung == "R1":
        return bool(shutil.which("lean") or shutil.which("z3"))
    if rung == "R3":
        if shutil.which("ruff"):
            return True
        try:
            import pyflakes  # noqa: F401
            return True
        except ImportError:
            return False
    return rung in ("R2", "R4", "R5")


def _sh(cmd: str, cwd: Path) -> tuple:
    try:
        r = subprocess.run(cmd, shell=True, cwd=str(cwd), capture_output=True,
                           text=True, timeout=RUNG_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {RUNG_TIMEOUT_S}s: {cmd}"
    return r.returncode, (r.stdout + r.stderr)[-4000:]


def run_rung(rung: str, scope: Path, arg=None) -> dict:
    scope = Path(scope).expanduser().resolve()
    if not available(rung):
        return {"rung": rung, "status": "not available",
                "output": f"{rung} has no checker on this host"}
    if rung == "R2":
        bad = []
        files = sorted(p for p in scope.rglob("*.py") if "__pycache__" not in p.parts)
        for p in files:
            try:
                py_compile.compile(str(p), doraise=True)
            except py_compile.PyCompileError as e:
                bad.append(str(e).strip()[-300:])
        return {"rung": rung, "status": "fail" if bad else "pass",
                "output": "\n".join(bad) or f"{len(files)} file(s) compile"}
    if rung == "R3":
        tool = "ruff check ." if shutil.which("ruff") else "python3 -m pyflakes ."
        code, out = _sh(arg or tool, scope)
        return {"rung": rung, "status": "pass" if code == 0 else "fail",
                "output": out.strip() or f"exit {code}"}
    if rung == "R4":
        cmd = arg or DEFAULT_TEST_CMD
        code, out = _sh(cmd, scope)
        # "no tests ran" proves nothing: unittest exits 5 for it only since
        # Python 3.12; on 3.10/3.11 it exits 0, so the output line is checked too.
        none_ran = re.search(r"\bRan 0 tests\b", out) is not None
        return {"rung": rung, "status": "fail" if (code != 0 or none_ran) else "pass",
                "output": f"$ {cmd}\n{out.strip()}\n[exit {code}]"
                          + ("\n[no tests ran]" if none_ran else "")}
    if rung == "R5":
        names = [n.strip() for n in (arg or "").split(",") if n.strip()]
        if not names:
            return {"rung": rung, "status": "fail",
                    "output": "R5 named no expected files (R5: a.py, b.py)"}
        missing = [n for n in names if not (scope / n).exists() or (scope / n).stat().st_size == 0]
        return {"rung": rung, "status": "fail" if missing else "pass",
                "output": ("missing or empty: " + ", ".join(missing)) if missing
                else f"present: {', '.join(names)}"}
    if rung == "R1":
        code, out = _sh(arg or "lean --version", scope)
        return {"rung": rung, "status": "pass" if code == 0 else "fail", "output": out.strip()}
    raise ValueError(f"unknown rung {rung}")


def ladder(scope, rungs: dict) -> list:
    """Run the named rungs strongest first; every rung runs, none is skipped."""
    return [run_rung(r, scope, rungs.get(r)) for r in RUNGS if r in rungs]


def verdict(results: list) -> bool:
    return bool(results) and all(r["status"] == "pass" for r in results)


def summary(results: list) -> str:
    return "\n".join(f"{r['rung']} {r['status'].upper()}: {r['output']}" for r in results)


def stamp(report: dict, results: list) -> dict:
    """Stamp rung results into a report; a failure overrules a done claim."""
    report["checks"] = results
    if results and not verdict(results):
        failed = [r for r in results if r["status"] != "pass"]
        report["complete"] = False
        report["open_items"] = "FAILED rung " + "; ".join(
            f"{r['rung']} ({r['status']})" for r in failed)
        report["evidence"] = (str(report.get("evidence", "-")) +
                              "\n--- checker ladder ---\n" + summary(results))
    return report


def main(argv=None) -> None:
    import lineage
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: check.py <worker_id> [rungs, e.g. 'R2; R4: python3 test_x.py; R5: a.py']")
        return
    wid, spec = argv[0], " ".join(argv[1:])
    lid = lineage.lineage_of(wid)
    w = lineage.worker_entry(lid, wid)
    if w is None:
        print(f"no worker {wid} (ids look like 20260914-xxxxxx.hhhhhh; see /status)")
        return
    rungs = parse_rungs(spec) if spec else parse_rungs(w["brief"]["definition_of_done"])
    if not rungs:
        print(f"no rungs named for {wid}: give them, e.g. check.py {wid} 'R4: python3 test_x.py'")
        return
    results = ladder(w["brief"]["scope"], rungs)
    print(summary(results))
    if not w.get("report_path"):
        print(f"(no report filed yet for {wid}; nothing re-stamped)")
        return
    report = json.loads(Path(w["report_path"]).read_text())
    was_complete = bool(report.get("complete"))
    report["checks"] = results
    if verdict(results):
        state = "done" if was_complete and report.get("evidence", "-") not in ("", "-") else w["state"]
    else:
        stamp(report, results)
        state = "failed"
    lineage.file_report(lid, wid, report, state=state)
    import events
    events.emit(lid, wid, "check", f"{'PASS' if verdict(results) else 'FAIL'} -> {state}: "
                + "; ".join(f"{r['rung']} {r['status']}" for r in results))
    print(f"— verdict: {'PASS' if verdict(results) else 'FAIL'}; {wid} is now {state} —")


if __name__ == "__main__":
    main()
