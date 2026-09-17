# procedures.md — procedural memory (SPEC §3d)

Learned how-tos. Written only through the curation gate. Neutral affect
always: "X failed on Y because Z" — never emotional framing (MemTrap rule).

Entry format:
```
- WHEN <situation>: <do this>. [learned: YYYY-MM-DD] [evidence: <what showed it>]
```

## Procedures

- WHEN a delegation flight test fails: check the INPUT side first (model
  string, mode defaults, discovery/filter picking the wrong file) before
  suspecting the model. [learned: 2026-09-04] [evidence: all four
  delegation failures on 2026-09-04 were input-side — fable model string
  (dotted vs hyphens), co-judge thinking default (empty reply scored 1.0),
  rotate --auto distilling a stats file, then a package.json. Proposed by
  the 2026-09-04 consolidation pass; gate-approved by Conrad same day.]

- WHEN an engine worker must change course mid-turn: do not rely on
  /steer — the SDK queues it for the next turn. Use the 32k stop (stop
  file, `--kill` for SIGTERM) and /resume with a note; treat the 26k mark
  as an event only. [learned: 2026-09-14] [evidence: trajectory f764f8
  shows the 26k steer spliced with target next-turn and canceled while the
  next call proceeded unaware; SPEC-v2 §5.1/§4.3 record it]

- WHEN a worker asks back (WAITING): answer through /resume <id> <answer>
  so the still-running worker process reads the answer file. Never try to
  reopen its SDK session from a new process. [learned: 2026-09-14]
  [evidence: worker-9b25b4.log step 10 — JsonRpcError "session already
  exists" on the first resume attempt; ask-back then passed live twice]

- WHEN a worker needs its outputs seen by the host: put them in the scope.
  sdk-minimal makes /tmp a private tmpfs and the rest of the tree
  read-only; a write elsewhere fails or silently vanishes.
  [learned: 2026-09-14] [evidence: worker-fe632e.log step 23 "Read-only
  file system"; the /tmp probe returned exit 0 but nothing landed]

- WHEN adding a runtime composition or sharing a dsh-home sessions root:
  match the compression mode of what already sits there (the `sdk`
  profile writes .jsonl.zstd) or use a separate root; give the standard
  composition the `headless` permission preset. [learned: 2026-09-14]
  [evidence: worker-1179b5.log step 1 refused the root over one .zstd
  artifact; cd1546 trajectory boots only after permission/preset headless]

- WHEN a checker rung relies on a tool's exit code: also match the
  tool's text output, because the code differs across supported versions.
  [learned: 2026-09-15] [evidence: unittest's exit 5 on "no tests ran"
  exists only from Python 3.12; on 3.10 an empty scope passed R4 until
  "Ran 0 tests" was matched too (Conrad's fix, one commit before step 5)]

- WHEN reporting the lead's context size: read the last assistant usage in
  the transcript JSONL (input + cache_read + cache_creation), never file
  size. [learned: 2026-09-15] [evidence: after a compaction the number
  drops while the JSONL keeps growing; owner decision at step 5]
