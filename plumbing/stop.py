#!/usr/bin/env python3
"""stop — /stop <worker_id>: the worker files a PARTIAL report with the
evidence so far (SPEC §5.2). Writes the stop file (the runtime sees it
within a second: engine closes its runtime, plain stops between steps);
with --kill also sends SIGTERM to the worker process (the hard stop).
"""

import os
import signal
import sys

import events  # noqa: E402
import lineage  # noqa: E402
from runtimes import verb_path  # noqa: E402


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: stop.py <worker_id> [--kill]")
        return
    wid, kill = argv[0], "--kill" in argv
    lid = lineage.lineage_of(wid)
    w = lineage.worker_entry(lid, wid)
    if w is None:
        print(f"no worker {wid} (ids look like 20260914-xxxxxx.hhhhhh; see /status)")
        return
    if w["state"] not in ("running", "waiting"):
        raise SystemExit(f"{wid} is {w['state']}; nothing to stop")
    verb_path(lid, wid, "stop").write_text("stop\n")
    events.emit(lid, wid, "stopped", "lead stop" + (" (kill)" if kill else ""))
    if kill and w.get("pid"):
        try:
            os.kill(w["pid"], signal.SIGTERM)
        except ProcessLookupError:
            pass
    print(f"— stop requested for {wid}{' + SIGTERM' if kill else ''}; the PARTIAL "
          "report follows in /status —")


if __name__ == "__main__":
    main()
