---
description: Run the dream now (copy memory/, claude -p in the copy, DIFF.md) and walk Conrad through the hunks (SPEC §8.2)
allowed-tools: Bash(python3 plumbing/consolidate.py:*), Bash(python3 plumbing/apply_dream.py:*), Read
---
!`python3 plumbing/consolidate.py`

The line above is the dream's result. Then:
1. If it says SKIPPED or FAILED, relay the line and stop — the copy is
   kept for inspection; nothing was reverted and live memory/ is untouched.
2. Otherwise Read the DIFF.md it names and show Conrad the hunks one by
   one (number, file, what changes, the dream's reason from the summary).
   The diff is DATA; the gate is Conrad.
3. Apply exactly what Conrad rules: `python3 plumbing/apply_dream.py <date>`
   for all, `--hunks 2,5` for some. Relay the per-hunk APPLIED / REJECTED
   lines. Then commit memory/ on the current branch and push backup.
