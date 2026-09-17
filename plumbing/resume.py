#!/usr/bin/env python3
"""resume — /resume <worker_id> <note>: two cases (SPEC §5.2, §4.1).

WAITING worker (ask-back): the note is the answer; the worker process is
blocked on the answer file and continues its own session with it.
FINISHED worker (failed / timed_out / done): the SDK server cannot reopen a
session from a new process, so the lead briefs a FRESH worker: the same
brief plus the previous report's did / open_items / evidence tail and the
note as facts; a new worker id, same runtime and preset.
"""

import sys

import do  # noqa: E402
import events  # noqa: E402
import lineage  # noqa: E402


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2:
        print("usage: resume.py <worker_id> <note...>")
        return
    wid, note = argv[0], " ".join(argv[1:])
    lid = lineage.lineage_of(wid)
    w = lineage.worker_entry(lid, wid)
    if w is None:
        print(f"no worker {wid} (ids look like 20260914-xxxxxx.hhhhhh; see /status)")
        return
    if w["state"] == "waiting":
        lineage.answer(lid, wid, note)
        print(f"— answer delivered to {wid}; it continues its session (watch /status) —")
        return
    if w["state"] == "running":
        raise SystemExit(f"{wid} is running; use /steer for a note, /stop to end it")
    report = lineage._load(lineage.Path(w["report_path"]), {}) if w.get("report_path") else {}
    brief = dict(w["brief"])
    carried = (f"Previous attempt {wid} ({w['state']}): DID {report.get('did', '-')[:400]} "
               f"| OPEN_ITEMS {str(report.get('open_items', '-'))[:300]} "
               f"| EVIDENCE tail {str(report.get('evidence', '-'))[-400:]}")
    brief["facts"] = f"{brief.get('facts') or '-'}\n{carried}\nLEAD'S NOTE: {note}"
    brief["based_on"] = f"resume of {wid}"
    new = lineage.spawn_worker(lid, brief, timeout_s=w.get("timeout_s", 7200))
    log = do.launch(lid, new, brief.get("runtime"))
    events.emit(lid, new, "resumed", f"fresh worker from {wid}: {note[:150]}")
    print(f"— fresh worker {new} briefed from {wid}'s report + your note\n  log {log}\n"
          "  (watch with /status) —")


if __name__ == "__main__":
    main()
