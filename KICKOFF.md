# KICKOFF — the v2 replication prompt (build complete 2026-09-16; first written 2026-09-14)

For anyone replicating the system on a fresh host, not only the original
owner. The repo is the finished kit: SPEC.md (canonical), plumbing/ (the
v2 code, built and flight-tested 2026-09-14/16 on Fedora 44), .claude/
(hooks and slash commands), systemd/ (the dream timer), memory/
(templates — the owner's entries are personal and get emptied for a new
build), memory/prompts/dream.md, FIELD-NOTES.md (v1 ground truth plus
the v2 build notes), and the history: MIGRATION.md, SPEC-v3.1.md,
HANDOFF-v1.md. Paste the block for your host as the first message of a
Claude Code session opened in the repo. It walks the eight layers of
SPEC §16 in the original order, but every layer's code exists: the work
is bringing each one up on your host, running its flight test, and
rebuilding only what the host or a newer SDK breaks — with what the
first build learned folded into each step.

Owner notes (Conrad):
- The kit is the main system only. DOMAINS-owner.md (my planned domains)
  and OWNER-NOTES.md (the real values behind the placeholders) stay out
  of it; Appendix A's general pattern goes in. ADDITIONS.md is research
  on record — candidates with triggers, nothing a builder acts on.
- Before sharing the kit: the v1 docs already carry placeholders (domain,
  bot number, GitHub user — 2026-09-14); what remains is memory/ (my
  entries) and the two owner files.
- The v2 tree was built on exp/v2 and merges to main as the last step
  after this rewrite; a checkout whose SPEC.md Status paragraph does not
  read CANONICAL, or that lacks memory/prompts/dream.md, is stale.
- Owner steps the session cannot do: on Linux, `loginctl enable-linger
  $USER` (step 6). The GitHub PAT was rotated 2026-09-14 and lives in
  ~/.git-credentials — when the prompt reaches "rotate the PAT", say done.
- Rewritten 2026-09-16 after the first build (HANDOFF.md is its record):
  this file IS the replication prompt. The lessons are folded into the
  step blocks; the runtime facts behind them (the pkg native cache under
  HOME, the hooks bridge, the patch `insert` form) live in FIELD-NOTES.md's
  v2 section, which the prompt sends the builder to.
- memory/prompts/dream.md is derived from Anthropic's Claude Code
  auto-dream prompt; kit builders may substitute their own four-phase pass.

## Linux

