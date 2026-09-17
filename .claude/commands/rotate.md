---
description: Rotate this session — rewrite state.md whole, write the handoff, end the session (SPEC §3)
allowed-tools: Bash(python3 plumbing/rotate.py:*), Read, Write
---
!`python3 plumbing/rotate.py --paths`

Rotate now, in this order:
1. Regenerate the state file WHOLE at the state.md path above with the
   Write tool: decisions, open threads, current focus — decision-relevant
   compression, never append or patch. This is the one moment you must.
2. Run `python3 plumbing/rotate.py` and relay its output (the handoff path).
3. Tell Conrad to end this session and open a new one in this directory;
   the SessionStart hook injects state.md and the newest handoff, and the
   new session continues without re-asking.
