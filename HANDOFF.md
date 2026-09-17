# HANDOFF — v2 build (updated 2026-09-16 · build complete, spec promoted, KICKOFF rewritten as the v2 replication prompt; merged to main 2026-09-16, work continues on main)

Read this first, then the lineage `state.md` (how to find it: CLAUDE.md),
then `SPEC.md` §16 for the step you are on. SPEC.md wins every
conflict. The v1 record is `HANDOFF-v1.md` (history only).

## Where things stand

- Host: Fedora 44. Repo: `~/Desktop/stuff/Project 2/agent-system` (the
  pre-step-1 docs say `~/Desktop/Project 2/…`; the real path has
  `stuff/`). Branch `main` since the 2026-09-16 merge (`exp/v2` = the
  build record), remote `backup` (private GitHub). Body:
  `~/Desktop/agent-system-runtime` (`AGENT_RUNTIME` in `.env`; the v1
  lineages, proposals and logs are still there, untouched).
- STEP 1 DONE 2026-09-14: pins recorded in `configs/stable.md` (Claude
  Code 2.1.271 on Max, `deepseek-flash`, `deepseek-harness-sdk==0.1.5rc1`
  installed in the user site via ensurepip + `pip install --user`);
  `.env` pruned to `DEEPSEEK_API_KEY` + `AGENT_RUNTIME`, mode 600 (the v1
  lines' backup file was deleted 2026-09-14 on Conrad's call); v1 code with no
  replacement deleted (escalate, toggle, standard_chat, watchdog/,
  plugins/) with its tests; `CLAUDE.md` v2; the adaptivemem guard at
  `memory/prompts/`; v1-only docs under `docs/history/`. Suite: 26 tests
  green. The lineage for this directory is seeded in the body
  (`lineages/index.json` + `state.md`).
- Flight test step 1 PASSED 2026-09-14: suite 26 green; `claude -p ping`
  answered; a fresh non-interactive session (`claude -p … --allowedTools
  Read,Glob,Grep`) found the lineage via index.json, read HANDOFF.md +
  state.md, listed open items 2–8 in order and asked to confirm step 2
  before acting. FINDING: a `claude -p` session WITHOUT allowed tools cannot
  read `$AGENT_RUNTIME` (outside the working directory; interactive
  sessions get a permission prompt instead). Step 5's SessionStart hook
  injects state.md so no read is needed; any `claude -p` run that must
  read the body needs `--add-dir` or the tool allowed. Conrad's one
  interactive confirmation session: pending (his step).
- STEP 2 DONE 2026-09-14: SDK claims checked against 0.1.5rc1 and §4.2
  corrected; `clients.py` (stdlib urllib) + `envfile.py`; verify /
  calibrate + their units deleted; `runtimes/{engine,plain}.py`,
  `worker.py` adapter, `compositions/{minimal,standard}.patch.yml`;
  lineage v2 (`lineages/index.json`, `waiting`, ask-back), `do.py`
  detached with `--scope/--preset/--runtime/--steps`, `status.py`,
  `evals/run.py` mechanical graders, `.claude/commands/{worker,status}.md`.
  Suite: 30 green.
- Flight test step 2 PASSED 2026-09-14: the same fizzbuzz brief on
  engine/minimal (worker 3e1bcd), plain (ae3d83) and engine/standard
  (cd1546) each filed a `done` report with evidence; the lead re-ran each
  scope's test itself (exit 0, three times). CoT: the We/Let's vs Let-me
  split SURVIVES on V4.1 — recorded in configs/stable.md; §4.4 stands.
  Found and fixed on the way: the engine's `inputTokens` is the cache-miss
  part only (prompt = inputTokens + cacheReadTokens; context line and
  cost fixed); the `sdk` profile persists sessions as `.jsonl.zstd` (the
  standard patch now sets `compression: none`; the one pre-fix artifact
  was MOVED, not deleted, to `$AGENT_RUNTIME/dsh-home/sessions-zstd-
  archive/`); the first standard rerun (1179b5) failed on that mixed-root
  conflict and filed a failed report as designed. The sandbox probe
  (9b25b4) ended in `waiting`: the worker refused the outside write on
  the brief's scope rule and asked back — ask-back works end to end;
  sdk-minimal sandbox enforcement stays UNTESTED until step 3 answers
  that ask-back with an authorization (it is left in the registry as the
  step-3 resume fixture). `/worker` and `/status` load at session start:
  Conrad's restart plus one try of each is the remaining check.