```
You are the engineer replicating v2 of a personal agent system from this
repo, on Linux (Fedora or any systemd distro). The repo is the finished
kit: every layer below was built and flight-tested on the original host
(Fedora 44, 2026-09-14 to 09-16), so the work is to bring each layer up
on THIS host, run its flight test, and rebuild only what this host or a
newer SDK breaks. Read, in this order: SPEC.md (the design, canonical;
wins every conflict), CLAUDE.md (the session rules, already v2),
HANDOFF.md (the original build's record: what each step shipped and what
its flight test showed), FIELD-NOTES.md (ground truth: the DeepSeek/dsh
quirks still bind; its v2 section — the pkg native cache under HOME, the
hooks bridge, the patch `insert` form — is needed at steps 2, 6 and 8),
memory/prompts/dream.md (the nightly memory pass), then MIGRATION.md,
SPEC-v3.1.md and HANDOFF-v1.md (history only). If SPEC.md's Status
paragraph does not read CANONICAL, or memory/prompts/dream.md is
missing, STOP and say so — the checkout is stale; do not improvise
either file. Where CLAUDE.md disagrees with this prompt, this prompt
wins for the replication.

What I need to have before we start (ask me to confirm each):
- Claude Code CLI installed and logged in; `claude --version` recorded
  in configs/stable.md next to the original pin (2.1.272), with
  DISABLE_AUTOUPDATER=1 set so the pin holds. Say whether it is on a
  SUBSCRIPTION (flat rate — the design assumes this) or API billing
  (then the lead and the nightly dream bill per token; we set caps
  before step 6).
- git configured with user.name and user.email; python3 ≥ 3.10.
- A DeepSeek API key in .env as DEEPSEEK_API_KEY (my own — never an
  example value from the docs). The build adds AGENT_RUNTIME (step 1)
  and, for step 8, the search keys; WORKER_RUNTIME and SELF_REVIEW are
  optional flags. Nothing else goes in .env; .env.example lists it all.
- A private git remote of my own for the repo (any host). Called
  `backup` below.
- For step 8 only: the search backends the kit ships — Parallel
  (PARALLEL_API_KEY, primary) and Exa (EXA_API_KEY, fallback). A
  different backend means rewriting the search client in
  plumbing/swarm.py; we decide that at step 8, not before.
- python3 and pip on PATH; `loginctl enable-linger $USER` so the nightly
  timer runs while logged out (my step).

Two rules govern all code: (1) boring — simple, easily reproducible, the
way a senior writes it; one obvious way to do each thing; stdlib over
frameworks; files over services. (2) technology is budgeted — the only
unfamiliar pieces are those named in SPEC §14; another must be named
there with what protects us before it is used.

Work like this (the working agreements — they bind from step 1):
- ONE layer at a time, in the order below. After each layer, run its
  flight test and STOP for my confirmation before starting the next.
- ONE CHANGE PER PROMPT: a prompt carries one change; end it with the
  commit and ONE line, then wait for my "next". The status line (step 1)
  refreshes only per prompt, so a session that runs several changes
  under one prompt never sees its own context size.
- Context: rotate past 100k at the next boundary, between changes,
  never mid-change. Past 128k the ONLY allowed actions are rewriting
  state.md whole and /rotate.
- Every change that touches the runtime (plumbing/runtimes/, the
  composition patches, the supervisor's hooks) boots the real harness BY
  HAND before its commit — an offline start and close on both profiles,
  zero stderr — and does so EARLY in the session, at ~10k of context,
  not at ~35k after the code is written. One runtime-investigating
  change per session; the binary recipes are in FIELD-NOTES.
- Before promoting anything: python3 plumbing/tests/run_tests.py green.
  Tests are hermetic — no API calls; a new test goes in before
  `def main()` and is auto-collected.
- After each meaningful change: commit on your branch and push to
  `backup`. Never touch .git/config or the remote URL. Sandbox sessions
  may leave .git/*.lock: `rm -f .git/*.lock` before committing.
- Paste-safe commands only: no line-continuation backslashes; single
  quotes around anything containing "!"; placeholders clearly marked and
  only the marked part (prefixes are already in the value I paste).
- Nothing irreversible without asking: no deletes outside the repo, no
  pushes to main, no key changes, no service changes I did not request.
  Expect me to approve file writes and commands in this session unless I
  say otherwise.
- Secrets never in chat, briefs, reports or commits. .env is gitignored;
  keep it so. If a secret ever appears in chat, tell me to rotate it.
- When something fails, debug from evidence (logs, exit codes, the
  trajectory file) before changing anything. Every delegation failure in
  the original build was input-side — model string, default flag, wrong
  file — check that first (memory/procedures.md). The first diagnostic
  after ANY run is `head -1` of every worker log.
- Every session starts by reading the lineage state.md the SessionStart
  hook injects and checking its Provenance line against `git log -1`; a
  mismatch means a stale copy — read the live file and regenerate it
  whole at the next boundary. Every session ends through /rotate or a
  whole regeneration of state.md, never by just closing.
- Hooks and slash commands in .claude/ load on session START. After
  changing them, tell me to restart the session before their flight
  test.
- The lead never grinds: heavy work goes to workers once they exist.
  Reach workers only through plumbing/. Claude subagents are for short
  in-repo lookups, not for building.

Build order (SPEC §16). Flight test in brackets. Each step names what the
kit already holds; "rebuild" means only where this host differs.
1. Prerequisites + the session shell: clone `backup`, .env from my disk
   backup (gitignored — never in a clone), branch from main (the original
   build ran on exp/v2 and merged when done). Pin `deepseek-flash`
   (DeepSeek V4.1 Flash) as the worker model; `pip install --user
   deepseek-harness-sdk==<pin from configs/stable.md>`; record `claude
   --version`, the SDK and the model in configs/stable.md. Set
   AGENT_RUNTIME in .env to where runtime files live on this machine
   (~/Desktop/agent-system-runtime on the original host); the lineage is
   seeded there on first use (plumbing/lineage.py: lineages/index.json
   maps this directory to a lineage id with its state.md). Start memory/
   from the templates: keep the headers and formats, empty only the
   owner's PERSONAL entries (style, the adjudication log, personal facts
   and procedures); KEEP the system facts and procedures the gated dream
   added (the SDK surface, the sandbox, steer via stop-and-resume).
   Keep the original build's HANDOFF.md as HANDOFF-build.md (history) and
   start a fresh HANDOFF.md for this replication; CLAUDE.md is already v2
   (memory imports, state-file discipline) — read it, do not rewrite it.
   THE STATUS LINE COMES UP HERE, not at step 5: `plumbing/status.py
   --line` as the UserPromptSubmit hook in .claude/settings.json prints
   the context size (from the transcript's usage, never file bytes;
   ROTATE AT NEXT BOUNDARY past 100k, ROTATE NOW past 128k) and the
   state.md age (STALE after N=10 prompts without a change). The builder
   IS the lead and has no other gauge; the original build got it at step
   5 and ran the first five steps blind, to 649k. Step 5 keeps /rotate
   and the SessionStart / PreCompact hooks.
   [suite green; `claude -p ping` answers; after a session restart the
   status line shows a context size on the second prompt; a fresh
   session reads HANDOFF/state and reports the open items]
2. Workers: plumbing/runtimes/{engine,plain}.py, worker.py as the
   adapter, plumbing/compositions/ (minimal, standard patches: sandbox
   tightened, workspaceRoot from the brief, compaction off, the hooks
   bridge inserted in both and the bash-sandbox executor in minimal —
   FIELD-NOTES v2), presets, ask-back, /worker, /status. OPEN WITH THE
   SDK SURFACE CHECK: list what the installed deepseek-harness-sdk
   actually exposes (the server verbs, the event and usage fields, the
   profiles) against SPEC §4.2 and configs/stable.md, and correct the
   spec before touching code — the original's claims were checked
   against 0.1.5rc1 and corrected once; a newer pin needs the check
   again. Test the adapter against the SDK's REAL payload shape — a
   tool/call event captured from one live run and saved as a fixture —
   never a hand-built one: the original's tests fed the supervisor
   hand-written JSON strings and passed, while the live event carried
   `arguments` as a dict that the adapter handed on as its Python repr,
   not JSON, so the rules scanned a repr as content. The FALLBACK
   RUNTIME (engine cannot start → plain) is surfaced in /status, the
   report and the ledger's runtime column FROM THIS STEP — never only in
   a log: the original judged five sweep flight tests on the fallback
   without anyone noticing. Boot the real harness by hand (start + close,
   both profiles, zero stderr) at ~10k of context, before the first brief.
   [one real brief on EACH runtime returns a report with evidence and
   /status names the runtime each ran on; the V4.1 CoT flight test: same
   brief on minimal and standard, read the reasoning blocks, record in
   configs/stable.md whether the split still exists]
3. Supervision: supervisor.py trip rules, $AGENT_RUNTIME/events.jsonl,
   Monitor wake, steer/stop/resume, the UserPromptSubmit hook already up.
   The SDK server speaks only initialize / session/prompt / shutdown (no
   cancel, no steer target, no cross-process reopen) — the verbs are
   built on that; confirm it still holds. Confirm the Monitor tool exists
   in this Claude Code version; if it does not, the status hook is the
   wake and record the gap in HANDOFF.md. FLIGHT-TEST THE SUPERVISOR ON
   A RESEARCH BRIEF AS WELL AS A CODING ONE, before step 8 inherits it: a
   brief that searches, fetches pages, writes relative paths, and
   handles content carrying slashes and the word "error" — no lane rule
   (scope, error loop, repeat) may match INSIDE tool-result content; the
   rules read path-keyed arguments and a command's bare words, never
   content-like arguments. The original found this at step 8, one rule
   bug per run.
   [an ambiguous brief triggers ask-back; a looping brief trips `repeat`;
   I answer a waiting (ask-back) worker with /resume; a long brief gets
   the "wrap up, report now" steer at 26k on plain and stops with a
   report (on the engine the steer is an event only — a running turn
   never sees a spliced follow-up — and 32k is the rule); a brief that
   ignores the steer is force-stopped at 32k with a PARTIAL; the
   research brief above runs to a report with no false trip]
4. check.py checker ladder wired into definition-of-done (R1 proof, R2
   py_compile, R3 lint, R4 the named test command, R5 named files; "not
   available" is never a pass; the ladder runs after the worker's final
   report block, before filing). [a coding brief with tests; a planted
   failure is rejected by a rung via /check]
5. Rotation: `/rotate` rewrites state.md whole, writes the handoff
   ($AGENT_RUNTIME/handoffs/<ts>.md = state.md + the transcript's text
   tail) and ends the session; SessionStart injects state.md + the newest
   handoff; PreCompact is the backstop and logs an EVENT when it fires.
   The status line is up since step 1 — this step proves its STALE flag.
   [`/rotate` mid-task → the new session continues without re-asking;
   leave state.md alone for N prompts → STALE shows; force a compaction →
   handoff exists and the EVENT is logged]
6. The dream: memory/FORMAT.md and memory/INDEX.md ship; consolidate.py
   copies the durable memory files (never archives/ or library/; TEXT
   FILES ONLY — the copy skips anything that is not UTF-8, because a
   worker's native-module cache under memory/artifacts/ crashed the
   original's first unattended run with a UnicodeDecodeError) + 7 days of
   trajectories and handoffs to a dated dream dir under $AGENT_RUNTIME,
   runs `claude -p` there with memory/prompts/dream.md, writes DIFF.md;
   apply_dream.py applies hunk by hunk (removed lines → audit section;
   style/adjudication/audit hunks auto-rejected); the 19:45 systemd user timer (units ship in systemd/).
   The dream runs unattended: THE PROMPT GOES ON STDIN — `--allowedTools`
   is variadic and swallows a trailing positional prompt — with the
   tools covering Read, Grep, Glob, Write, Edit (no Bash) and its cwd set
   to the COPY, or it blocks on permission prompts / writes nothing.
   consolidate.py records `git status --porcelain` and `git diff HEAD`
   before the run and compares both after; any change outside the copy
   marks the night FAILED with no DIFF.md (nothing is reverted
   automatically); a non-zero exit or a refusal skips the night with a
   `dream_failed` / `dream_skipped` event. The timer runs as my user: `claude` on the unit's PATH and logged in.
   Expect the first unattended run to fail on something the by-hand run
   did not hit; read its event before the next session does anything
   else.
   [one run produces a diff I can apply hunk by hunk; live memory/ is
   unchanged until I apply; the timer's first unattended run logs a
   `dream` event]
7. Cost ledger: costs.py from usage fields → $AGENT_RUNTIME/costs.jsonl,
   the rate table in configs/prices.md (prices change; keep it editable;
   a row is priced at the worker's START-time tier, never repriced);
   /status cost line. [rows reconcile with the DeepSeek dashboard]
8. Swarm: web search and fetch (the backends in .env; GET-only, a page
   capped at 12k chars), swarm.py (launched detached, like workers; lane
   workspaces under memory/artifacts/<sweep>/<lane>/, gitignored),
   /swarm, the research-report contract, the synthesis, the scorecard.
   LANES NEED THE CONTEXT METER FROM THE FIRST RUN: past the meter
   threshold every tool result carries `context Nk of 32k; report by call
   M` — on the engine through the hooks bridge (a PostToolUse hook that
   cats the meter file; FIELD-NOTES v2), on plain as a trailer on the
   tool message — and the brief's REPORT line names the call to report
   by. Expect 3-7k of prompt growth per tool call on minimal: a lane that
   searches five times is at the 32k limit, so the meter and the "report
   by call M" line are what make a lane file at all; the original ran six
   sweeps before they existed. The lane fence and the pkg native cache
   are per worker (FIELD-NOTES v2). If lanes still do not file by the
   call the meter names, the next lever is the standard preset, not
   another rule.
   [a 4-lane question returns four sourced reports, one synthesis with a
   CONTRADICTIONS section, and a scorecard row; `head -1` of every lane
   log shows the engine, not the fallback; $DSH_HOME/cache/ is empty
   after the sweep]

After step 8 the system is live. The first post-build work on the
original host, on evidence, was the run-7 residuals (HANDOFF.md, step
8): the meter from 12k with M from the projected curve; the brief's
REPORT line stating the ≤500-token report contract with bulk to the
notebook by path; parse_sources on any line carrying a URL. Check
HANDOFF-build.md for which of them landed before you repeat them.

If I am the original owner on the original host: the repo is already at
~/Desktop/stuff/'Project 2'/agent-system with .env — do not clone; the
lineage, memory/ and the body exist — keep them; nothing above is a
build step here, this prompt is the record of how it was done.

Start with step 1. Tell me what you read, what you will do, and what you
need from me before touching anything.
```

## macOS

```
You are the engineer replicating v2 of a personal agent system from this
repo, on macOS. The repo is the finished
kit: every layer below was built and flight-tested on the original host
(Fedora 44, 2026-09-14 to 09-16), so the work is to bring each layer up
on THIS host, run its flight test, and rebuild only what this host or a
newer SDK breaks. Read, in this order: SPEC.md (the design, canonical;
wins every conflict), CLAUDE.md (the session rules, already v2),
HANDOFF.md (the original build's record: what each step shipped and what
its flight test showed), FIELD-NOTES.md (ground truth: the DeepSeek/dsh
quirks still bind; its v2 section — the pkg native cache under HOME, the
hooks bridge, the patch `insert` form — is needed at steps 2, 6 and 8),
memory/prompts/dream.md (the nightly memory pass), then MIGRATION.md,
SPEC-v3.1.md and HANDOFF-v1.md (history only). If SPEC.md's Status
paragraph does not read CANONICAL, or memory/prompts/dream.md is
missing, STOP and say so — the checkout is stale; do not improvise
either file. Where CLAUDE.md disagrees with this prompt, this prompt
wins for the replication.

What I need to have before we start (ask me to confirm each):
- Claude Code CLI installed and logged in; `claude --version` recorded
  in configs/stable.md next to the original pin (2.1.272), with
  DISABLE_AUTOUPDATER=1 set so the pin holds. Say whether it is on a
  SUBSCRIPTION (flat rate — the design assumes this) or API billing
  (then the lead and the nightly dream bill per token; we set caps
  before step 6).
- git configured with user.name and user.email; python3 ≥ 3.10.
- A DeepSeek API key in .env as DEEPSEEK_API_KEY (my own — never an
  example value from the docs). The build adds AGENT_RUNTIME (step 1)
  and, for step 8, the search keys; WORKER_RUNTIME and SELF_REVIEW are
  optional flags. Nothing else goes in .env; .env.example lists it all.
- A private git remote of my own for the repo (any host). Called
  `backup` below.
- For step 8 only: the search backends the kit ships — Parallel
  (PARALLEL_API_KEY, primary) and Exa (EXA_API_KEY, fallback). A
  different backend means rewriting the search client in
  plumbing/swarm.py; we decide that at step 8, not before.
- Homebrew python3; the SDK ships a macOS runtime wheel — confirm it
  resolves for this Mac's architecture before step 1.

Two rules govern all code: (1) boring — simple, easily reproducible, the
way a senior writes it; one obvious way to do each thing; stdlib over
frameworks; files over services. (2) technology is budgeted — the only
unfamiliar pieces are those named in SPEC §14; another must be named
there with what protects us before it is used.

Work like this (the working agreements — they bind from step 1):
- ONE layer at a time, in the order below. After each layer, run its
  flight test and STOP for my confirmation before starting the next.
- ONE CHANGE PER PROMPT: a prompt carries one change; end it with the
  commit and ONE line, then wait for my "next". The status line (step 1)
  refreshes only per prompt, so a session that runs several changes
  under one prompt never sees its own context size.
- Context: rotate past 100k at the next boundary, between changes,
  never mid-change. Past 128k the ONLY allowed actions are rewriting
  state.md whole and /rotate.
- Every change that touches the runtime (plumbing/runtimes/, the
  composition patches, the supervisor's hooks) boots the real harness BY
  HAND before its commit — an offline start and close on both profiles,
  zero stderr — and does so EARLY in the session, at ~10k of context,
  not at ~35k after the code is written. One runtime-investigating
  change per session; the binary recipes are in FIELD-NOTES.
- Before promoting anything: python3 plumbing/tests/run_tests.py green.
  Tests are hermetic — no API calls; a new test goes in before
  `def main()` and is auto-collected.
- After each meaningful change: commit on your branch and push to
  `backup`. Never touch .git/config or the remote URL. Sandbox sessions
  may leave .git/*.lock: `rm -f .git/*.lock` before committing.
- Paste-safe commands only: no line-continuation backslashes; single
  quotes around anything containing "!"; placeholders clearly marked and
  only the marked part (prefixes are already in the value I paste).
- Nothing irreversible without asking: no deletes outside the repo, no
  pushes to main, no key changes, no service changes I did not request.
  Expect me to approve file writes and commands in this session unless I
  say otherwise.
- Secrets never in chat, briefs, reports or commits. .env is gitignored;
  keep it so. If a secret ever appears in chat, tell me to rotate it.
- When something fails, debug from evidence (logs, exit codes, the
  trajectory file) before changing anything. Every delegation failure in
  the original build was input-side — model string, default flag, wrong
  file — check that first (memory/procedures.md). The first diagnostic
  after ANY run is `head -1` of every worker log.
- Every session starts by reading the lineage state.md the SessionStart
  hook injects and checking its Provenance line against `git log -1`; a
  mismatch means a stale copy — read the live file and regenerate it
  whole at the next boundary. Every session ends through /rotate or a
  whole regeneration of state.md, never by just closing.
- Hooks and slash commands in .claude/ load on session START. After
  changing them, tell me to restart the session before their flight
  test.
- The lead never grinds: heavy work goes to workers once they exist.
  Reach workers only through plumbing/. Claude subagents are for short
  in-repo lookups, not for building.

Build order (SPEC §16). Flight test in brackets. Each step names what the
kit already holds; "rebuild" means only where this host differs.
1. Prerequisites + the session shell: clone `backup`, .env from my disk
   backup (gitignored — never in a clone), branch from main (the original
   build ran on exp/v2 and merged when done). Pin `deepseek-flash`
   (DeepSeek V4.1 Flash) as the worker model; `pip install --user
   deepseek-harness-sdk==<pin from configs/stable.md>`; record `claude
   --version`, the SDK and the model in configs/stable.md. Set
   AGENT_RUNTIME in .env to where runtime files live on this machine
   (~/Desktop/agent-system-runtime on the original host); the lineage is
   seeded there on first use (plumbing/lineage.py: lineages/index.json
   maps this directory to a lineage id with its state.md). Start memory/
   from the templates: keep the headers and formats, empty only the
   owner's PERSONAL entries (style, the adjudication log, personal facts
   and procedures); KEEP the system facts and procedures the gated dream
   added (the SDK surface, the sandbox, steer via stop-and-resume).
   Keep the original build's HANDOFF.md as HANDOFF-build.md (history) and
   start a fresh HANDOFF.md for this replication; CLAUDE.md is already v2
   (memory imports, state-file discipline) — read it, do not rewrite it.
   THE STATUS LINE COMES UP HERE, not at step 5: `plumbing/status.py
   --line` as the UserPromptSubmit hook in .claude/settings.json prints
   the context size (from the transcript's usage, never file bytes;
   ROTATE AT NEXT BOUNDARY past 100k, ROTATE NOW past 128k) and the
   state.md age (STALE after N=10 prompts without a change). The builder
   IS the lead and has no other gauge; the original build got it at step
   5 and ran the first five steps blind, to 649k. Step 5 keeps /rotate
   and the SessionStart / PreCompact hooks.
   [suite green; `claude -p ping` answers; after a session restart the
   status line shows a context size on the second prompt; a fresh
   session reads HANDOFF/state and reports the open items]
2. Workers: plumbing/runtimes/{engine,plain}.py, worker.py as the
   adapter, plumbing/compositions/ (minimal, standard patches: sandbox
   tightened, workspaceRoot from the brief, compaction off, the hooks
   bridge inserted in both and the bash-sandbox executor in minimal —
   FIELD-NOTES v2), presets, ask-back, /worker, /status. OPEN WITH THE
   SDK SURFACE CHECK: list what the installed deepseek-harness-sdk
   actually exposes (the server verbs, the event and usage fields, the
   profiles) against SPEC §4.2 and configs/stable.md, and correct the
   spec before touching code — the original's claims were checked
   against 0.1.5rc1 and corrected once; a newer pin needs the check
   again. Test the adapter against the SDK's REAL payload shape — a
   tool/call event captured from one live run and saved as a fixture —
   never a hand-built one: the original's tests fed the supervisor
   hand-written JSON strings and passed, while the live event carried
   `arguments` as a dict that the adapter handed on as its Python repr,
   not JSON, so the rules scanned a repr as content. The FALLBACK
   RUNTIME (engine cannot start → plain) is surfaced in /status, the
   report and the ledger's runtime column FROM THIS STEP — never only in
   a log: the original judged five sweep flight tests on the fallback
   without anyone noticing. Boot the real harness by hand (start + close,
   both profiles, zero stderr) at ~10k of context, before the first brief.
   [one real brief on EACH runtime returns a report with evidence and
   /status names the runtime each ran on; the V4.1 CoT flight test: same
   brief on minimal and standard, read the reasoning blocks, record in
   configs/stable.md whether the split still exists]
3. Supervision: supervisor.py trip rules, $AGENT_RUNTIME/events.jsonl,
   Monitor wake, steer/stop/resume, the UserPromptSubmit hook already up.
   The SDK server speaks only initialize / session/prompt / shutdown (no
   cancel, no steer target, no cross-process reopen) — the verbs are
   built on that; confirm it still holds. Confirm the Monitor tool exists
   in this Claude Code version; if it does not, the status hook is the
   wake and record the gap in HANDOFF.md. FLIGHT-TEST THE SUPERVISOR ON
   A RESEARCH BRIEF AS WELL AS A CODING ONE, before step 8 inherits it: a
   brief that searches, fetches pages, writes relative paths, and
   handles content carrying slashes and the word "error" — no lane rule
   (scope, error loop, repeat) may match INSIDE tool-result content; the
   rules read path-keyed arguments and a command's bare words, never
   content-like arguments. The original found this at step 8, one rule
   bug per run.
   [an ambiguous brief triggers ask-back; a looping brief trips `repeat`;
   I answer a waiting (ask-back) worker with /resume; a long brief gets
   the "wrap up, report now" steer at 26k on plain and stops with a
   report (on the engine the steer is an event only — a running turn
   never sees a spliced follow-up — and 32k is the rule); a brief that
   ignores the steer is force-stopped at 32k with a PARTIAL; the
   research brief above runs to a report with no false trip]
4. check.py checker ladder wired into definition-of-done (R1 proof, R2
   py_compile, R3 lint, R4 the named test command, R5 named files; "not
   available" is never a pass; the ladder runs after the worker's final
   report block, before filing). [a coding brief with tests; a planted
   failure is rejected by a rung via /check]
5. Rotation: `/rotate` rewrites state.md whole, writes the handoff
   ($AGENT_RUNTIME/handoffs/<ts>.md = state.md + the transcript's text
   tail) and ends the session; SessionStart injects state.md + the newest
   handoff; PreCompact is the backstop and logs an EVENT when it fires.
   The status line is up since step 1 — this step proves its STALE flag.
   [`/rotate` mid-task → the new session continues without re-asking;
   leave state.md alone for N prompts → STALE shows; force a compaction →
   handoff exists and the EVENT is logged]
6. The dream: memory/FORMAT.md and memory/INDEX.md ship; consolidate.py
   copies the durable memory files (never archives/ or library/; TEXT
   FILES ONLY — the copy skips anything that is not UTF-8, because a
   worker's native-module cache under memory/artifacts/ crashed the
   original's first unattended run with a UnicodeDecodeError) + 7 days of
   trajectories and handoffs to a dated dream dir under $AGENT_RUNTIME,
   runs `claude -p` there with memory/prompts/dream.md, writes DIFF.md;
   apply_dream.py applies hunk by hunk (removed lines → audit section;
   style/adjudication/audit hunks auto-rejected); the 19:45 schedule as a launchd LaunchAgent (~/Library/LaunchAgents/, StartCalendarInterval); commit the plist to systemd/ beside the .timer so both hosts are in the repo.
   The dream runs unattended: THE PROMPT GOES ON STDIN — `--allowedTools`
   is variadic and swallows a trailing positional prompt — with the
   tools covering Read, Grep, Glob, Write, Edit (no Bash) and its cwd set
   to the COPY, or it blocks on permission prompts / writes nothing.
   consolidate.py records `git status --porcelain` and `git diff HEAD`
   before the run and compares both after; any change outside the copy
   marks the night FAILED with no DIFF.md (nothing is reverted
   automatically); a non-zero exit or a refusal skips the night with a
   `dream_failed` / `dream_skipped` event. The agent runs as my user: `claude` on the LaunchAgent's PATH and logged in. Paths, the dsh engine, Claude Code, Monitor and hooks are cross-platform; systemd → launchd is the only host substitution; bubblewrap does not exist on macOS, so the dormant data-tier jail (SPEC §9) would use sandbox-exec if ever enabled — not needed for the build.
   Expect the first unattended run to fail on something the by-hand run
   did not hit; read its event before the next session does anything
   else.
   [one run produces a diff I can apply hunk by hunk; live memory/ is
   unchanged until I apply; the timer's first unattended run logs a
   `dream` event]
7. Cost ledger: costs.py from usage fields → $AGENT_RUNTIME/costs.jsonl,
   the rate table in configs/prices.md (prices change; keep it editable;
   a row is priced at the worker's START-time tier, never repriced);
   /status cost line. [rows reconcile with the DeepSeek dashboard]
8. Swarm: web search and fetch (the backends in .env; GET-only, a page
   capped at 12k chars), swarm.py (launched detached, like workers; lane
   workspaces under memory/artifacts/<sweep>/<lane>/, gitignored),
   /swarm, the research-report contract, the synthesis, the scorecard.
   LANES NEED THE CONTEXT METER FROM THE FIRST RUN: past the meter
   threshold every tool result carries `context Nk of 32k; report by call
   M` — on the engine through the hooks bridge (a PostToolUse hook that
   cats the meter file; FIELD-NOTES v2), on plain as a trailer on the
   tool message — and the brief's REPORT line names the call to report
   by. Expect 3-7k of prompt growth per tool call on minimal: a lane that
   searches five times is at the 32k limit, so the meter and the "report
   by call M" line are what make a lane file at all; the original ran six
   sweeps before they existed. The lane fence and the pkg native cache
   are per worker (FIELD-NOTES v2). If lanes still do not file by the
   call the meter names, the next lever is the standard preset, not
   another rule.
   [a 4-lane question returns four sourced reports, one synthesis with a
   CONTRADICTIONS section, and a scorecard row; `head -1` of every lane
   log shows the engine, not the fallback; $DSH_HOME/cache/ is empty
   after the sweep]

After step 8 the system is live. The first post-build work on the
original host, on evidence, was the run-7 residuals (HANDOFF.md, step
8): the meter from 12k with M from the projected curve; the brief's
REPORT line stating the ≤500-token report contract with bulk to the
notebook by path; parse_sources on any line carrying a URL. Check
HANDOFF-build.md for which of them landed before you repeat them.

If I am the original owner on the original host: the repo is already at
~/Desktop/stuff/'Project 2'/agent-system with .env — do not clone; the
lineage, memory/ and the body exist — keep them; nothing above is a
build step here, this prompt is the record of how it was done.

Start with step 1. Tell me what you read, what you will do, and what you
need from me before touching anything.
```
