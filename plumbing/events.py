"""events — the lead's wake feed: $AGENT_RUNTIME/events.jsonl (SPEC §5).

One JSON object per line: ts, lineage, worker, event, detail. Events:
trip:<rule>, ask, checkpoint, done, failed, resumed, steer, stopped,
compaction (worker `lead`, written by the PreCompact hook at step 5),
dream / dream_skipped / dream_failed / dream_applied (worker `lead`,
step 6 — consolidate.py and apply_dream.py).
The lead runs a Monitor on this file; the supervisor and the adapters
write it; nothing here ever reads a transcript.
"""

import json
import time

import lineage  # noqa: E402

EVENTS = lineage.RUNTIME / "events.jsonl"


def emit(lineage_id: str, worker_id, event: str, detail="") -> dict:
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "lineage": lineage_id, "worker": worker_id, "event": event,
           "detail": str(detail)[:500]}
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with open(EVENTS, "a") as f:
        f.write(json.dumps(row) + "\n")
    return row
