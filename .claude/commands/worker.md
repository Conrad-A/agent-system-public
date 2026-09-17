---
description: Brief a DeepSeek worker and launch it detached — args go to plumbing/do.py ("goal" --scope DIR [--preset minimal|standard|think] [--runtime engine|plain] [--steps N] [--dod "..."])
allowed-tools: Bash(python3 plumbing/do.py:*)
---
!`python3 plumbing/do.py $ARGUMENTS`

Relay the output above to Conrad verbatim (worker id, scope, log path).
Then start a Monitor on the events file printed above, so you are woken
when the worker asks back, trips a rule, or finishes:
`tail -n 0 -F <events path> | grep --line-buffered -E '"event": "(ask|trip|done|failed|stopped|check)'`
Do NOT read the worker's log or trajectory — briefs and reports only
(SPEC §3). On an event: /status, then /resume, /steer or /stop.
