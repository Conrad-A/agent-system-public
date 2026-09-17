#!/usr/bin/env python3
"""worker — the adapter: brief -> runtime -> report (SPEC §4.1, §4.2).

Usage:  python3 plumbing/worker.py <lineage_id> <worker_id> [--runtime engine|plain]
do.py spawns this detached. The brief is read from the lineage registry
(spawn_worker stored it); the report is filed through lineage.file_report:
state `done` only when the runtime finished AND evidence exists, otherwise
`failed` with a PARTIAL report. Ask-backs are handled inside runtimes.run
(the process blocks on the answer file, then continues its own session).
SIGTERM = the hard stop: the report on disk becomes the PARTIAL. The text
log at $AGENT_RUNTIME/lineages/<lid>/worker-<hex>.log is the supervisor's
feed for plain and a step / context summary for the engine (whose full
trajectory is the runtime's session JSONL, path stamped in the report).
"""

import signal
import sys

import costs  # noqa: E402
import events  # noqa: E402
import lineage  # noqa: E402
import runtimes  # noqa: E402


class Stopped(RuntimeError):
    """SIGTERM arrived (the lead's hard stop)."""


def _on_sigterm(signum, frame):
    raise Stopped("stopped by SIGTERM")


def main(lid: str, wid: str, runtime=None) -> None:
    d = lineage.LINEAGES / lid
    d.mkdir(parents=True, exist_ok=True)
    logf = d / f"worker-{wid.split('.')[-1]}.log"

    def log(line: str) -> None:
        with open(logf, "a") as f:
            f.write(line + "\n")

    brief = lineage.worker_brief(lid, wid)
    signal.signal(signal.SIGTERM, _on_sigterm)
    try:
        report = runtimes.run(brief, lid, wid, log, runtime=runtime)
        has_evidence = report.get("evidence", "-") not in ("", "-")
        unanswered = str(report.get("open_items", "")).startswith(lineage.ASK_PREFIX)
        state = "done" if report.get("complete") and has_evidence and not unanswered else "failed"
    except (Exception, Stopped) as e:  # noqa: BLE001 — a crash must still file a report
        log(f"WORKER ERROR: {e!r}")
        report = runtimes.build_report(
            brief, f"worker error: {e}", [], runtime=runtime or runtimes.select(),
            complete=False, cost=dict(runtimes.EMPTY_COST))
        state = "failed"
    path = lineage.file_report(lid, wid, report, state=state)
    events.emit(lid, wid, state, report.get("did", "")[:200])
    started = (lineage.worker_entry(lid, wid) or {}).get("started") or lineage._now()
    try:                                     # step 7: one ledger row per worker
        costs.record_worker(lid, wid, report, started, preset=brief.get("preset"),
                            searches=costs.search_usage(brief.get("search_log")))
    except Exception as e:  # noqa: BLE001 — the report is filed; the ledger never undoes that
        log(f"COST LEDGER ERROR: {e!r}")
    log(f"REPORT FILED: {state} -> {path}")


if __name__ == "__main__":
    argv = sys.argv[1:]
    rt = None
    if "--runtime" in argv:
        i = argv.index("--runtime")
        rt = argv[i + 1]
        del argv[i:i + 2]
    main(argv[0], argv[1], rt)