- STEP 3 DONE 2026-09-14/15: the SDK server speaks only initialize /
  session/prompt / shutdown (no cancel, no steer target, no cross-process
  session reopen), so the verbs were built on that: in-process ask-back
  (the worker blocks on the answer file and continues its own session),
  steer = queued follow-up (engine) / inbox file (plain), stop = stop
  file + `--kill` SIGTERM, resume = answer a waiting worker or brief a
  fresh one from a finished report; `supervisor.py` trip table wired into
  both runtimes (repeat, error loop, stall, scope, budget, context,
  reasoning, finish, checkpoint); `events.py` -> $AGENT_RUNTIME/
  events.jsonl; `status.py --line` as the UserPromptSubmit hook
  (.claude/settings.json); /steer /stop /resume commands; /worker tells
  the lead to Monitor the events file. Suite: 37 green.
- Flight test step 3 (2026-09-14/15): ask-back PASSED live twice (probe
  workers 28e3e7, fe632e: waiting -> answer -> same session -> done, with
  ask/resumed/done events); `repeat` trip PASSED (36a284 stopped at the
  third `date`, PARTIAL); 32k stop PASSED four times (0447e9, 9228bf,
  f764f8, ce2860: trip:context, PARTIAL); the 26k STEER on the engine
  DID NOT LAND — the follow-up is spliced `next-turn` and the running
  turn never sees it (trajectory trace), so on the engine 26k is an
  event only and 32k is the rule (SPEC §5.1 updated); plain's steer
  is unit-tested, not live-tested. Hook: fired live in the session.
  Monitor wake: see the next line. SANDBOX: workspace-write IS enforced
  in sdk-minimal (writes confined: private /tmp, read-only elsewhere;
  reads are not) — scope trip stays as the read fence; no reorder.
- STEP 4 DONE 2026-09-15: `check.py` ladder (R1 proof and R3 lint are
  "not available" on this host and that is never a pass; R2 py_compile,
  R4 the named test command with "no tests ran" = fail, R5 named
  expected files), rungs named in the definition-of-done (`R2; R4: cmd;
  R5: a.py, b.py`), run by the adapter AFTER the worker's final report
  block and before filing (a failing rung = failed report, rung output
  as evidence, no further turn, `trip:ladder` event); `/check
  <worker_id> [rungs]` re-runs on demand, re-stamps report + state and
  writes a `check` event; steer/stop/resume/check print usage with no
  arguments. Order rungs -> report -> self_review reserved for when
  SELF_REVIEW exists. Suite: 41 green.
- Flight test step 4 PASSED 2026-09-15: run 1 (worker ba979e, fizzbuzz +
  a unittest, dod naming R2/R4/R5) came back `done` with all three
  rungs stamped pass; then a failing assertion was planted in the same
  scope and `/check R4` flipped that report to `failed` with the
  traceback as evidence — a rung overruling a done claim.
- STEP 5 BUILT 2026-09-15: `status.py --line` now reads the transcript
  JSONL the UserPromptSubmit hook receives and prints the context size
  (last assistant usage: input + cache read + cache creation — never
  file bytes) with ROTATE AT NEXT BOUNDARY past 100k and ROTATE NOW
  past 128k, plus the state.md age and STATE.MD STALE after N=10
  prompts without a change (counter in lineages/<id>/prompts.json); it
  records the transcript path in lineages/<id>/session.json for
  /rotate. `rotate.py` writes $AGENT_RUNTIME/handoffs/<ts>.md = state.md
  + the transcript's message-text tail and a `rotation` event; `/rotate`
  = rewrite state.md whole, run rotate.py, end the session. Hooks
  (.claude/hooks, ≤10 lines each, copies and prints only, wired in
  .claude/settings.json): SessionStart prints state.md + the newest
  handoff; PreCompact copies state.md + the raw transcript tail to a
  handoff and logs a `compaction` EVENT (worker `lead`). v1 rotate.py
  (dsh discovery, zstd) and its six tests deleted. Suite: 38 green.
- Flight test step 5 PASSED 2026-09-15 (all three parts). Part 1: the
  session that built steps 1-5 ran /rotate at 649k context; handoff
  20260915T021825Z.md + a `rotation` event; the new session was started
  by the SessionStart hook with state.md + that handoff and continued
  without re-asking. Part 2: state.md left alone; the status line
  counted 1..9 and on the 10th prompt read "context 66k · state.md
  changed 5m ago, 10 prompts — STATE.MD STALE" (first prompt of a fresh
  session says "context n/a" — no assistant usage yet; fine). Part 3:
  /compact fired the PreCompact hook: handoff 20260915T022422Z.md
  (state.md + raw transcript tail) and a `compaction` event, worker
  `lead`, in events.jsonl. One defect found and fixed: the hook stamped
  the event `ts` in the handoff form (20260915T022422Z) instead of the
  ISO form events.py uses; now `date -u +%Y-%m-%dT%H:%M:%SZ`, verified
  by running the hook against a throwaway AGENT_RUNTIME. The one
  mis-stamped event stays in events.jsonl (body, never rewritten).
