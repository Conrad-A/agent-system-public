#!/usr/bin/env python3
"""Eval runner (SPEC §12): outcome-graded, never transcript-graded.

Tasks are JSON files in evals/regression/ and evals/capability/:
{ "id": "...", "prompt": "...", "grader": "exact|contains|regex",
  "expected": "...", "trials": 3 }
Graders are mechanical (no LLM judge in the core, SPEC §6): `exact`,
`contains` (case-insensitive; a list means all must appear), `regex`.
Regression gate: every task at pass^k (works every trial) for `main`;
capability: pass@k, the hill. Eval runs are worker runs — they cost money
and run deliberately, never on every commit.

Usage:  python3 evals/run.py [regression|capability]
"""

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "plumbing"))
from clients import DEEPSEEK, WORKER_MODEL, message  # noqa: E402


def ask(prompt: str) -> str:
    r = DEEPSEEK.complete([{"role": "user", "content": prompt}],
                          model=WORKER_MODEL, effort="max")   # 16384 incl. thinking
    return message(r).get("content") or ""


def grade(task: dict, out: str) -> bool:
    g, expected = task["grader"], task["expected"]
    if g == "exact":
        return out.strip() == expected.strip()
    if g == "contains":
        wants = expected if isinstance(expected, list) else [expected]
        return all(w.lower() in out.lower() for w in wants)
    if g == "regex":
        return re.search(expected, out.strip()) is not None
    raise ValueError(f"unknown grader {g}")


def run_task(task: dict) -> list:
    return [grade(task, ask(task["prompt"])) for _ in range(task.get("trials", 3))]


def main(folder: str) -> None:
    tasks = sorted(pathlib.Path(__file__).parent.joinpath(folder).glob("*.json"))
    if not tasks:
        print(f"no tasks in {folder}/ — harvest them from real failures")
        return
    total_pass_all = 0
    for p in tasks:
        t = json.loads(p.read_text())
        res = run_task(t)
        pass_all, pass_any = all(res), any(res)       # pass^k gate, pass@k hill
        total_pass_all += pass_all
        print(f"{t['id']}: trials={res} pass^k={pass_all} pass@k={pass_any}")
    print(f"\n{folder}: {total_pass_all}/{len(tasks)} at pass^k")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "regression")
