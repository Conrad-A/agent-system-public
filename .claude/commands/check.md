---
description: Re-run the checker ladder on a worker's scope and re-stamp its report — /check <worker_id> [R2; R4: cmd; R5: a.py, b.py]
allowed-tools: Bash(python3 plumbing/check.py:*)
---
!`python3 plumbing/check.py $ARGUMENTS`

Relay the output above verbatim. A failing rung is a fact: the report is
now failed whatever it claimed; retry with /resume.
