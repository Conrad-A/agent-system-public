---
description: Answer a waiting worker's ask-back, or brief a fresh worker from a finished one's report — /resume <worker_id> <note>
allowed-tools: Bash(python3 plumbing/resume.py:*)
---
!`python3 plumbing/resume.py $ARGUMENTS`

Relay the output above verbatim. A waiting worker continues its own
session with your answer; a finished one gets a fresh worker briefed from
its report plus your note.