- STEP 6 BUILT 2026-09-15 (commits 3d68000, fde7d3b): `memory/FORMAT.md`
  (the entry rules, from §8.1) and an initial `memory/INDEX.md`;
  `consolidate.py` rewritten = copy the durable files + 7 days of
  trajectories (engine `dsh-home/sessions/*/<wid>/session.v3.jsonl`,
  plain `lineages/<id>/worker-*.log`) + handoffs read-only →
  `$AGENT_RUNTIME/dream/<date>/` → `git status --porcelain` + `git diff
  HEAD` before → `claude -p --model claude-fable-5-1 --allowedTools
  Read,Grep,Glob,Write,Edit` in the copy, prompt on STDIN (the flag is
  variadic and swallowed a positional prompt — found at the flight test)
  → check again → DIFF.md with numbered hunks + the dream's summary.
  Exit non-zero / empty / no CLI = `dream_skipped` event, no DIFF.md
  (SPEC §8.2 got that line); a repo change = `dream_failed` naming the
  paths, nothing reverted. `apply_dream.py <date> [--hunks 2,5]`:
  removed lines of facts/procedures → that file's audit section with the
  dream's reason; resolutions → adjudication rows; style / adjudication
  / prompts / audit-section hunks REJECTED; `dream_applied` event.
  `systemd/consolidate.{service,timer}` (user units, 19:45,
  `Persistent=false`, confirmed by Conrad 2026-09-15 — a night the
  machine was off is skipped, not run late at boot). `/consolidate` command.
  Suite: 42 green.
- Flight test step 6 PASSED 2026-09-15: enable-linger confirmed
  (`Linger=yes`); one real run through the service unit itself
  (`systemctl --user start consolidate.service`, timer still disabled):
  first attempt SKIPPED cleanly on the argv bug (event logged, copy
  kept, no DIFF.md — the skip path worked as specified); after the stdin
  fix: 2 min 7 s, 32 archive files read, DIFF.md with 5 hunks at
  `$AGENT_RUNTIME/dream/2026-09-14-2/`, live memory/ byte-untouched (git
  status clean on memory/). apply_dream exercised hunk by hunk against a
  scratch copy of memory/: 5 applied, the one supersession landed in the
  facts audit section with the dream's reason, one adjudication row; the
  auto-reject of style / audit / prompts hunks is covered by the suite
  (the real diff had no such hunk). Timer then installed and enabled:
  next run Tue 2026-09-15 19:45 EDT. Rulings pending from Conrad: the
  5 hunks of 2026-09-14-2, the v1 proposals 09-04 / 09-05, junk
  archives 0135/0139.
- Gate pass 2026-09-15 DONE: the 5 dream hunks applied (apply_dream, all
  APPLIED); v1 proposals 1-9 DECLINED, 10 PROMOTED (expires 2026-12-01),
  11 DEFERRED to the router chore; archives 0135/0139 deleted. Every
  ruling is a row in memory/adjudication-log.md. Lead rotated here.
- STEP 7 BUILT 2026-09-15: `plumbing/costs.py` — `configs/prices.md`
  rate table (USD per 1M, deepseek-flash peak / off-peak from the DeepSeek
  pricing page read 2026-09-15, the peak spans on one parsed line; a
  `subscription` row for `claude-fable-5-1` at 0) → one row per worker in
  `$AGENT_RUNTIME/costs.jsonl`, appended by worker.py after the report is
  filed (a ledger failure is logged, never undoes the report), priced at
  the tier of the worker's START time (cache miss = whole prompt − cache
  hit; output includes reasoning); the dream's `claude -p` lands as a
  subscription row with seconds (consolidate.py); `costs.py --backfill`
  rows every filed report without one — engine workers from their
  trajectory's usage fields (incl. the `.jsonl.zstd` archive via the 3.14
  stdlib), plain from the report — idempotent; `/status` ends with
  `cost: today (UTC) · 7d · all` plus the dream count. SPEC §10 updated.
  Suite: 44 green.
