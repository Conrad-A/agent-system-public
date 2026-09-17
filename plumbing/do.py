#!/usr/bin/env python3
"""do — /worker: brief a DeepSeek worker and launch it DETACHED (SPEC §4).

Usage:
  python3 plumbing/do.py "<goal>" --scope DIR [--dod "<definition of done>"]
      [--preset minimal|standard|think] [--runtime engine|plain]
      [--steps N] [--timeout S] [--constraints "..."] [--facts "..."]

The lineage is this directory's (lineages/index.json). `think` runs one
tool-free call inline and prints the answer (no registry entry). Every
other preset registers the worker and starts worker.py with setsid, so
the worker outlives this process and the lead's session; stdout/stderr go
to the worker log. The lead then watches /status (and, from step 3, the
Monitor on events.jsonl). Never spawn for ~/Desktop as a whole (§4.3).
"""

import argparse
import subprocess
import sys
from pathlib import Path

import lineage  # noqa: E402

PRESETS = ("minimal", "standard", "think")
DEFAULT_DOD = "task completed with evidence, or a clear stop-reason reported"
HERE = Path(__file__).resolve().parent


def build_brief(a) -> dict:
    scope = Path(a.scope).expanduser().resolve()
    if scope == Path.home() or scope == Path.home() / "Desktop":
        raise SystemExit("refusing: the scope must be one project directory, "
                         "never the home directory or the whole Desktop (SPEC §4.3)")
    return {"goal": a.goal, "definition_of_done": a.dod, "scope": str(scope),
            "constraints": a.constraints, "facts": a.facts, "preset": a.preset,
            "runtime": a.runtime,
            "caps": {"steps": a.steps, "timeout_s": a.timeout, "max_tokens": 16384}}


def launch(lid: str, wid: str, runtime=None, env=None) -> Path:
    """Start worker.py detached (own session); `env`, when given, is the
    worker process's whole environment (swarm lanes: §7 confinement)."""
    log = lineage.LINEAGES / lid / f"worker-{wid.split('.')[-1]}.log"
    cmd = [sys.executable, str(HERE / "worker.py"), lid, wid]
    if runtime:
        cmd += ["--runtime", runtime]
    with open(log, "a") as out:
        proc = subprocess.Popen(cmd, cwd=str(HERE), start_new_session=True, env=env,
                                stdin=subprocess.DEVNULL, stdout=out, stderr=out)
    lineage.set_pid(lid, wid, proc.pid)
    return log


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="do.py", description="brief + launch a worker")
    ap.add_argument("goal")
    ap.add_argument("--scope", help="the project directory the worker may touch")
    ap.add_argument("--dod", default=DEFAULT_DOD, help="definition of done")
    ap.add_argument("--preset", default="minimal", choices=PRESETS)
    ap.add_argument("--runtime", default=None, choices=("engine", "plain"))
    ap.add_argument("--steps", type=int, default=25, help="step cap (64 for coding)")
    ap.add_argument("--timeout", type=int, default=7200, help="seconds")
    ap.add_argument("--constraints", default="-")
    ap.add_argument("--facts", default="-")
    a = ap.parse_args(argv)
    if a.preset == "think":
        import think
        print(think.think(a.goal))
        return
    if not a.scope:
        ap.error("--scope DIR is required for minimal/standard workers")
    lid = lineage.for_dir()
    wid = lineage.spawn_worker(lid, build_brief(a), timeout_s=a.timeout)
    log = launch(lid, wid, a.runtime)
    print(f"— worker {wid} launched ({a.preset} / {a.runtime or 'engine'}, "
          f"{a.steps}-step cap) on: {a.goal[:80]}\n"
          f"  scope {a.scope}\n  log {log}\n"
          f"  events {lineage.RUNTIME / 'events.jsonl'}\n"
          f"  (reports with evidence; watch with /status; Monitor the events file) —")


if __name__ == "__main__":
    main()
