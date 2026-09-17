# data-tiers.md — the registry of OPEN workspace roots (SPEC §9)

Data tiers are a property of the WORKSPACE, not the task. Every directory a
worker may operate in is `open` or `private`; only roots listed here are
open, everything else is private by default. A TRAINING-TIER model (a
provider that may train on traffic) may be spawned only into an open root;
the plumbing refuses anything else — no brief, flag or lead judgment
overrides it. This repo is NOT open (memory/ holds personal facts), and
neither is `$AGENT_RUNTIME`.

Dormant until a training-tier model exists (none is configured: the only
worker model is `deepseek-flash` through the paid API, stamped `private`
on every report and ledger row). The fences in §9 are built when the first
such model arrives, together with the one unit test that spawns a
training-tier worker told to read outside its root and asserts refusal.

| open root (absolute path) | purpose | added | expires |
|---|---|---|---|

(empty — nothing is open)