- Flight test step 7 PASSED 2026-09-15 on this side: backfill wrote 16
  rows from the step 2-6 runs (3e1bcd's pre-fix report said 1315 input,
  the trajectory says 5539 whole prompt / 4224 cached; 9b25b4's 0-call
  report recovered to 2 calls from its trajectory; d6aa9e read from the
  zstd archive; 1179b5 got no row — nothing was billed; ae3d83 plain
  pre-fix has no cache-hit count, so its 8020 prompt tokens are priced as
  misses, an overestimate of at most $0.002); one live engine worker
  (917655, cost.txt brief) wrote a `worker` row identical to a trajectory
  recompute. Ledger: 17 rows, 69 calls, 739,717 prompt tokens (565,248
  cache hit, 174,469 miss), 67,764 output, $0.1370 total, every row PEAK
  (Tue 01:19-03:14 UTC). RECONCILED by Conrad 2026-09-15: the dashboard
  for 2026-09-15 UTC shows $0.13, 71 requests, 808,753 tokens against the
  ledger's $0.137 / 69 / 807,481 — the gap is ae3d83 (priced as all-miss)
  and one unfiled worker. Step 7 CONFIRMED. The dashboard billed the
  01-03 UTC runs at the higher rate, so prices.md is right; SPEC §2 and
  configs/stable.md were reworded 2026-09-15 to say plainly that those
  UTC windows are FULL price and every other hour and the weekend half —
  the old "off-peak = 50% off, peak = ..." sentence read backwards.
- Backend survey 2026-09-15 (13 backends, prices, one DeepSeek-native
  probe): Conrad chose Parallel Search API (`basic`) as PRIMARY and Exa as
  FALLBACK; both keys in `.env` — PLACEHOLDERS as of this writing (the
  values match a your/paste/<> pattern; re-probed twice, names only).
- STEP 8 BUILT 2026-09-15 (six commits after b698853; suite 53 green):
  `configs/prices.md` web-search table + `costs.py` search columns
  (`search_requests`, `search_usd`, folded into `usd`); `tools/
  web_search.py` (one function per backend, Parallel first, ONE retry on
  Exa on error or empty, backend stamped, keys by presence from env or
  `SEARCH_AUTH_FILE`, `--mode` reserved and logged, one JSON line per
  call to `SEARCH_LOG`) + `tools/web_fetch.py` (stdlib GET + html2text,
  GET-only, private hosts refused); `plumbing/sanitize.py` run inside
  `lineage.file_report` (every filed report) + the `sources` report field
  + the SOURCES line for `sources_required` briefs; lane confinement on
  both runtimes (PATH with tools/ first, HOME = the lane dir, the two
  handles, nothing else; the engine prunes the process env — the harness
  ITSELF scrubs credential-shaped and DSH_* names from every shell, which
  is why the keys travel as a mode-600 file) + the supervisor's lane
  fence; `plumbing/swarm.py` (`--plan` validate + launch detached, `--run`,
  `--status`, `--verdict`: gate, fake-parallelism refusal, ≤5 lanes, spend
  cap over tokens + search requests, one successor on a 32k stop,
  dead-lane / serial-collapse trips, reports.md, scorecard.jsonl);
  `/swarm`; `/status` shows sweeps in flight; `configs/data-tiers.md`
  (empty registry). Two fixes to older code on the way: a URL in a
  command matched the supervisor's path regex (`//host/`) and would have
  tripped `scope`; quoted paths with spaces are now scanned whole.
