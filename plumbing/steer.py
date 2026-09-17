#!/usr/bin/env python3
"""steer — /steer <worker_id> <message>: a note the worker sees before its
next model call (SPEC §5.2). Engine: queued as a follow-up prompt on the
worker's session by its watcher thread; plain: read before the next call.
"""

import sys

import events  # noqa: E402
import lineage  # noqa: E402
from runtimes import verb_path  # noqa: E402


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2:
        print("usage: steer.py <worker_id> <message...>")
        return
    wid, note = argv[0], " ".join(argv[1:])
    lid = lineage.lineage_of(wid)
    w = lineage.worker_entry(lid, wid)
    if w is None:
        print(f"no worker {wid} (ids look like 20260914-xxxxxx.hhhhhh; see /status)")
        return
    if w["state"] not in ("running", "waiting"):
        raise SystemExit(f"{wid} is {w['state']}; steer applies to running workers")
    verb_path(lid, wid, "steer").write_text(note.strip() + "\n")
    events.emit(lid, wid, "steer", note[:200])
    print(f"— steer queued for {wid} ({len(note)} chars); it lands before the "
          "worker's next model call —")


if __name__ == "__main__":
    main()
