# facts.md — semantic memory (SPEC §3d)

Rules: updated IN PLACE through the curation gate only. Supersede, never
erase — losing facts move to the AUDIT section with when/why. Every entry
carries the full tag line. Never re-distilled through handoffs.

Entry format:
```
- FACT: <the fact, one or two lines>
  [src: user-said | worker-inferred | web-claimed | doc:<file>]
  [true-since: YYYY-MM-DD] [learned: YYYY-MM-DD] [scope: <context or global>]
  [expires: YYYY-MM-DD | -] [session: <id>]
```

## Facts

(Audited/superseded entries live in the "Audit — superseded entries"
section at the END of this file; rulings in memory/adjudication-log.md.)

### v2 build (lineage 20260914-30ee9c, steps 1-5, 2026-09-14/15)

- FACT: deepseek-harness-sdk 0.1.5rc1 server surface = initialize,
  session/prompt, shutdown only. No cancel verb, no mid-turn steer target:
  follow-ups are spliced with target `next-turn` and never reach a running
  turn. A session cannot be reopened by a new process ("session already
  exists"). Consequences built into v2: engine steer at 26k is an EVENT for
  the lead, 32k stop is the rule; ask-back = the worker process blocks on
  the answer file inside its own session; resume of a finished worker =
  fresh worker briefed from the report plus the lead's note.
  [src: worker-inferred (trajectory f764f8 splice target next-turn,
  outcome canceled; worker-9b25b4.log step 10 "already exists")]
  [true-since: 2026-09-14] [learned: 2026-09-14] [scope: v2 runtimes]
  [expires: -] [session: 20260914-30ee9c]

- FACT: sdk-minimal sandbox confines WRITES, not reads: scope writable,
  /tmp is a private tmpfs that never reaches the host, everything else
  read-only ("Read-only file system" on a home write; home remains
  readable). So the scope trip in supervisor.py stays as the READ fence.
  [src: worker-inferred (worker-fe632e.log step 23)] [true-since: 2026-09-14]
  [learned: 2026-09-14] [scope: v2 runtimes] [expires: -]
  [session: 20260914-30ee9c]

- FACT: SDK profile quirks: the `sdk` profile writes sessions as
  .jsonl.zstd and a backend configured `compression: none` refuses a root
  containing one (the standard patch sets compression none; a pre-fix
  artifact lives in dsh-home/sessions-zstd-archive/). The standard
  composition needs an explicit `headless` permission preset to boot.
  Composition = profile + patch files, `dsh_home` mandatory; no `cordis=`
  argument, no `str_replace_editor` in sdk-minimal, no DSH_SESSION_DIR.
  The engine's inputTokens counts cache misses only — add cacheReadTokens
  for the context figure the 32k rule needs.
  [src: worker-inferred (worker-1179b5.log step 1; cd1546 trajectory
  seq 0 permission/preset headless; SDK source read at step 2)]
  [true-since: 2026-09-14] [learned: 2026-09-14] [scope: v2 runtimes]
  [expires: -] [session: 20260914-30ee9c]

- FACT: Reasoning content is replayed into every later request when tools
  are present: a deliberating sdk-minimal worker adds ~3k tokens per step
  on top of tool output, so the 26k→32k window is about one step wide on
  such briefs. Both `sdk` and `sdk-minimal` send reasoningEffort max,
  maxTokens 16384; the CoT split (minimal reasons every call, standard
  often zero reasoning tokens) is catalog-driven and recorded in
  configs/stable.md.
  [src: worker-inferred (request/header blocks of the minimal and standard
  trajectories)] [true-since: 2026-09-14] [learned: 2026-09-14]
  [scope: v2 runtimes] [expires: -] [session: 20260914-30ee9c]

- FACT: unittest exits 5 on "no tests ran" only on Python ≥ 3.12; the kit
  supports ≥ 3.10, so check.py's R4 also fails on "Ran 0 tests" in the
  output. R1 (proof) and R3 (lint) are "not available" on this host and
  that is never a pass; nothing gets installed mid-run (owner host
  decision).
  [src: user-said] [true-since: 2026-09-15] [learned: 2026-09-15]
  [scope: v2 checker ladder] [expires: -] [session: 20260914-30ee9c]

- FACT: The lead's context figure = input + cache_read + cache_creation of
  the LAST assistant usage in the Claude Code transcript JSONL, never file
  bytes: a compaction makes it drop while the file keeps growing. Status
  line flags STATE.MD STALE at N=10 prompts without a state.md change.
  First /rotate happened 2026-09-15 at 649k context.
  [src: user-said + worker-inferred] [true-since: 2026-09-15]
  [learned: 2026-09-15] [scope: v2 rotation] [expires: -]
  [session: 20260914-30ee9c]

## Audit — superseded entries (write contract §3d: supersede, never erase)

(none yet)
