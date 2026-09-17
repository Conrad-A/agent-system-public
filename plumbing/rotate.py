#!/usr/bin/env python3
"""rotate — /rotate: the handoff for a lead rotation (SPEC §3).

The LEAD rewrites state.md whole first (the one moment it must); this
script then writes $AGENT_RUNTIME/handoffs/<timestamp>.md = state.md +
the raw tail of the session transcript (the last RAW_TAIL_CHARS of
message text), logs a `rotation` event, and says to end the session. The
next session's SessionStart hook injects state.md and the newest handoff.
The transcript path comes from lineages/<id>/session.json, recorded by
the status hook on every prompt.

Usage:  python3 plumbing/rotate.py            write the handoff
        python3 plumbing/rotate.py --paths    print the state.md path + handoffs dir
"""

import json
import sys
import time
from pathlib import Path

import events  # noqa: E402
import lineage  # noqa: E402

RAW_TAIL_CHARS = 24000            # ~6-8k tokens of recent conversation, verbatim
HANDOFFS = lineage.RUNTIME / "handoffs"


def transcript_text(path) -> str:
    """User / assistant text blocks of a transcript JSONL, in order."""
    out = []
    for line in open(path, errors="replace"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        role = o.get("type")
        if role not in ("user", "assistant"):
            continue
        content = (o.get("message") or {}).get("content")
        if isinstance(content, str):
            out.append(f"[{role}] {content}")
        elif isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "text" and b.get("text"):
                    out.append(f"[{role}] {b['text']}")
    return "\n".join(out)


def write_handoff(lid: str, transcript_path=None) -> Path:
    HANDOFFS.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    state = lineage.state_path(lid)
    tail = ""
    if transcript_path and Path(transcript_path).exists():
        tail = transcript_text(transcript_path)[-RAW_TAIL_CHARS:]
    body = (f"# handoff {ts} — lineage {lid}\n\n"
            f"## state.md (as rewritten by the lead before rotating)\n\n"
            f"{state.read_text() if state.exists() else '(no state.md)'}\n\n"
            f"## raw transcript tail (last ~{RAW_TAIL_CHARS} chars of message text)\n\n"
            f"{tail or '(no transcript recorded — the status hook had not run)'}\n")
    p = HANDOFFS / f"{ts}.md"
    p.write_text(body)
    events.emit(lid, "lead", "rotation", f"handoff {p.name}")
    return p


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    lid = lineage.for_dir()
    if "--paths" in argv:
        print(f"state.md: {lineage.state_path(lid)}\nhandoffs: {HANDOFFS}")
        return
    sess = lineage._load(lineage._lineage_dir(lid) / "session.json", {})
    p = write_handoff(lid, sess.get("transcript_path"))
    print(f"— handoff written: {p}\n  End this session now and open a new one in this directory; "
          "the SessionStart hook injects state.md and this handoff. —")


if __name__ == "__main__":
    main()