- Flight test step 8 PASSED 2026-09-16 (Conrad's ruling on run 7). Seven
  live sweeps on Conrad's question (US small-business defense contracting
  in 2026: set-asides, CMMC, SBIR/STTR, GSA consolidation; 4 lanes; caps
  $1.00 / 12 calls / 1200 s per lane, never reached — 32k was the binding
  limit). Runs 1-4 (1d46, cf7e, 7d19, 4aa3) found and fixed rule bugs one
  at a time: stall, scope (7 false / 0 true — demoted to an event for
  lanes), dead lane at step 10, serial collapse at 18 s, dead lane charged
  across a succession. Run 5 (874f, verdict 3/5) ran ALL PLAIN: every lane
  logged `ENGINE CANNOT START — falling back to plain` on line 1 (lane
  HOME = lane dir had been applied to the worker PROCESS, not only its
  shell) and nobody read it — changes 5-9: shell-only HOME, the fallback
  surfaced in /status, reports.md, the sweep line and the scorecard, the
  fetch bound. Run 6 (ece1, the engine's first, verdict 1/5): 0 completed,
  every lane tripped 32k at calls 6-8, each exactly one call past its stop
  call; the 26k steer is INERT on the engine (spliced next-turn, the
  running turn never sees it); lanes cat whole 44k-char pages; no notebook
  — changes 10 (lane trips never match content), 11 (brief `report_call`
  5 / successor 3), 13 (PAGE_CAP 12000) and 12, the CONTEXT METER: past
  20k every tool result carries `context Nk of 32k; report by call M`,
  plain as a trailer on the tool message, the engine through the
  @deepseek-ai/dsh-hooks-claude-code bridge (a PostToolUse command hook
  that cats the worker's meter file), mounted by both composition patches
  via the patch parser's `insert` form (an id-only patch only modifies a
  row it finds), minimal also inserting the sdk profile's bash-sandbox
  shell executor the bridge waits for; hooks.json per worker under
  $DSH_HOME/cache/<wid>. On the way: the dream crashed 2026-09-15 on a
  lane's harness cache (non-UTF-8 .cache/pkg/*.node under artifacts/) —
  consolidate.py went text-only with a `dream_failed` event (915958e) and
  the pkg cache moved to $DSH_HOME/cache/<wid>, deleted at close
  (d9f23a9); the ONE CHANGE PER PROMPT agreement (2ce14e4). Diagnostics:
  memory/artifacts/<sweep>/diag_run6.py and diag_run7.py — per-call
  prompt tables, STOP CALL per lane, hook and meter records (trajectory
  METADATA only). RUN 7 (89cf, engine/minimal, 230 s, 58 searches,
  $0.383): the meter landed on every lane (hook/invoked + hook/result
  exit 0 decision pass on every tool call; the line arrives as an inbox
  splice rendered as a user message after the tool result); 3 of 4 lanes
  filed sourced reports (10/6/8 sources), all done-at-cap — the message
  after the meter's M was the answer, but call 5's results added 5-16k
  so every answering prompt was already past 32k; synthesis.md with five
  CONTRADICTIONS; scorecard row, verdict 3/5; gsa answered on time and
  hit max-tokens on a 39k-token answer (finish trip, failed, no
  successor). RESIDUALS — open threads, not gates (Conrad, 2026-09-16):
  (1) the meter starts at 12k and M comes from the projected curve, not
  the fixed 5; (2) the brief's REPORT line states the §4.1 ≤500-token
  contract, bulk to the notebook by path; (3) parse_sources accepts ANY
  LINE CARRYING A URL, not only the dash-bullet form (Conrad, 2026-09-16
  ~22:35 UTC, completing the cut-off ruling; run 7 produced `- url · title
  · claim`, `S1 url · …` and `[S1] url · …`, and the scorecard counted 1
  sourced lane where 3 cited sources);
  also reports.md renders ~1,000 chars of each SOURCES block (the full
  lists are in the report JSONs). Search spend to reconcile against the
  Parallel and Exa dashboards: runs 1-7 = 14/16, 25, 32, 40, 54, 43, 58
  requests plus 3 hand probes.
- PROMOTION DONE 2026-09-16 (Conrad's plan, confirmed ~22:35 UTC):
  `SPEC-v2.md` → `SPEC.md` (canonical), the v1 spec `SPEC.md` →
  `SPEC-v3.1.md` (history, banner added); references swept in the live
  docs, code and tests (SPEC-v2 → SPEC everywhere; the v1-meaning
  `SPEC.md` / `SPEC §` → SPEC-v3.1 in CLAUDE.md, KICKOFF.md, OWNER-NOTES.md,
  configs/toolbox.md, fable.py, ingest.py, the tests, and mechanically in
  HANDOFF-v1.md and FIELD-NOTES.md); docs/history/ and memory/ untouched —
  memory/'s spec references are a GATE item (owner chores). The lineage
  state.md was regenerated first: the run-7 session had ended without
  rotating, so the SessionStart hook injected a stale copy (Provenance
  check against `git log -1` caught it).
- KICKOFF REWRITTEN 2026-09-16 (Conrad's plan plus six step-block
  additions): KICKOFF.md is the v2 replication prompt — one body, the two
  host blocks generated from it and differing only in the four host lines;
  the lessons folded into the step blocks (the status line at step 1; the
  SDK surface check, the real-payload adapter test and the fallback in
  /status at step 2; the research-brief supervisor test and no rule
  matching inside content at step 3; the working agreements binding from
  step 1 — one change per prompt, past 128k only state.md and /rotate, a
  by-hand harness boot before any runtime commit; stdin and the text-only
  copy at step 6; the meter and 3-7k growth per call at step 8; the run-7
  residuals as the first post-build work). FIELD-NOTES.md gained the v2
  runtime section the prompt points at (pkg cache under HOME, the hooks
  bridge, the mount, the binary recipes). MERGED 2026-09-16: the two
  KICKOFF fixes from Conrad's read (153ccd4), main fast-forwarded to it,
  suite 63 green on main, pushed; work continues on main and exp/v2
  stays as the build record. FOUND AT THE MERGE: the suite went red on
  main because the hooks' executable bit is not tracked (core.fileMode
  is false; both hooks are mode 644 in git on every branch; the exp/v2
  tree had +x set by hand at step 5) — restored on disk for the green;
  settings.json runs them via `sh`, so only the test cares; the mode
  is recorded in git since the same night (`git update-index
  --chmod=+x`, mode 100755 on both; a fresh clone gets +x). On
  evidence: the residual threads
  above (parse_sources first); the search-spend reconciliation (Conrad,
  dashboards); the README/OPERATIONS rewrite.
- PUBLIC COPY PUBLISHED 2026-09-17 at
  `https://github.com/Conrad-A/agent-system-public`: ONE orphan commit
  b2d1a9e "agent-system v2" squashed from main at 696157b — 97 files,
  OWNER-NOTES.md and DOMAINS-owner.md removed, LICENSE (MIT, 2026 Conrad
  Albarracin) added, personal memory entries emptied per KICKOFF step 1
  with the system facts and procedures kept, audit clean (identifier and
  key-shape hits both zero), suite 64 green in the worktree. The local
  `public` branch is kept, so a republish is a fresh orphan squash from
  main plus `git push --force public public:main`; force is fine on the
  PUBLIC remote only, NEVER on backup. The first squash (8272e4b,
  2026-09-16) was discarded: it predated the kickoff-line fix and it
  carried the owner's Linux account name in the enable-linger chore,
  which that session's grep missed because it searched for the full email
  address and the line has no @-domain. Fixed on main at 696157b; the
  placeholder is `$USER` everywhere in the kit (KICKOFF.md:28 and :78,
  setup/03-agent-host.sh:48, agent-system-diagram.html:698, HANDOFF.md).
- CREDENTIAL LEAK AND ROTATION 2026-09-17: diagnosing the push failures,
  the lead printed `~/.git-credentials` through a masking sed that did
  not match, so a live fine-grained PAT reached the transcript and the
  session log; Conrad rotated it the same hour and the exposed token is
  dead. Two rules out of it, both in the working agreements below: never
  read or print that file from a command, and a credentials line MUST
  end in `@github.com` or the store helper never matches the entry —
  git then falls through to ANONYMOUS access, which reads a public repo
  fine and fails every push, so a clean `git ls-remote` against a public
  repo proves NOTHING about the token.

## Open items — the build (SPEC §16; flight test in brackets)

2 (as planned before the build). WORKERS: `plumbing/runtimes/{engine,plain}.py`, `worker.py` as the
   adapter, `runtimes/__init__.py` selection (flag > `WORKER_RUNTIME` >
   engine; loud, narrow fallback), `compositions/` (minimal, standard:
   sandbox tightened, workspaceRoot from the brief, compaction off),
   presets (think / minimal / standard), ask-back (`waiting` state +
   answer file), `clients.py` (DeepSeek; GLM reserved), `/worker`,
   `/status`. Also in this step: FIRST confirm every SDK claim in SPEC
   §4.2 and MIGRATION §1 against the installed 0.1.5rc1 (class and
   method names, turn/end reasons, sandbox policy, the Minimal prompt
   string) and correct §4.2 before building on it; delete `verify.py`,
   `calibrate.py`, `systemd/calibrate.*` and their tests once
   `clients.py` exists; `think.py` becomes the `think` preset on
   `deepseek-flash`; rewrite `evals/run.py` (it imports from a
   `plumbing/verifier/` directory that never existed — broken since v1,
   left alone in step 1 on Conrad's call); `lineage.py` adopts
   `lineages/index.json` (directory → lineage id) and drops the throne
   and window fields; `do.py` launches DETACHED (setsid) and takes
   `--preset` / `--runtime`; a tiny stdlib `.env` loader (nothing exports
   `.env` today — the shell does not source it; `lineage.py` only falls
   back to the v1 default path); `status.py` flattens multi-line `did`
   fields in "recent reports".
   [one real brief on EACH runtime returns a report with evidence; the
   §2 CoT flight test: same brief on minimal and standard, read the two
   reasoning blocks ONCE, record in configs/stable.md whether the
   We/Let's vs Let me split survives on V4.1]
2. WORKERS — DONE 2026-09-14 (see Where things stand).
3. SUPERVISION — DONE 2026-09-15 (see Where things stand).
3 (as planned). SUPERVISION: `supervisor.py` trip table (§5.1), `runtime/events.jsonl`,
   `Monitor` wake (the tool EXISTS in CLI 2.1.271 — use it; the
   UserPromptSubmit status hook is the safety net), `steer` / `stop` /
   `resume`, `.claude/hooks` UserPromptSubmit → `status.py --line`. Hooks
   and slash commands load at session START: restart before their flight
   test. Learned at step 2: steer = `session/prompt` with a current-turn
   target and stop = `session/cancel` exist as strings only (confirm the
   params live); there is no pause verb — pause = cancel, resume = a new
   prompt on the same session id; the engine's `on_notification` stream
   and the plain log's `CONTEXT call n: prompt_tokens=` lines are the
   supervisor's feed; first resume test = answer the waiting probe worker
   9b25b4 with an authorization (that also settles sdk-minimal sandbox
   enforcement).
   [an ambiguous brief triggers ask-back; a looping brief trips `repeat`;
   resume a paused engine worker; a long brief gets the 26k wrap-up steer
   and stops with a report; a brief that ignores it is force-stopped at
   32k with a PARTIAL]
4. CHECKER LADDER — DONE 2026-09-15 (see Where things stand).
   [a coding brief with tests; a planted failure is rejected by a rung]
5. ROTATION — DONE 2026-09-15 (see Where things stand).
5 (as planned). ROTATION: status line context size (ROTATE AT NEXT BOUNDARY past 100k,
   ROTATE NOW past 128k; from the transcript's last `usage`, never file
   bytes) + STATE.MD STALE after N=10 unchanged prompts; `/rotate`
   (rewrite state.md, handoff to `runtime/handoffs/<ts>.md`, end);
   SessionStart injects state.md + the newest handoff (replaces the
   by-hand read in CLAUDE.md); PreCompact backstop + `compaction` EVENT.
   [/rotate mid-task → the new session continues without re-asking; N
   idle prompts → STALE shows; a forced compaction → the handoff exists
   and the EVENT is logged]
6. DREAM — BUILT + flight test PASSED 2026-09-15 (see Where things
   stand); the owner gate pass (dream hunks, v1 proposals, archives) is
   pending Conrad's rulings. As planned:
   `memory/FORMAT.md` (from §8.1) + an initial `memory/INDEX.md`;
   `consolidate.py` copy → `claude -p --model claude-fable-5-1
   --allowedTools Read,Grep,Glob,Write,Edit` run IN the copy with
   `memory/prompts/dream.md` → DIFF.md; `apply_dream.py` (removed lines →
   audit section; style / adjudication / audit / prompts hunks
   auto-rejected); the before/after `git status --porcelain` + `git diff
   HEAD` check (any change outside the copy = night FAILED, no DIFF.md,
   nothing reverted); `systemd/consolidate.{service,timer}` at 19:45
   (`Persistent=false`; `claude` on the unit's PATH, logged in). Owner:
   `loginctl enable-linger` BEFORE this step; rule by hand on
   `$AGENT_RUNTIME/proposals-20260904.md` and `proposals-20260905.md`;
   the junk archives `memory/archives/20260904-01{35,39}-dsh-main.txt`.
   [one run produces a diff applied hunk by hunk; live memory/ unchanged
   until applied]
7. COST LEDGER — DONE 2026-09-15 (see Where things stand); the
   dashboard reconciliation is Conrad's. As planned: `costs.py` (usage
   fields → `runtime/costs.jsonl`), `configs/prices.md` rate table
   (editable), `/status` cost line.
   [rows reconcile with the DeepSeek dashboard]
8. SWARM — DONE 2026-09-16 (built 2026-09-15; flight test PASSED with
   run 7 — see Where things stand). As planned:
   `tools/web_fetch.py`, `tools/web_search.py` (backend and key
   chosen at this step), `swarm.py` launched detached, `/swarm`, the
   research-report contract, the scorecard, `configs/data-tiers.md`
   (empty registry, SPEC §9).
   [a 4-lane question returns four sourced reports, one synthesis with a
   CONTRADICTIONS section, and a scorecard row]
Later, on evidence: check mode · second worker model · Tailscale · data
tiers waking · Langfuse (SPEC §15).

## Open items — docs and housekeeping

- `README.md` and `OPERATIONS.md` are still v1 prose; rewrite after
  step 3 when the v2 shape is real (MIGRATION §2). `FIELD-NOTES.md`: prune
  the access-layer sections to an appendix and add the V4.1 / SDK notes
  (profiles, patch files, the zstd session store, `DISABLE_AUTOUPDATER=1`
  for the CLI pin) at the same time — the v2 runtime section (pkg cache,
  hooks bridge, mount, binary recipes) landed 2026-09-16 with the KICKOFF
  rewrite; the prune and the profile notes remain. `setup/03-agent-host.sh` → `setup/host.sh` (Claude
  Code, python deps, SDK pin, timer install) at step 6 with the timer.
- `memory/prompts/throne.md` and `architect.md` are v1 prompts kept with
  memory/ (owner's call). The throne role is gone in v2; `architect.md`
  needs a v2 agenda (cost ledger, scorecards, dream diffs, adjudication
  log — SPEC §10) before the first weekly session.
- Promotion DONE and KICKOFF rewritten 2026-09-16 (see Where things
  stand). MERGED to `main` 2026-09-16 (fast-forward at 153ccd4, suite
  green on main, pushed); work continues on main.

## Owner chores (not build steps)

- `loginctl enable-linger $USER` before step 6.
- Check that snapper covers /home (needs root; SPEC §11).
- Delete `~/Desktop/_to_delete/` and the four scratch files on the
  Desktop; the RAM is due for replacement.
- Body cleanup: `$AGENT_RUNTIME/lineages/<worker_id>/` is an EMPTY directory
  created 2026-09-15 02:13 UTC by a verb run with the literal placeholder
  (found by /status at step 7); `rmdir` it — outside the repo, so your call.
- Router forwards 80/443/3478 from v1: close them if still open
  (MIGRATION §3); also the TCP 8080 rule (gate ruling 2026-09-15 on v1
  proposal 11 — the 2026-08-28 fact fragment is superseded once checked).
- Revoke the v1 Z.ai (GLM) and Langfuse keys: their `.env` lines were
  removed and the backup deleted on 2026-09-14.
- Keep `DISABLE_AUTOUPDATER=1` set on this host so the `claude` pin in
  configs/stable.md holds (set 2026-09-14).
- Reconcile the search spend on the Parallel and Exa dashboards against
  the ledger (runs 1-7: 14/16, 25, 32, 40, 54, 43, 58 requests, plus 3
  hand probes); the keys have been real since run 1 (2026-09-15).
- GATE (rule with the 2026-09-15 dream diff, 8 hunks): the promotion left
  memory/ untouched, so these lines still cite the v1 spec by bare section
  number (v3.1 sections — `SPEC §` now reads as the v2 spec): style.md:1
  (§3d), :14 (§3c); facts.md:1 (§3d), :114 (§8); procedures.md:1 (§3d);
  adjudication-log.md:1 (§3d); prompts/adaptivemem.md:1 (§3d);
  prompts/architect.md:8 (§8); prompts/throne.md:1 (§2d, §3c), :5
  (`SPEC.md`), :12 (§3c). And these name the renamed file `SPEC-v2`:
  INDEX.md:1, :29; FORMAT.md:1, :3; procedures.md:26; prompts/dream.md:9.
  Per line: rewrite to `SPEC-v3.1 §…` / `SPEC §…`, or leave (throne.md and
  architect.md are v1 prompts kept as history).

## Lessons for the KICKOFF (folded into KICKOFF.md 2026-09-16; kept as the record)

- Loud fallback nobody reads: every sweep lane in runs 1-5 logged `ENGINE
  CANNOT START — falling back to plain` on line 1 and the ledger's runtime
  column said `plain (fallback — …)` from run 1; five flight tests were
  judged without anyone reading either. Lessons: a fallback must surface
  where the lead looks (/status, reports.md, the sweep status line, the
  scorecard row), never only in a log; the first diagnostic after any run
  is `head -1` of every worker log; a decision recorded as "lane HOME =
  lane dir" must say which process. (Ruling on run 5, 2026-09-15; fixed by
  changes 5 and 6 of the step-8 flight test.)

## Working agreements (learned, non-negotiable)

Those in CLAUDE.md, plus: sandbox sessions may leave `.git/*.lock` — run
`rm -f .git/*.lock` before committing locally; keep SPEC.md,
MIGRATION.md and this file in sync when a decision lands; hard-won facts
go through the gate into `memory/`, never only into this file; NEVER
read or print `~/.git-credentials` from a command (a masking regex that
fails to match prints the secret — derive its shape with `grep -c` and
`wc` only), and a credentials line without the `@github.com` suffix makes
git fall through to anonymous access, so reads of a public repo succeed
while every push fails.

## Kickoff line for a fresh session

"Read HANDOFF.md and the lineage state.md, then SPEC.md §16; the repo
is at ~/Desktop/stuff/'Project 2'/agent-system on the Fedora host, branch
main. Continue at the NEXT open item; confirm the step before acting."
