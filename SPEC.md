# SPEC v2 — Claude Code as the harness (canonical since 2026-09-16; drafted 2026-09-14)

Naming: the SYSTEM is v2 (second architecture); this file is its spec.
The v1 system's spec is `SPEC-v3.1.md` (its own internal version was 3.1).

READING THIS AS A KIT: lines marked "(Conrad, date)" are the original
owner's decisions and history, kept so the reasoning is traceable. They
are not instructions to a new builder. Owner-only material lives outside
this file (DOMAINS-owner.md, and the owner paragraph in KICKOFF.md).

Status: CANONICAL — promoted 2026-09-16 after step 8's flight test (run 7,
Conrad's ruling); this file was `SPEC-v2.md` until then. The v1 system's
record is `SPEC-v3.1.md`; this file is the design the rebuild targeted.
Where the two conflict, v2 describes the intent and v3.1 describes
what was built. Sections carried unchanged from v3.1 say so and point at it
rather than repeating it.

Two design rules for everything below (Conrad, 2026-09-14):
1. CODE IS BORING. Simple, easily reproducible, the way seniors write it:
   plain structure, one obvious way to do each thing, nothing clever,
   stdlib over frameworks, files over services. Applies to every line.
2. TECHNOLOGY IS BUDGETED. A separate, secondary rule for what the code
   sits on: an unfamiliar runtime, protocol or mechanism is named in §14
   with what pays for it — never forbidden, never accidental. Says
   nothing about how code is written; rule 1 does.

## 1. Identity

Personal agent system on one Fedora host. A frontier LEAD directs; cheap
WORKERS grind; a human GATE decides what becomes durable. The lead is a
Claude Code session (Fable 5.1, Max subscription); workers are DeepSeek
V4.1 Flash running inside DeepSeek's own engine; memory is a git
repo of files with provenance. Same shape as Cognition's Devin Fusion
(lead owns plan, ambiguity, review; sidekick explores, implements, tests,
reports; the two exchange only briefs, results and feedback) — measured
there at ~36–39% cheaper than the frontier model alone at equal quality.

AUTONOMY PRINCIPLE (carried from v3.1 §1, unchanged): 24/7 ACCESS, not
autonomy. Nothing executes without Conrad initiating it. ONE sanctioned
exception: the nightly consolidation pass, permitted because it only
proposes and cannot act.

What v2 removes from v3.1, in one line each (details in MIGRATION.md):
dsh as a chat surface · ZCode · the `!` plugin routers · the LLM-judge
verify layer, co-judge, Fable verify-arm and judge calibration ·
`!escalate` (the lead IS the escalation) · headscale, Caddy relay, certs,
Sunshine/Moonlight · the Signal watchdog · Langfuse as a required
component. The system that remains is smaller: ~1.5k lines of plumbing,
two host services (Claude desktop app + one timer).

## 2. Roles and models (exact)

| Role | Model | Transport | Status |
|---|---|---|---|
| LEAD (orchestrator, throne, gate operator, reviewer) | `claude-fable-5-1` (auto-fallback `claude-fable-5`) | Claude Code interactive session in this repo; `claude -p` only for the scheduled consolidation pass | Max subscription |
| WORKER (default, only) | `deepseek-flash` (= DeepSeek V4.1 Flash, released 2026-09-10) | DeepSeek API via the dsh engine (§4.2); plain-loop fallback | .env `DEEPSEEK_API_KEY` |
| Second worker model | KEPT AS IDEA (Conrad, 2026-09-14; not planned, not built): `glm-5.3-flash` (Z.ai; open weights) as ONE factual-check lane in a swarm — the one complementarity benchmarks support (fewer confident wrong answers). Revisit only if a swarm scorecard shows a sweep that needed it. | — | not configured |
| Training-tier model | NONE registered. Data-tier rule (§9) is written and dormant. Candidate if ever: Muse Spark 1.3 Contributor (Meta trains on traffic). | — | not configured |

Model-string discipline (learned the hard way, Sept 2026): pin the exact
string in `configs/stable.md` with the date; never pin an alias.
`deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` are temporary
aliases routing to V4.1 — do not use them. `deepseek-v4-pro` was retired
2026-09-14 (routes to Flash). There is no stronger DeepSeek tier.

DeepSeek quirks still binding (V4.1, confirmed 2026-09-14): thinking via
`reasoning_effort` low/high/max + `thinking: {type: enabled|disabled}`;
with `tools` present, `reasoning_content` must be replayed on EVERY later
request, even turns with no tool call; thinking mode ignores temperature
and floors `top_p` at 0.95; thinking tokens count against `max_tokens`
(use ≥16384). Billing windows, confirmed against the DeepSeek dashboard
2026-09-15: Mon–Fri 01:00–04:00 and 06:00–10:00 UTC (9pm–midnight and
2–6am Eastern) are PEAK and billed at FULL price; every other hour and the
whole weekend are off-peak at HALF price. Conrad's working day is
off-peak; late-evening Eastern runs are not. The rates are in
`configs/prices.md`. This only prices worker runs; no scheduled job runs
on DeepSeek (the dream runs on Claude).

OPEN (flight test, build step 2): the v3.1 preset-assignment matrix
(Minimal catalog → "We/Let's" CoT; wide catalog → "Let me") was measured on
V4. V4.1 is a new architecture. Run one Minimal and one Standard worker on
the same brief, read the reasoning blocks in the trajectories, and record
whether the split still exists. If it does, §4.4 stands; if not, presets
collapse to "tool scope is a capability knob," and §4.4 shrinks to one
preset.

## 3. The lead

- PATHS: `runtime/…` anywhere in this spec means `$AGENT_RUNTIME/…` (from
  `.env`, §10) — the body, outside the repo, never committed.
- A Claude Code session opened in this repo. `CLAUDE.md` carries: role,
  working agreements, the boring-by-default rule, `memory/style.md` and
  `memory/prompts/adaptivemem.md` (the memory-trap guard), and imports of the
  memory files the session needs.
- Owns: the plan, interpretation of ambiguity, review of every worker
  report, the curation gate, lineage state. Never grinds: no long tool
  chains, no reading worker transcripts into context, no verify-by-
  rereading — briefs and reports only. Two exceptions, both bounded: a
  take-over (§5.2) reads ONE worker's partial report and trajectory; the
  §2 CoT flight test reads two trajectories once, at build time.
- Talks to workers ONLY through `plumbing/` (do / status / steer / stop /
  resume). The lead is runtime-agnostic by construction; the engine (§4.2)
  is never a second surface.
- Phone access = the Claude app linked to the desktop (the desktop app
  holds a sleep inhibitor while linked — expected). No VPN in the core.
  Optional later: official Tailscale + SSH as a recovery lane (§11).
- STATE DISCIPLINE (carried from v3.1 §3b/§3c): the lead maintains
  `state.md` for its lineage as it goes — decisions, open threads, focus —
  regenerated holistically, decision-relevant compression, never
  append/patch. Durable facts go through the gate, never into handoffs.
- ROTATION (decision, Conrad, 2026-09-14): the lead's hard line is 128k
  of context; it rotates BEFORE that, by hand, at the next phase boundary
  — never at Claude Code's auto-compaction, which fires near the end of
  the window, long after quality has started to slide. v1's arm-then-fire
  rule, with the human pulling the trigger: ARM at ~100k, FIRE at the
  next quiet boundary. v1's finding stands: a fresh session seeded from a
  good state file beats a compacted one, and the handoff is the weak
  point. Mechanism, all in existing hooks:
  - The `UserPromptSubmit` status line carries two more fields (the hook
    itself is one line that calls `plumbing/status.py --line`; the
    arithmetic lives there, tested): the session's context size — read
    from the last assistant `usage` entry in the transcript JSONL Claude
    Code hands the hook (input + cache read + cache creation), never from
    file bytes, which never drop after a compaction — past 100k it says
    ROTATE AT NEXT BOUNDARY,
    past 128k ROTATE NOW — and the age of `state.md`: if the file has not
    changed in the last N prompts (N set at step 5; start at 10) the line
    says STATE.MD STALE. The second field is the warning light for the
    weak point: the hook cannot judge the state file's content, but it
    can see it quietly going stale.
  - `/rotate` = the lead rewrites `state.md` whole (this is the one
    moment it MUST), the handoff is written (state.md + raw transcript
    tail) to `runtime/handoffs/<timestamp>.md`, the session ends, a new
    one opens; the `SessionStart` hook injects `state.md` (at
    `runtime/lineages/<id>/state.md`) and the newest handoff. Boundaries
    are phase/task boundaries: the end of a build step, a sweep, a
    review.
  - `PreCompact` is the backstop only: if compaction arrives first, the
    hook copies state.md + raw tail to a handoff BEFORE it (a hook is a
    shell script; it copies, it does not think). A compaction that fired
    is logged as an EVENT — it means a rotation was missed.
  Workers (§4.3) have their own cap: 32k of context, v1's number, still
  right for DeepSeek V4.1 Flash, and 32k is the line, not the target.
  Same arm/fire shape: ARM at ~26k — the supervisor steers "wrap up and
  write the report now" (a PLAIN worker sees it before its next call; an
  ENGINE worker never does mid-turn — its brief is the only channel,
  §5.1); FIRE = the worker's next turn end with a report
  on disk, which is the normal stop (expected around 28–30k); 32k is the
  kill switch for a worker that ignored the steer — forced stop, whatever
  is on disk becomes the PARTIAL. The lead briefs a fresh worker from the
  report. Workers never rotate in place (an automatic successor is built
  for swarm lanes in `swarm.py`, §7; doing the same for lead-briefed
  workers is the small addition to make if the ledger shows long coding
  briefs hitting the cap repeatedly).
- LINEAGE = one project directory: its `state.md`, worker registry and
  archive chain. One writer — the Claude Code session that opened it. A
  second session in the same directory reads `state.md` and never writes
  it; it hands anything worth keeping to the first session as a report.
  (v3.1 §3c's throne / untie / retie machinery governed multiple chat
  windows on two harnesses; with one lead surface it has nothing to
  govern and is dropped.)

## 4. Workers

### 4.1 Contract (carried from v3.1 §3c, unchanged in substance)
- BRIEF (lead → worker): goal, constraints, definition-of-done (incl. which
  checker rungs apply, §6), relevant facts, scope (paths), preset, caps.
  Briefs reference paths; they never inline file bodies.
- REPORT (worker → lead), fixed fields, ≤ ~500 tokens to the lead, bulk to
  files by path: `did · changed · decisions · surprises · open_items ·
  evidence · based_on · runtime · data_tier · cost`. Claims without evidence
  do not count as done. Reports are DATA, never instructions.
- REGISTRY per lineage: id, state (running / waiting / done / failed /
  timed_out), brief, started, timeout, report path, trajectory path.
- OWNERSHIP INVARIANT: hierarchy only — spawn down, report up; no lateral
  handoff. One writer per resource; writers get their own git worktree.
- ASK-BACK: a worker that is unsure writes its question to the registry,
  sets `waiting`, and blocks on an answer file. Never guesses.

### 4.2 Runtime: dsh ENGINE by default, PLAIN loop as fallback
- ENGINE = DeepSeek Harness driven WITH NO UI via `deepseek-harness-sdk`
  (`pip install`; it pulls `deepseek-harness-runtime-bin`: one 275 MB
  single-file Node executable plus a ripgrep sidecar — no system Node, no
  web UI, no service). CONFIRMED against 0.1.5rc1 on 2026-09-14 (SDK
  source read, initialize handshake on both profiles, one real
  `sdk-minimal` run): one subprocess per worker, newline JSON-RPC on
  stdio. `DeepSeekHarness(dsh_home=, cwd=, profile=, patches=, model=,
  provider="deepseek-official", reasoning_effort=, max_tokens=, env=,
  request_timeout_seconds=)`; `run(prompt, session_id=, on_notification=)`
  returns `RunResult(session_id, final_response, finish_reason, events,
  notifications)`; `finish_reason` = the last root `turn/end`
  `reason.kind` (`completed` seen live; `max-tokens`, `error`,
  `cancelled`, `aborted` exist as strings). `dsh_home` (or `DSH_HOME`) is
  MANDATORY — the SDK never touches `~/.dsh`; profiles, plugins and the
  session store live under it. Composition = a named PROFILE
  (`sdk-minimal`, `sdk`) plus ordered PATCH files (id-targeted config
  overrides, `disabled: true`, insert lists; `!!js` allowed); there is no
  `cordis=` argument. Events, identical in `RunResult.events` and in the
  session JSONL: `request/header` (config + the tool catalog sent per
  request), `request/context`, `assistant/message` (content blocks incl.
  `reasoning` and `tool-call`, plus per-call `usage`: `inputTokens` = the
  cache-MISS part only, `cacheReadTokens`, `outputTokens`,
  `reasoningTokens`, `totalTokens`), `tool/call`, `tool/result`,
  `step/start|end`, `turn/start|end`, `agent/inbox/spliced`; subagent
  lifecycle = `subagent.started/finished` notifications. THE SDK SURFACE (read from the
  server's dispatch at step 3): the SDK runtime answers exactly three
  methods — `initialize`, `session/prompt`, `shutdown`. `session/prompt`
  on a live session queues a FOLLOW-UP (the agent's inbox); on an unknown
  id it CREATES the session, and a session id that already exists on disk
  is refused — so a durable session continues only inside the process
  that opened it; there is no cancel, no steer target and no cross-process
  resume on this surface (`session/cancel`, `session/resume` and the like
  belong to other dsh surfaces). Consequences, built at step 3: the worker
  PROCESS is the session's lifetime — an ask-back blocks the process on
  the answer file and the answer is the next prompt on the same session
  (§4.1 literally, both runtimes); STEER = a follow-up prompt queued by
  the adapter's watcher thread; STOP = the adapter closes the runtime
  (report PARTIAL) or SIGTERM; RESUME after a stop = a fresh worker
  briefed from the report.
- SHIPPED PROFILES (read from `dsh --dump-default-config`): `sdk-minimal`
  IS DeepSeek's Minimal composition — system prompt exactly `You are a
  helpful software engineer assistant.` (no harness identity, no runtime
  context), ONE tool: persistent `bash` with DeepSeek's description and a
  300 s timeout, JSONL sessions, no compaction — and NO
  `str_replace_editor` (the v3.1 note was wrong for this release); stock
  sandbox policy `danger-full-access` with `workspaceRoot = process.cwd()`.
  `sdk` is the wide catalog: one-shot `bash` (60 s stock, sandboxed), fs
  read / write / search, todo, goal, ralph (a self-looping executor, up to
  64 rounds), in-process subagents (spawn / fork), workflow, web search +
  fetch, plan mode, `compaction-basic` + a tool-result pruner, an approval
  plugin (policy `ask` unless the mode is `danger-full-access`), OTEL
  telemetry (`FEEDBACK_ONLY`); system prompt `You are a coding agent
  powered by the {{model}} model.` + `Your working directory is {{cwd}}.`.
- OUR COMPOSITIONS (`plumbing/compositions/{minimal,standard}.patch.yml`,
  applied over the shipped profiles; the runtime's cwd = the brief's
  scope, so `workspaceRoot` follows it): `minimal` = `sdk-minimal` +
  sandbox mode `workspace-write`. `standard` = `sdk` + the same sandbox,
  approval policy `never` (no UI: a blocked action fails instead of
  asking — nobody answers `session/request_permission`; ask-back is our
  own channel), compaction OFF (`compaction-basic`, `command-compact`
  disabled), web tools OFF (network is for swarm lanes only, §7), `ralph`
  and `workflow` OFF (self-loops outside our caps), telemetry OFF, bash
  timeout 300 s; subagents stay on — in-process descendants under the same
  `max_tokens`, and the supervisor's step count covers the whole session
  tree. The adapter sets `DSH_HOME=$AGENT_RUNTIME/dsh-home` (one shared
  home; sessions are keyed by worker id), `DSH_TELEMETRY_DISABLED=1`,
  `DSH_MAX_TOKENS_AS_SUCCESS=false`. The `sdk` profile persists sessions as
  `.jsonl.zstd` by default; the standard patch sets `compression: none` on
  the shared `sessions` root (a root cannot mix modes), so both presets
  leave plain JSONL. `workspace-write` IS ENFORCED inside
  `sdk-minimal` (probed 2026-09-14 through an answered ask-back): a mount
  namespace with the scope writable, a PRIVATE tmpfs on `/tmp` (a write
  there returns exit 0 and never reaches the host), and everything else
  read-only (`touch ~/x` fails with "Read-only file system"). It confines
  WRITES, not reads — the home directory is visible read-only — so the
  §5.1 `scope` trip (any path outside the scope) is the read fence, and
  §7's lane confinement (`env -i`, no repo, no `.env`) stays necessary for
  workers that see untrusted content.
- PLAIN = the v1 `worker.py` loop moved to `plumbing/runtimes/plain.py`:
  direct API, the same 16-tool catalog, one-shot bash, text step log. Two
  forced changes: this host has no `openai` package (the v1 loop, verify
  and think never ran here), so the loop calls the API through
  `plumbing/clients.py` (stdlib `urllib`, thinking + `reasoning_content`
  replay); and the jail is the brief's scope, never `~/Desktop`. Same
  brief in, same report out, fewer features: steer is an inbox file read
  before each model call; no resume; terse log.
- SELECTION: `--runtime engine|plain` > `WORKER_RUNTIME` in .env > default
  `engine`. AUTO-FALLBACK is narrow and loud: engine → plain only when the
  engine CANNOT START (import, missing binary, handshake); never mid-task,
  never on task failure; stamped in the report, `/status`, and the cost
  ledger as `runtime: plain (fallback — <reason>)`.
- PIN the SDK version exactly in `configs/stable.md`. Bump procedure: on
  `exp/`, run the suite, one live worker on EACH runtime, then commit. One
  shared contract test runs the same fake brief through both runtimes and
  asserts identical report shape.
- Trajectory: the engine's session JSONL stays where the runtime writes
  it — `$DSH_HOME/sessions/<cwd-mangled>/<worker-id>/session.v3.jsonl`
  (`DSH_SESSION_DIR` no longer exists; the adapter records the resolved
  path in the registry); plain writes `lineages/<id>/worker-<wid>.log`. It
  is the supervisor's feed, the archive consolidation mines, and the
  evidence for the §2 CoT flight test.

### 4.3 Caps (carried from v3.1 §3e2; provenance unchanged — tripwires,
tuned from this system's own logs at ~2× p95 after two weeks)
- Steps: 25 default, 64 for coding goals. Hitting a cap = stop + report.
- Context: 32k per worker — prompt tokens per call (plain:
  `usage.prompt_tokens` of each response, written to the step log;
  engine: `usage.inputTokens + usage.cacheReadTokens` of each
  `assistant/message` event, `inputTokens` being the cache-miss part only —
  confirmed at step 2). The
  supervisor sees the count after the call that crossed it, so
  "never-cross" means no further call past it. At ~26k — on PROJECTION, this
  prompt plus its growth over the previous call, so one call earlier than the
  line (ruling on run 5, 2026-09-15) — the supervisor steers "wrap up:
  write the report now"; the worker's next turn end with a report is the
  normal stop; at 32k it is stopped by force with a PARTIAL (§5.1
  `context` rule). The lead briefs a fresh worker from that report —
  v1's worker rule, now a steer plus a trip instead of a rotation.
  The 32k check runs AFTER the call's tool calls (ruling on run 5,
  2026-09-15: run 5 lost three notebook writes and filed three answers
  as PARTIAL): a write on the tripping call persists, a call with tool
  calls trips once they ran (no further model call), and a final
  message over the line is KEPT — filed done with finish_reason
  `done-at-cap`, the overage first in its open_items and in `at_cap` on
  the report; a worker at the line takes no ask-back.
- Context arithmetic learned at step 3: with tools present the model's
  `reasoning_content` is replayed into every later request, so a
  deliberating minimal worker adds ~3k tokens per step on top of tool
  output; the 26k→32k window is one big step wide. The engine's window
  budget is therefore effectively the 32k stop plus the brief's own
  "wrap up before the cap" line.
- Learned at the step-8 flight test (runs 3-4, 2026-09-15): a research
  lane that reads fetched pages whole spends 32k in ~10 calls and one
  successor does not recover it; the fetch tool now returns a 6k-char
  excerpt and saves the page to a file (§7). The caps stay 32k / 12
  calls / $1 per sweep until the ledger says otherwise (Conrad's ruling).
- Timeout per worker (default 2h) and per shell command (300 s).
- Spend per task: alert ~$1, hard stop ~$5 (from usage fields, §10).
- Workspace = the project directory named in the brief. NEVER `~/Desktop`
  as a whole (v1's jail was the entire Desktop — resume, job files, keys).
- Permissions (v3.1 §3f, restated for v2): the lead runs under Claude
  Code's own permission modes; a worker's mode is its composition's
  sandbox policy plus `workspaceRoot`, and a brief may narrow it, never
  widen it. Destructive or irreversible actions — deletes outside the
  workspace, pushes, sends, key or service changes — require the human in
  every mode. The active mode shows in `/status`.

### 4.4 Presets (one-knob principle, pending the §2 flight test)
| Preset | Catalog | Use | Cap |
|---|---|---|---|
| `think` | none (tool-free call) | one hard question, distilled answer | 1 call |
| `minimal` | persistent bash + str_replace_editor (DeepSeek's RL composition) | planning, research, analysis, plan-then-execute | 25 |
| `standard` | wide catalog | mechanical execution with a tight brief | 25 / 64 |
Domain roles (v3.1 §2c) arrive later as on-disk agent definitions over the
same three shapes.

## 5. Supervision — two layers

The lead cannot be interrupted mid-thought (turn-based), so continuous
supervision is split: detection is mechanical and always on; judgment is
the lead's and event-driven.

### 5.1 Layer 1 — mechanical supervisor (plumbing, no model, every step)
Subscribes to each worker's notification stream / trajectory. Trip rules
(initial values; tune from logs):
| Rule | Trip |
|---|---|
| repeat | same tool call (name+args) ≥ 3 times |
| error loop | same error substring ≥ 3 consecutive tool results — for any worker but a LANE. For a LANE (ruling on run 6, 2026-09-15; change 10) never a word in the text: the same non-zero exit AND error line on 3 consecutive results, the line being the last line of plain's stderr, or on the ENGINE the last output line before the harness's trailing exit marker. The SDK's `tool/result` is text only — no exit or stderr field, `isError` false on every run-6 result (it counts as exit 1 if it ever comes), stderr merged into the text — so the marker is the engine's only exit channel: `[Command finished with exit code N]` ends every result of sdk-minimal's persistent bash; sdk's one-shot bash appends `[exit code: N]` on a non-zero exit only, or `[killed by signal: X]` / `[timed out after Nms]` (read from run 6's trajectories and the runtime binary). A non-zero exit that printed nothing has no signature: grep, diff and test say "no match" that way (run 6's sbir-sttr result 5 was one) and that is not an error. Known residual, not seen: on the engine a banner echoed before three no-match greps would be the same line thrice. Run 6's gsa successor was killed on the word "exception" in three page slices, exit 0 each |
| stall | no file change and no new path read in the last 8 steps; for a LANE a new search query or fetched url is new ground too (a research lane touches no paths — found at the step-8 flight test 2026-09-15, when all four lanes tripped stall inside a minute), and so is a relative OR absolute file word new to the lane (ruling on run 6, 2026-09-15; change 10): relative path-keyed values and a command's file-shaped words are resolved against the lane dir and count when they name a file there — a file the call itself creates counts at its result, `t.split` in a python heredoc names none — so the same page read by relative name and then by absolute path is one ground. Run 6's sbir-sttr successor cd'd to its lane once and read page-01..09.md by relative name into a stall at step 9 while the scan saw absolute paths only |
| context | the PROJECTION for the next call — prompt tokens on the last call plus their growth over the call before (0 on the first call), so the direct rule prompt > 26k is the floor — > ~26k (ruling on run 5, 2026-09-15: the steer at 26k landed, but the answer call replayed 5-9k of reasoning and tripped 32k in 5 of 8 workers; the steer now fires one call earlier) — steer "wrap up, report now" — PLAIN-ONLY (ruling on run 6, 2026-09-15): on plain it lands before the next call; on the ENGINE the follow-up is queued `next-turn` and never reaches the running turn (flight-tested 2026-09-14; run 6: the projection steer fired one call earlier on every lane, was queued, and the lanes kept exploring to 35-39k), so there it is an event for the lead only — on the engine the BRIEF is the only channel that reaches a running lane; > 32k — checked AFTER the call's tool calls ran, so a write persists: tool calls → stop, PARTIAL, no further call; a final message → kept, `done-at-cap` (§4.3; ruling on run 5, 2026-09-15), on both |
| meter | not a trip — the CONTEXT METER (ruling on run 6, 2026-09-15; change 12): once the prompt passes 20k every tool result carries one line, `context Nk of 32k; report by call M`. M is the number of the LAST tool call — the brief's unit: the message after it is the report, as the brief's REPORT CALL says of a lane's 5th and a successor's 3rd — the smaller of the brief's `report_call` and the projection: this call's tool call plus one per further call while the prompt, growing by the last call's growth, stays under 32k (the last call that fits is the report, so the call before it makes the last tool call — diag_run6's STOP CALL, the call the answer had to follow; every run-6 lane spent exactly one call past it); never before this call's own tool call, already made. On PLAIN the runtime appends the line to the tool message (the supervisor sees the raw text). On the ENGINE the harness's Claude Code hooks bridge delivers it (§7, §14 item 1a): a PostToolUse command hook cats the supervisor's meter file (`meter-<id>.txt` beside the steer file, rewritten atomically at every model call — the bridge's additionalContext JSON past 20k, `{}` under it, written at supervisor init so the cat always succeeds) and the bridge adds the line as a context message after the tool result — the only channel that reaches a running engine turn. Fail-open: no config or a failing hook and the worker runs unmetered; the trajectory's hook records are the evidence either way |
| budget | steps > brief allotment, elapsed > timeout, spend > alert |
| scope | any path outside the brief's scope (also enforced by the sandbox); a path-valued tool argument (`path`, `file_path`, `cwd`, `dir`) is judged whole, spaces and all (step-8 flight test 2026-09-15: a successor lane's `read_file` under `Project 2/` was cut at the space and read as outside); a path's first segment starts with a name character, so a `/regex/` literal in an awk, sed or grep program is not a path (run 2, 2026-09-15). PROBATION OUTCOME (Conrad 2026-09-15, after run 3): seven false trips, zero true — DEMOTED. For a lane an outside path is a `scope` EVENT the lead reads, never a stop (the sandbox is the write fence, §4.2); on every worker only path-keyed arguments and a command's bare words are scanned — file contents, search queries and notebook text never (run 3 read a notebook's `8(a)/HUBZone/SDVOSB/WOSB` as paths; the engine hands the supervisor a dict, which reached the scan as a Python repr and is now passed as JSON). The lane fence (`..`, `$DSH_HOME`, `$AGENT_RUNTIME`, SEARCH_AUTH_FILE, the repo's `.env`) stays a trip, and since change 10 reads relative path-keyed values too (`read_file ../notes.md` was invisible to it before) |
| finish | `turn/end` reason `max-tokens` or `error` |
| reasoning heuristics | regex on `reasoning_content`: "try again", the same plan restated, "not sure what the user wants" |
| swarm: serial collapse | one lane > ~60% of a sweep's tool calls, checked only once every running lane has ≥ 3 calls AND some lane has reached the first checkpoint (10 calls) — run 3, 2026-09-15: the fastest starter tripped at 18 s with 7 of 11 calls while the others were on their first call |
| swarm: fake parallelism | lanes > distinct sub-questions, or overlapping lane briefs |
| swarm: dead lane | neither a notebook write nor a search in the last 10 steps; a successor's window starts at its own first step (run 4, 2026-09-15) |
GENERAL RULE for a LANE (ruling on run 6, 2026-09-15): no lane trip ever
matches inside a tool result's content — a lane's results are untrusted web
text, so the rules read exits, paths, calls and counts, never words.
On trip: STOP the worker on BOTH runtimes (the SDK surface has no cancel
and no pause, §4.2): the runtime sees the stop, the report is filed
PARTIAL with the trip evidence, registry state `failed`; the lead reads
the report and resumes with a fresh worker or takes over. `context` at
26k is the exception: it STEERS (the same `steer` verb the lead uses,
§5.2) and writes the event, nothing stops; at 32k it stops like any trip
— after the call's tool calls ran, and a final message over the line is
kept as done-at-cap (§4.3).
An ask-back is not a trip: the worker asked, so its process WAITS on the
answer file (state `waiting`) and continues its own session with it.
Then write an EVENT with the evidence to `runtime/events.jsonl` — one
JSON object per line: `ts, lineage, worker, event, detail`, where `event`
is `trip:<rule>`, `ask`, `checkpoint`, `done`, `failed`, `resumed`, `scope` (a lane's outside
path: an event, no stop — 2026-09-15), `compaction` (worker `lead`;
written by the PreCompact hook). Also emits: ask-back, checkpoint
(every 10 steps on long tasks, and before any op the brief marked
destructive), done.

### 5.2 Layer 2 — the lead, woken on events
When the lead spawns a worker it starts a `Monitor` on `runtime/events.jsonl`;
Claude Code re-invokes the session when a line arrives. The lead reads the
evidence and picks one verb:
- `steer <msg>` — message the worker sees before its next model call (engine: a follow-up prompt queued on its session by the adapter's watcher thread; plain: the steer file read before the call).
- `stop` — the stop file (the runtime sees it within a second) and, with `--kill`, SIGTERM; either way the worker files a PARTIAL report with the evidence so far.
- `resume <id> <note>` — a WAITING worker (ask-back) gets the note as its answer and continues its own session, nothing learned is lost (both runtimes, in-process); a FINISHED worker (failed / timed_out / done) gets a FRESH worker briefed from its report plus the note — the SDK surface cannot reopen a session from a new process (§4.2).
- take over — read the partial report / trajectory and finish the task in the lead.
COST DISCIPLINE (load-bearing): the supervisor sees every step; the lead
sees only events. Polling every step would put worker transcripts back into
the lead's context — the thing the architecture exists to avoid.
`Monitor` is the primary wake. The safety net, not a second path: a
`UserPromptSubmit` hook appends a status line to every message Conrad
sends — always one lead line (context size, state.md age; §3) plus one
per running worker — so a `waiting` worker cannot be missed if the
Monitor is absent or was not started.

## 6. Verification — mechanical first, no LLM judge in the core

- CHECKER LADDER (`plumbing/check.py`), reject-authorized, strongest rung
  first: R1 proof (Lean/SMT where a formal spec exists — the only rung whose
  pass can ship alone) · R2 compile/types · R3 lint/static · R4 tests ·
  R5 diffs/exit codes/expected files. A failure is a fact no model opinion
  overturns; a pass proves only what that rung states. The brief's
  definition-of-done names the rungs; results are stamped into the report.
- The LLM-judge verify layer of v3.1 §3 (N candidates → GLM scoring, co-
  judge, Fable arm, calibration) is REMOVED from the core. Rationale on
  record: it existed to replace a frontier tier under the no-Claude rule;
  with a frontier lead reviewing every report it solves a problem the
  system no longer has, at O(N·K·C) judge calls. Code stays in git history.
- OPTIONAL SELF-REVIEW PASS (evaluator-optimizer, Anthropic's pattern;
  flag `SELF_REVIEW=on|off`, default OFF; ~$0.002 per pass at V4.1 rates):
  runs ONLY when the brief's definition-of-done has NO mechanical rung —
  written analysis, research summaries, plans. One DeepSeek critique call
  against the definition-of-done, at most ONE revision by the worker, then
  the critique is appended to the report as `self_review`. Three conditions
  make it safe, all mandatory: (1) ORDER — `self_review` is the LAST field
  (or a file the report points to); the lead reads evidence and rung
  results and forms its verdict BEFORE reading it. (2) LABEL — the field
  header says "worker's own critique, same model family — a hint, not
  evidence"; nothing in it counts toward done. (3) SANITIZER — the report
  sanitizer (§7) runs over it like any other field. Never a replacement
  for a ladder rung; never unbounded; the lead's review stays the gate.
  REMOVAL: it is ~30 lines in the adapter behind one flag plus one test
  and one report field; nothing else reads `self_review`. Deleting it is
  a flag flip first, a small diff second — designed to be add-only.
- OPTIONAL CHECK MODE (later, `do.py --n N`): N workers in separate
  worktrees → ladder → dedupe identical outcomes → survivors' SHORT reports
  to the lead, who picks. No rubric, no logprobs. Guardrails carried from
  the literature: never prune mid-trajectory; N ≤ ~8 for a homogeneous
  pool; the picker (the lead) is outside the generator's family.

## 7. Swarm mode — research fan-out (opt-in; the expensive bet)

Sources for the rules below: Anthropic's Agent SDK subagent design and
multi-agent research write-up; Moonshot's Kimi K3 Agent Swarm docs (the
swarm coach is trained, PARL — its documented behavior is what transfers,
not code). Everything here is rules on plumbing; no new model, no token
against the §14 budget.

- SHAPE (MinionS): the lead decomposes a research question into
  INDEPENDENT sub-questions → ≤5 `minimal` workers in parallel, one each →
  each returns a distilled report with SOURCES → the lead synthesizes.
- DECOMPOSABILITY GATE — the first step of `/swarm`, before anything is
  spawned. Three yes/no questions: independent subtasks? low merge cost?
  divergence acceptable? 3/3 → fan out. 2/3 → fan out with the lead as the
  named merge owner. ≤1/3 → no swarm: one worker, or the lead answers.
  (Payoff is on hard, broad browse/gather tasks; on simple questions a
  sweep costs several times a single run for nothing.)
- LEAD BUDGET PER SWEEP: ~15 lead steps — decompose, write the plan,
  spawn, synthesize. The plan (sub-questions, lane assignments, what each
  lane must NOT cover) is written to `state.md` BEFORE spawning so it
  survives a compaction mid-sweep.
- LANE BRIEF (self-contained — a lane's context starts EMPTY; nothing is
  inherited from the lead): sub-question · what the other lanes cover (so
  no duplication, no gaps) · allowed sources / tools · TOOL-CALL BUDGET
  (default 10–15; simple fact-finding ≤10) · "start wide, then narrow"
  (short broad queries first, evaluate, then drill) · output = research
  report + sources · path of the lane's notebook · REPORT CALL: the message
  after the 5th tool call IS the REPORT block, no exceptions, a successor's
  after the 3rd (the brief carries `report_call`) · never cat, sed or
  python-print a saved page whole — grep or head it · notes.md after EVERY
  fetch, in the very next tool call (Conrad's ruling on run 6, 2026-09-15:
  no lane wrote a notebook, every lane cat whole 44k-char pages and tripped
  32k at calls 6-8; built as change 11).
- NOTEBOOKS (context sharding): each lane keeps a running
  `memory/artifacts/swarm-<id>/<lane>/notes.md` as it works (each lane's own
  directory, which is also its workspaceRoot — built 2026-09-15); the report
  to the lead is CONCLUSIONS ONLY (≤500 tokens). Notes survive a lane dying
  mid-run and are what consolidation mines later.
- RESEARCH REPORT contract = worker report + mandatory `sources`
  (url · title · the claim it supports). An unsourced claim does not count.
- CAPS (all three, always): DEPTH 1 (lanes may not spawn sub-workers) ·
  CONCURRENCY ≤5 · SPEND cap per sweep (from usage fields) — at the cap,
  `swarm.py` stops spawning, stops running lanes, and returns what it has,
  marked partial. A lane that hits its step/tool budget returns PARTIAL
  and is resumable; the lead decides whether to resume it.
- ROTATION IN A SWEEP (§3 applied): lanes are workers — the 26k steer /
  32k stop apply, and a lane's NOTEBOOK is its state file: the wrap-up
  steer means "write conclusions to the notebook, then report". If a
  lane is force-stopped at 32k, `swarm.py` — not the lane, not the lead —
  spawns ONE successor briefed from the notebook plus the partial report,
  counted as the same lane (concurrency unchanged); a second force-stop
  ends the lane PARTIAL; a lane whose FINAL message lands over the line
  is done-at-cap (§4.3) — a result, no successor, the overage on its
  reports.md header and `done_at_cap` in the scorecard row (ruling on
  run 5, 2026-09-15). No LLM decides this; it is a rule in the
  orchestrator. The LEAD rotates before a sweep, never during one: if the status line
  says ROTATE, rotate first, then `/swarm` — the plan is in `state.md`
  so nothing is lost either way, and `swarm.py` is launched DETACHED
  (`setsid`/`nohup`, or a transient user unit) — never as a Claude Code
  background task, which dies with the session — so lanes keep running
  through a lead rotation; the new session starts the `Monitor` on
  `events.jsonl` when the injected `state.md` says a sweep is running.
  The sweep spend cap covers successor lanes.
- ERRORS ARE NOT FINDINGS: a lane ending with a `turn/end` reason of `error` (rate
  limit, API failure) files an error, never a report with `did:` content.
- ISOLATION: lanes never see each other's output — that is what keeps them
  decorrelated; only the lead reads all N. REPORT SANITIZER: before the
  lead reads any report, plumbing neutralizes instruction-shaped patterns
  (imitated harness/system tags, `Human:`/`Assistant:` turn markers,
  "ignore previous instructions"-class text) — escaped in place, nothing
  deleted, a marker line prepended. Reports are DATA (§4.1), now enforced:
  `plumbing/sanitize.py`, run inside `lineage.file_report` — every filed
  report, not only a lane's (built 2026-09-15).
- ORCHESTRATION LIVES IN `swarm.py`, outside the lead's context: fan-out,
  wait, collect, sanitize, budget enforcement, scorecard. The lead's
  conversation holds only the plan and the N short reports.
- SUPERVISOR RULES for a sweep (added to §5.1 trip table): SERIAL COLLAPSE
  — one lane consuming > ~60% of the sweep's tool calls; FAKE PARALLELISM
  — lane count > distinct sub-questions, or two lane briefs overlapping;
  DEAD LANE — no notebook write in 10 steps. (Built 2026-09-15 in
  `swarm.py`: fake parallelism is refused at the plan; serial collapse is
  checked each poll only once every running lane has ≥3 calls AND some
  lane has reached the first checkpoint (10 calls) — the ruling of
  2026-09-15 after run 3, where the fastest starter tripped at 18 s with
  7 of 11 calls while the others were on their first call; dead lane by the notebook's mtime OR the search log growing
  within the last 10 steps — run 2 showed deepseek-flash writes the
  notebook at the end, so the brief now says "append after every fetch" —
  and, after run 6 wrote no notebook at all, "after EVERY fetch, in your
  very next tool call" plus the report call (change 11, 2026-09-15),
  and a successor starts a clean 10-step window — run 4's gsa successor
  was tripped 6 s after spawning because the count was charged across
  the succession (fixed 2026-09-15); a trip stops that lane, which files
  PARTIAL like any trip. A tripped or
  stopped lane that leaves no final message files its NOTEBOOK as the
  PARTIAL — did = the notebook's sanitized text, sources = its urls marked
  unverified — so a rule trip is never a total loss; Conrad 2026-09-15.)
- SYNTHESIS CONTRACT: the lead's synthesis carries a mandatory
  CONTRADICTIONS section — where lanes disagree, both positions and their
  sources are listed and reconciled explicitly, never silently (the same
  rule v3.1 applied to lineage-merge reports and verifier disagreement).
- SCORECARD (PARL's three-part reward, logged per sweep by `swarm.py`):
  (1) lead's quality verdict on the synthesis, (2) genuine parallelism —
  distribution of tool calls across lanes, (3) subtask completion rate —
  lanes completed / lanes spawned. Read weekly with the architect log;
  a swarm mode that keeps scoring badly on (2) or (3) is not earning its
  cost. Rows: `runtime/scorecard.jsonl`, one per sweep (tool calls per
  lane, max share, completion, sourced lanes, search requests, usd,
  partial, stopped_by, `fallback_lanes` + the runtime per lane — a lane
  that fell back to plain is named in the row, the sweep status line, the
  swarm_done/partial event, reports.md's lane header and /status, never
  only in a log; ruling on run 5, 2026-09-15; that start-time stamp is a
  registry write landing in the same second as the sweep's later spawns —
  atomic and locked since change 9, §8, after run 6's cmmc lane died at
  launch on a torn read), a copy in the sweep's
  `scorecard.json`; the lead's
  verdict lands by `swarm.py --verdict <sweep> <1-5>`, which refuses until
  `synthesis.md` exists with a CONTRADICTIONS heading (built 2026-09-15).
- OUTPUTS: full findings + notebooks → `memory/artifacts/swarm-<id>/`
  (`plan.json`, `<lane>/`, `reports.md` = the N sanitized short reports,
  `scorecard.json`, the lead's `synthesis.md`). Sweep directories are
  gitignored (`memory/artifacts/*/`, Conrad 2026-09-15) so sweep output is
  never committed by accident: promotion of ANY sweep artifact into the
  genome is a gate decision, made per artifact, never by `git add`;
  reports → lead; fact-worthy items → gate → `facts.md` with `web-claimed`
  provenance and the source cited. Library ingestion (`/ingest`) unchanged.
- PREREQUISITES: (a) web tools for workers, CLI-first per the tool-surface
  policy — `web_fetch` and `web_search` scripts reachable through bash;
  network allowed for swarm lanes only. (b) the research-report contract.
  BUILT 2026-09-15 (Conrad's backend decision after the survey):
  `tools/web_search.py` — one function per backend, Parallel Search API in
  `basic` mode PRIMARY, Exa FALLBACK, one retry on the fallback on an error
  OR an empty result, the answering backend stamped, selection by which
  keys are present (one key still works), `--mode lookup|research`
  RESERVED — logged, never routed on until scorecard evidence (§15), one
  JSON line per call to `SEARCH_LOG`; `tools/web_fetch.py` — stdlib GET +
  html2text, GET-only, no bodies, http(s) only, loopback and private hosts
  refused, 2 MB cap; since run 4 (ruling 2026-09-15) it writes the
  page text to `page-NN.md` in the lane's directory and prints only that
  path plus an excerpt bounded at 6000 chars (`--max-chars`) — and since
  run 6 (ruling 2026-09-15, change 13) the SAVED page is capped at 12,000
  chars, a marker line at its end and `capped` on the `saved:` line, so a
  lane that ignores the brief and cats the file whole cannot pull 44k
  chars into context — and the
  lane brief says search first, fetch only when the search excerpts are
  not enough, grep the saved page instead of re-fetching — deepseek-flash
  lanes were passing whole pages through context and every
  first-generation lane tripped 32k within three minutes. Both stdlib,
  hermetically tested, first on a lane's PATH. Search prices live in `configs/prices.md`; lanes cite the `url`
  field, never excerpt text.
- LANE CONFINEMENT (blueprint Layer 4 — break the lethal trifecta: an
  agent reading untrusted web content must not also hold private data and
  an exfiltration channel): a lane's `workspaceRoot` is its own
  `memory/artifacts/swarm-<id>/` directory and nothing else — no repo, no
  `memory/` beyond it, no `.env`: the lane's shell gets `env -i` plus
  `PATH`, `HOME` and — only if the search backend needs one — the search
  key (the DeepSeek key is held by the runtime process, not the shell).
  BUILT 2026-09-15 as: PATH (tools/ first), HOME = the lane's own
  directory for the lane's SHELL only (so `~` and `$HOME` stay inside the
  scope; the worker PROCESS keeps the real HOME — the SDK lives in the user
  site under it, and runs 1-5, which set the process HOME to the lane dir,
  made every lane fall back to plain; ruling on run 5, 2026-09-15), locale, and two
  handles — `SEARCH_AUTH_FILE` (a mode-600 file in `runtime/swarms/<id>/`
  holding the search keys, deleted when the sweep ends) and `SEARCH_LOG`.
  The keys travel as a file because the harness's subprocess layer
  (`dsh-subprocess`, read 2026-09-15) drops every credential-shaped name
  (`KEY|PASSWORD|SECRET|TOKEN`) and every `DSH_*` name from any shell it
  spawns — which is also why the DeepSeek key never reaches ANY worker's
  shell on the engine. The engine adapter prunes the rest of the lane
  process's env; the plain runtime hands bash exactly that env. The
  harness runtime is a `pkg`-packaged executable whose dlopen hook copies
  each native module's package under `PKG_NATIVE_CACHE_PATH`, else
  `$HOME/.cache/pkg/<hash>` — run 6 left 38 MB under every lane dir and
  crashed the 2026-09-15 dream; since ruling 3 (2026-09-16) every ENGINE
  worker's harness gets `PKG_NATIVE_CACHE_PATH = $DSH_HOME/cache/<worker
  id>`, removed at worker end — per worker, never shared, because pkg
  re-copies on every launch with plain overwrites and a sweep's
  simultaneous lanes would race on one directory. The same directory
  holds the worker's `hooks.json` (change 12, 2026-09-16): both
  composition patches mount the harness's Claude Code hooks bridge
  (`@deepseek-ai/dsh-hooks-claude-code`, §14 item 1a) with `configPath:
  !!js process.env.DSH_HOOKS_CONFIG`, an env name the engine adapter sets
  per worker and the shell scrub drops (`DSH_*`); its one PostToolUse
  command hook, `cat` of the supervisor's meter file, puts the §5.1
  context meter after every tool result past 20k. One config per
  process, read at startup — written before the harness starts. The
  bridge injects the `shell` service, which Minimal never provided (its
  persistent bash runs over the PTY seam), so the minimal patch also
  inserts the sdk profile's `bash-sandbox` executor row — it registers as
  `ctx.shell` over the subprocess, sandbox and sandbox-policy rows Minimal
  has, adds no tool, and the boot check (2026-09-16) showed the composed
  tool rows unchanged. Reads are
  fenced, not walled (§4.2): the supervisor's lane fence trips `scope` on
  `..`, `$DSH_HOME`, `$AGENT_RUNTIME`, any mention of SEARCH_AUTH_FILE,
  the repo's `.env`, the body's literal path and `$PKG_NATIVE_CACHE_PATH`
  (the harness forwards that variable to the shell; ruling 3) — read in
  path-keyed arguments and commands only; any
  other outside path is a `scope` EVENT for the lead, never a stop (the
  scan's probation ended after run 3, 2026-09-15: seven false trips, zero
  true, demoted); file contents, search queries and notebook text are
  never scanned; quoted paths are scanned whole (the repo path has a space);
  the `tools/` scripts are reachable by absolute path, read-only, and
  `tools/` is exempt from the scope trip; `web_fetch` is GET-only, no
  request bodies. Lanes are the only workers with network
  and therefore the only workers with nothing private in reach.
- Claude Code's own subagents are NOT the swarm: they run on Fable and
  bill the subscription. The lead may use them for its own short in-repo
  lookups; lanes are always DeepSeek workers. If one lane needs
  frontier-grade judgment, the lead runs that ONE lane itself as the
  quality anchor — a per-brief choice, not a mode.
- COST: ~N worker runs (cents) + one lead synthesis over N short reports.
- SECOND WORKER MODEL: an IDEA on record (§2), not a plan — "one lane on
  GLM" for factual sweeps, revisited only on scorecard evidence.

## 8. Memory

The design below is v3.1 §3d (decision 2026-08-27) carried in full — copied
here rather than referenced, because SPEC-v3.1.md is history and this is not.
Three v2 edits: the Signal ingestion path is gone, the consolidation pass is
replaced by the DREAM (8.2), and two rules from the v1 blueprint's context
policy are added to the write contract. `memory/FORMAT.md` (the entry rules
the dream reads) is written by hand from 8.1 at step 6 and committed; the
two must agree.

### 8.1 Layers, entries, contracts (v3.1 §3d)

CONTEXT POLICY (blueprint Layer 3, in order of preference): keep it OUT of
context (agentic search over files, never pre-loading) → ISOLATE it (big,
separable work goes to a worker with a fresh window that returns
conclusions) → DISTILL it (whole-document synthesis in a throwaway session
that leaves a distilled artifact in `memory/artifacts/`) → COMPACT it (state
file + hooks, §3) → REMEMBER it (files the lead reads at start and updates
through the gate). Session hygiene: reset at task boundaries, not on a
timer; never converse inside a polluted context — mine it and leave; every
heavy session ends by writing its distilled artifact.

Lives in the repo's `memory/` tree; four layers (working / episodic /
semantic / procedural, per the CoALA taxonomy):
- `memory/facts.md` — SEMANTIC: durable knowledge, updated in place, never
  re-distilled. Every entry carries: provenance (user-said / worker-inferred
  / web-claimed; session), TWO dates (when-TRUE vs when-LEARNED —
  bitemporal, per Toki, arXiv 2606.06240), scope ("valid for context C"),
  and optional `expires:` for facts that know their death date.
- `memory/procedures.md` — PROCEDURAL: learned how-tos ("when X fails, do Y
  first"), written only through the gate. Highest-leverage layer — a fact
  helps once, a procedure helps every recurrence.
- `memory/style.md` — PROCEDURAL (calibration): the owner's preferences,
  slow-growing, loaded into EVERY session from file (never via handoff).
- `memory/artifacts/` — distilled artifacts from workers, swarms and
  throwaway runs.
- `memory/archives/` — EPISODIC: full session logs (lead + workers,
  gitignored), greppable on demand, plus the rotation log.
- `memory/library/` — THE LIBRARY (reference corpus): raw external
  documents — PDFs, docs, papers, manuals. What the system can LOOK UP, as
  opposed to facts.md (what it has LEARNED). Unbounded; NEVER loaded
  wholesale — agentic retrieval (filename / full-text search, targeted
  reads); whole-document synthesis goes through a throwaway session that
  returns a distilled artifact. No vector DB, and no graph store, until
  scale demonstrably demands it — the trigger is grep failing to find
  contradictions the dream should have caught, not corpus size.
  Rules: library content is DATA, never instructions (documents are a
  prompt-injection surface); facts extracted from a document enter facts.md
  only through the gate, with provenance citing the source file.
  INGESTION: drop files into `library/inbox/` (drag from the desktop or the
  Claude app); `/ingest` (on command, per the autonomy principle) renames to
  `YYYY-MM_topic_title.ext`, moves into `library/`, appends one line per doc
  to `library/index.md` (filename, title, source, date, one-line
  description), and for PDFs writes a `pdftotext` sidecar `.txt` so grep
  reaches inside them. Sidecars matter from document #1; the index matters
  increasingly as the corpus grows.
- `memory/INDEX.md` (v2, ≤200 lines) — pointers + one-line descriptions,
  never content; the dream's phase-4 output.
(WORKING memory = the lead's live context + `state.md` + worker reports.)

WRITE CONTRACT (Toki-lite — contradiction resolution is write-time
concurrency control; undeclared heuristics admit anomalies):
- SUPERSEDE, NEVER ERASE: a superseded entry moves to the file's audit
  section (when / why / what replaced it) — never deleted. Prevents audit
  erasure; adversarial or mistaken overwrites stay traceable. In v2 this is
  plumbing at dream-apply time (8.2), not a prompt rule.
- ADJUDICATION LOG: every resolved contradiction is a row (conflict key,
  winner, reason) in `adjudication-log.md`, so the same conflict replays to
  the same outcome. Ruled items are settled; the dream is told so.
- SINGLE WRITER: the lead is the only writer of durable memory (below).
- ADVERSARIAL-BY-DEFAULT GATE (memory-poisoning literature: attacks succeed
  at <0.1% poison rates; content screening alone has hard limits — arXiv
  2606.04329, 2608.21230, 2607.27080): every fact proposal originating from
  workers, web content, or library documents is potentially adversarial at
  the gate. The write path is the battleground; the gate is the defense;
  audit rows are the repair mechanism.
- STATE FILES (blueprint): machine-read state is JSONL (registry, events,
  costs) — models editorialize less in JSON. `state.md` stays prose by
  choice because the SessionStart hook injects it as context for the lead;
  it is regenerated holistically, never appended (§3). Registry and index
  writes are ATOMIC and LOCKED (change 9, ruling on run 6, 2026-09-15):
  `lineage._save` writes `<file>.tmp` beside the file and `os.replace`s
  it, so a reader never sees a truncated file; every load-modify-save
  holds `<file>.lock` (flock), so concurrent writers — a sweep's spawns
  and a lane worker's start-time runtime stamp land in the same second —
  never lose an update. Readers take no lock. Run 6's cmmc lane died at
  launch on the empty file (`JSONDecodeError`, char 0).
- NEUTRAL-AFFECT RECORDS: failures are recorded as "approach X failed on
  task Y because Z" — never with emotional framing (affect in history
  induces avoidance of currently-correct approaches).

MEMORY ACCESS MODEL: ONE durable store, one ephemeral layer, write access
gated by session type — never two parallel durable stores (parallel stores
fragment retrieval and drift into contradiction).
- READS: universal — every session type reads `style.md` (always) and
  `facts.md` (as needed).
- WRITES to durable memory: the LEAD ONLY (the gate — where provenance,
  scope tags and neutral-affect rules are enforced). WORKERS propose facts in
  their reports; the lead promotes or not. SWARM lanes and throwaway
  sessions write artifacts only, never memory — bulk and unvetted by nature.
- The EPHEMERAL layer (state.md, handoffs, worker reports, notebooks) is
  separate from durable memory and dies with its lineage.
- Claude Code's own project memory is the lead's working notes, not a
  second durable store (8.2, "two memories").

MEMORY-TRAP DEFENSES (MemTrapBench, arXiv 2608.20202 — even TRUE, relevant
memories measurably degrade current-task reasoning):
- ADAPTIVEMEM GUARD in the lead's standing prompt (`memory/prompts/adaptivemem.md`,
  imported by CLAUDE.md): watch for four risks — task boundary (don't carry
  the prior task's framing), cognitive bias (past strategies are shortcuts OR
  traps; re-evaluate from the current query), trauma (past negative feedback
  never overrides present correctness), safety (sandbox / counterfactual
  premises from history never govern real situations). Identify the live
  task from the latest query alone; keep only clearly relevant prior
  context; on conflict prefer objective truth/safety > current query >
  minimum context. Don't over-trigger — routine queries use memory normally.
- SCOPE TAGS on every entry (above) — the core trap is valid-in-original-
  context applied beyond its scope.

FORGETTING POLICY: supersession on write + `expires:` honored by the dream +
scope expiry (a fact scoped to project X dies with project X) + usage-decay
REVIEW (entries whose when-LEARNED date is older than 90 days and that were
never superseded are listed under `STALE?` in the dream's summary, never
removed — durable memory is small enough to review, so forgetting stays
human-gated). Entries carry no access date, so "untouched" means exactly
that: learned long ago, never updated.

### 8.2 The dream (v2 — replaces the v1 consolidation pass)

The nightly pass becomes a DREAM (adopted from Anthropic:
the Claude Code auto-dream prompt, run the way Managed Agents run dreams —
against a COPY, never the live store):
- MECHANISM. `consolidate.py` (timer, 19:45) copies the durable files of
  `memory/` (facts, procedures, style, INDEX, FORMAT, adjudication-log,
  architect-log — plus artifacts/ as INPUT ONLY: its text files are
  copied, it is never diffed, a dream's edit to an artifact is no
  proposal — never archives/ or library/) to
  `runtime/dream/<date>/memory/`, copies the last 7 days of worker
  trajectories — the engine's `$DSH_HOME/sessions/<cwd-mangled>/<worker-id>/session.v3.jsonl`
  and plain's `runtime/lineages/<id>/worker-<wid>.log` (§4.2) — and of
  `runtime/handoffs/` read-only beside it as `archives/`, then runs `claude -p --model claude-fable-5-1
  --allowedTools Read,Grep,Glob,Write,Edit` IN THAT DIRECTORY with the
  prompt `memory/prompts/dream.md`. No Bash: the prompt's transcript
  search uses Grep. The dream reads, greps narrowly, and WRITES — into the
  copy.
- BINARIES AND CRASHES. A non-UTF-8 file is skipped everywhere — copy,
  archives, diff: the first unattended dream (2026-09-15) crashed in the
  diff step on the harness package cache (`.cache/pkg/…/koffi.node`) that
  run 6's gsa lane had left under `memory/artifacts/` with its shell HOME
  = lane dir, and no event recorded it. Any exception after the copy now
  marks the night FAILED with a `dream_failed` event naming the error
  (exit 3); summary.md and dream.log stay, no DIFF.md is written. The
  fence's git snapshot decodes with errors=replace, so a binary in the
  lead's own dirty files cannot crash the night either.
- THE FENCE, honestly: the copy is a convention — Write/Edit can name an
  absolute path. So the fence is checked, not assumed: `consolidate.py`
  records `git status --porcelain` AND `git diff HEAD` for the whole repo
  before the dream and compares both after (status alone cannot see a
  second edit to a file that was already dirty). Any new change outside
  `runtime/dream/<date>/`
  means the dream stepped out of its copy: the night is marked FAILED,
  no DIFF.md is written, an EVENT names the paths, and nothing is
  reverted automatically — the owner reverts by hand, so a lead's own
  uncommitted edits from that day are never destroyed by the check.
- OUTPUT. The script diffs live `memory/` against the copy and writes
  `runtime/dream/<date>/DIFF.md` + the dream's own summary. That diff IS
  the proposal. No prose proposals file, no "carried items" bookkeeping —
  the next dream diffs against whatever was applied.
- THE GATE APPLIES. Conrad reads the diff in the lead session and accepts
  all or hunk by hunk: `plumbing/apply_dream.py <date>` applies every
  hunk; `--hunks 2,5` applies the numbered ones (DIFF.md numbers them);
  then the lead commits. Rejected hunks vanish with the copy. This is the Managed
  Agents step "review the output and discard it if you don't like it."
- DELETES become SUPERSESSIONS — at APPLY, mechanically. The dream deletes
  in the copy exactly as the original prompt says; when the gate accepts a
  hunk that removes a line from facts.md or procedures.md, the apply
  script appends that line to the file's audit section with the date and
  the reason the dream gave for it (the prompt asks for one line per
  removal and per resolution: `file · old · new · reason`) before
  committing. Not a prompt rule; plumbing.
  Nothing is ever erased from live memory.
- CONTRADICTIONS. The dream resolves them in the copy ("latest value");
  the diff shows old and new; each accepted resolution becomes a row in
  `adjudication-log.md`. The gate approves resolutions, it does not
  hand-resolve.
- PRESERVE UNCHANGED: `style.md`, `adjudication-log.md`, every audit
  section, `prompts/` — enforced at apply (hunks touching them are
  rejected automatically), and the dream is told ruled items are settled
  (the one prompt line with no plumbing substitute: otherwise "latest
  value" re-flips a human ruling every night).
- TWO MEMORIES, BY DESIGN: Claude Code's own project memory
  (`~/.claude/projects/<project>/memory/`) is the lead's working notes —
  its built-in auto-dream (reported as: after 24h and >5 sessions, or on
  `/dream` where that command exists) keeps that tidy with nothing for us
  to build. `memory/` in the repo is the durable,
  gated store — the nightly copy-dream above. This is v3.1's "one durable
  store, one ephemeral layer" rule, unchanged. IDEA on record: when
  `/dream` reaches this install, symlink the project memory folder to the
  repo's `memory/` and let git be the copy (review = `git diff`, apply =
  commit, discard = checkout) — needs a "lead reads memory at HEAD" rule
  first.
- INDEX. `memory/INDEX.md` (a committed file, ≤200 lines) is the dream's
  Phase-4 output: pointers + one-line descriptions, never content.
  facts.md stays the content file.
- Read-only tools would be pointless here (the dream must write); safety
  comes from the copy plus the before/after check above. Fallback if the CLI
  is unavailable: skip the night; a DeepSeek `think` call cannot run a
  multi-phase agentic pass and should not pretend to.
- Same rule when `claude -p` exits non-zero, times out, or refuses (an
  empty reply): the night is SKIPPED — a `dream_skipped` EVENT with the
  exit code and the stderr tail, no DIFF.md, the copy kept for
  inspection; nothing retries and nothing falls back.
- Judge CALIBRATION is removed with the verifier. Archives now include
  worker trajectories (§4.2).
Open gate items carried (OWNER ONLY — leftovers of Conrad's v1 runs, not
part of the kit): the v1 proposals of 2026-09-04 / 2026-09-05 (in
`runtime/`, prose format) — rule on them once by hand; junk archives
0135/0139.

## 9. Data tiers (written now, dormant until a training-tier model exists)

RULE: data tiers are a property of the WORKSPACE, not the task. Every
directory a worker may operate in is `open` or `private`; open roots are
registered explicitly in `configs/data-tiers.md`; everything else is
private by default. A model whose provider may train on traffic is a
TRAINING-TIER model and may only be spawned into an open root. The plumbing
refuses anything else; no brief, flag or lead judgment overrides it.
Fences: (1) bubblewrap jail per training-tier worker — only the open root
bound, `.git` and `.env` masked, no home, `--unshare-net` unless the brief
binds it; (2) `env -i` + only that provider's key; (3) deterministic
pre-flight scan of the brief (paths outside root, inlined file bodies,
secret/PII patterns) → refuse loudly; (4) `data_tier` stamped on report and
ledger. The agent-system repo itself is NOT open (memory/ holds personal
facts). One unit test spawns a training-tier worker told to read outside
the root and asserts refusal.

## 10. Observability and cost

- `runtime/` throughout this spec means `$AGENT_RUNTIME` from `.env`
  (v1 default `~/Desktop/agent-system-runtime`) — the body, gitignored,
  outside the repo.
- Worker trajectories (§4.2) are the ground truth; the lead's own
  transcripts live in `~/.claude/projects/`.
- `runtime/costs.jsonl` (built step 7, 2026-09-15): one row per worker,
  appended by `worker.py` when the report is filed, from the API usage
  fields — ts (the worker's START), lineage, worker, model, runtime,
  preset, data tier, tier (peak / off-peak / subscription), calls, input
  (whole prompt), cache read, cache miss, output (reasoning included),
  reasoning, usd, source. Priced by `costs.py` from `configs/prices.md`
  (editable: USD per 1M per model and tier, plus the peak spans of §2) at
  the tier of the worker's start time; a row is never repriced. The
  dream's `claude -p` is a `subscription` row: usd 0, seconds counted.
  Step 8 (2026-09-15) adds `search_requests` and `search_usd` per row — a
  lane's `searches.jsonl`, one line per backend call, priced from the
  web-search table of prices.md and folded into `usd` — and
  `runtime/scorecard.jsonl`, one row per sweep (§7).
  `costs.py --backfill` writes a row for every filed report that has none
  (engine workers from their trajectory's usage fields — the ground truth,
  never the text — else the report's cost dict; idempotent). `/status`
  prints today (UTC) · 7d · all; caps (§4.3) tune from it. One stdlib file.
- Langfuse: KEPT AS IDEA (Conrad, 2026-09-14; not planned, not built).
  Two jobs it would do: trace browsing (covered more cheaply by
  trajectories + costs.jsonl + /status) and a home for the EVAL SUITE —
  datasets of real tasks, runs per configuration, side-by-side scoring.
  Bring it in only when evals/ has grown from real failures to the point
  where comparing runs from a JSONL by hand is annoying. Six containers;
  ClickHouse corrupted twice on the v1 host; nothing in v2 depends
  on it.
- Weekly transcript read stays the early-warning ritual. The weekly
  ARCHITECT ENTRY stays as practice: one dated entry in
  `memory/architect-log.md` evaluating the system — what the cost ledger,
  swarm scorecards, dream diffs and adjudication log show; which §15
  decisions now have evidence; what to change or close, with the evidence
  cited.

## 11. Host, access, lifecycle

- Any Linux (systemd) or macOS machine that runs Claude Code and
  Python ≥ 3.10. Nothing in v2 needs a GPU or a particular distro.
- Services on the host: the Claude desktop app (link + phone access) and
  one user timer (`consolidate.timer`). That is the whole footprint.
- Access: Claude app link only. The app's shell IS the remote shell —
  commands, files, scripts on the desktop from the phone.
  KEPT AS IDEA (Conrad, 2026-09-14; not planned, not built): official
  Tailscale (free, no self-hosting) on desktop + phone, plus an SSH client
  on the phone, as a recovery lane for the one case the app link cannot
  cover — the app itself down, logged out, or the machine at the LUKS
  prompt. Build it the first time that actually happens, not before.
  Sunshine/Moonlight likewise: only if a GUI ever needs operating remotely.
- Removed: headscale, DuckDNS, router forwards, Caddy relay, acme.sh certs,
  Sunshine, signal-cli + watchdog (bot number can lapse), Langfuse stack,
  `calibrate.timer`, `dsh-tailnet-relay`, `agent-system` (dsh) service.
- Sleep/suspend may stay enabled (the v1 "sleep masked" workaround is
  retired).
- Backups: genome → private GitHub remote `backup` after every meaningful
  commit (PAT rotated 2026-09-14; lives in `~/.git-credentials`, never in
  `.git/config` or the repo). Body (runtime/, archives) single-disk by
  choice; snapper local snapshots — verify they cover /home.
- SECURITY INVARIANTS (v3.1 §5, the four that survive the access-layer
  removal): (1) destructive or irreversible actions require an explicit
  confirmation; (2) secrets never transit briefs, reports, chat or
  commits — `.env` only; (3) LUKS2 full-disk encryption, no auto-unlock —
  reboots wait at the passphrase prompt, accepted; (4) every process the
  system runs is unprivileged (no sudo in any timer, hook or worker).
- MAINTENANCE (v3.1 §6b, what remains): SDK and `claude` bumps only via an
  `exp/` branch with the pin/bump procedure (§4.2); rotate API keys on any
  suspicion of a leak (one `.env` edit); after a kernel update, confirm
  sleep/resume still works.

## 12. Genome / body, branches, tests (carried from v3.1 §7)

Unchanged: REPO = GENOME (behavior-defining, branch-versioned), RUNTIME
STATE = BODY (gitignored). `runtime/` here and everywhere in this spec is
`$AGENT_RUNTIME/`, outside the repo (§10); the `.gitignore` entry only guards
against an accidental in-repo copy. `main` = stable, `exp/*` = experiments, promote
by merge after the suite is green + flight tests. Tests are hermetic (no
API calls) and remain the regression gate; both runtimes are under the
shared contract test; the data-tier refusal test is added when §9 wakes.
Two v3.1 §7 rules restated because they bind v2 specifically:
- EVALS (`evals/`): 20–50 tasks harvested from real failures, outcome-graded
  never transcript-graded; pass^k (works every time) is the bar for
  `main`, pass@k for capability. Eval runs are worker runs — they cost
  money and run deliberately, never on every commit.
- NOTHING BEHAVIORAL LIVES ONLY IN AN APP'S STORAGE: hooks, slash commands,
  `CLAUDE.md`, compositions, prompts and eval definitions are files in the
  repo. Claude Code's `~/.claude` holds the lead's working memory and
  login, nothing that defines how the system acts.

## 13. Command surface (single source of truth — new commands are added HERE first)

`!` registry → Claude Code slash commands / skills in `.claude/`:
`/worker <brief>` (spawn; `--preset`, `--runtime`, `--n`) · `/status` ·
`/steer <id> <msg>` · `/stop <id>` · `/resume <id> [note]` ·
`/check <rungs>` · `/swarm <question>` · `/consolidate` · `/ingest` ·
`/rotate` (manual handoff).
Removed: `!verify`, `!do on/off` (toggle), `!think` as a command (it is the
`think` preset), `!escalate`, `!calibrate`, and the lineage commands
`!throne` / `!untie` / `!retie` (§3: one lineage per directory).

## 14. Novelty budget — the named unfamiliar pieces (McKinley's tokens)

This section is about TECHNOLOGY CHOICES, not code style. Code style is
rule 1 in the preamble and applies everywhere, including inside these
pieces.

1. dsh ENGINE as the worker runtime (rc-grade, someone else's protocol) —
   paid for with the plain-loop fallback and the pin/bump procedure.
   1a. The engine's HOOKS BRIDGE plugin (`@deepseek-ai/dsh-hooks-claude-code`,
   mounted by both composition patches for change 12's context meter: a
   PostToolUse command hook whose stdout JSON adds one context line after
   each tool result, the only channel that reaches a running engine turn) —
   paid for with: the bridge is FAIL-OPEN (an unreadable config or a failing
   hook is logged and the agent continues), HAND-TESTED AT BUILD (an offline
   config dump and a harness start/close with the patch before the commit),
   and PLAIN'S TRAILER AS THE FALLBACK (the same meter line appended to the
   tool result in Plain.turn; run 7's trajectory proves the engine side).
2. Two-layer SUPERVISION with the lead woken by `Monitor` — new mechanism;
   paid for with the cost-discipline rule and tunable trip table.
3. (half) SWARM web tools + sources contract — paid for with: two stdlib
   scripts with hermetic tests, the report sanitizer, the lane fence plus
   the harness's own credential scrub, the scorecard (a mode that keeps
   scoring badly on parallelism or completion is not earning its cost),
   and `--mode` routing withheld until scorecard evidence.
4. CLAUDE CODE HOOKS (PreCompact / SessionStart / UserPromptSubmit) —
   nobody here has watched one fail; paid for with: each hook is a ≤10-line
   shell script that only copies and prints files, tested by hand once
   when built (the prompt hook at step 3; compaction and session-start at
   step 5), and the system works without them (state.md is still written
   by the lead; the status line is also in `/status`).
Everything else is stdlib, JSONL, git, systemd, flags.
Rules for this list (so it stays bookkeeping, never a veto):
- WHAT COUNTS: a dependency or mechanism whose failure modes we do not
  yet know here. Not "new to us" or "clever" — unknown failure modes.
- ADDING ONE: name it here and say what pays for it (fallback, pin,
  test, tunable). A payment, not a permission — the list cannot say no.
- RETIRING ONE: once a piece has run pinned for a while with no
  surprises, it is boring; strike it. The list shrinks as well as grows.

## 15. Open decisions

- §2 CoT flight test on V4.1 (decides whether presets are cognition or capability).
- Second worker model (GLM, one swarm lane) — an IDEA on record (§2), not a plan.
- Tailscale + SSH recovery lane — an IDEA on record (§11), not a plan.
- Langfuse — an IDEA on record (§10) for the eval suite, not a plan.
- Check mode (§6) — only if a task class shows repeat single-worker failure.
- FUSION OBSERVATION RUN (owner, optional, ~$20): put three or four of
  Conrad's real tasks through Devin Fusion (Desktop/CLI), read the session
  transcripts it hands back, and note three things we could not get from
  Cognition's blog: how granular their lead's briefs are, how often the
  lead intervenes mid-task, and what their reports contain. Then cancel.
  Learning behavior from your own account is fine; decompiling, extracting
  prompts, or reusing their text is not (terms + copyright).
- The §2c onboarding pattern is Appendix A (part of the kit). The owner's own planned domains (math / quant / security) are in DOMAINS-owner.md, outside the kit. Eval task set; dshx gateway (moot unless dsh returns as a surface).

## 16. Build order — one layer, one flight test, commit + push each

(The builder's copy of this order, as a paste-ready prompt, is `KICKOFF.md` —
since 2026-09-16 the v2 REPLICATION PROMPT: the build is complete, and that
file carries this order with the lessons learned folded into each step.)

1. Clone `backup` on the fresh host, `.env` from the disk backup — it is
   gitignored, so a clone never contains it (rotate the PAT if it was
   ever embedded in a remote URL), `pip install deepseek-harness-sdk==<pin>`, record `claude
   --version` in configs/stable.md; then `CLAUDE.md` v2 + memory imports
   + state-file discipline. TEST: suite green; `claude -p ping` answers;
   a fresh session reads HANDOFF/state and reports the open items.
2. Workers: `runtimes/{engine,plain}.py`, `worker.py` adapter, presets,
   ask-back, `/worker`, `/status`. TEST: one real brief on each runtime →
   report with evidence; AND the §2 CoT flight test.
3. Supervision: supervisor trip rules, events file, `Monitor` wake, steer /
   stop / resume, prompt-submit status hook. TEST: a deliberately ambiguous
   brief must trigger an ask-back; a looping brief must trip `repeat`; a
   long brief gets the 26k wrap-up steer and stops with a report; one that
   ignores it is force-stopped at 32k with a PARTIAL.
4. `check.py` ladder wired into definition-of-done. TEST: a coding brief
   with a test suite; one rung must reject a planted failure.
5. Rotation: status line shows context size (100k nudge, 128k now) and
   state.md age; `/rotate` rewrites state.md, writes the handoff, and
   the next session resumes from it; PreCompact backstop. TEST: `/rotate`
   mid-task → the new session continues from state.md without
   re-asking; leave state.md untouched for N prompts → STALE shows;
   force a compaction → the handoff exists and a compaction EVENT is
   logged.
6. The DREAM: write `memory/FORMAT.md` (from 8.1) and an initial
   `memory/INDEX.md`; `consolidate.py` copy → `claude -p` with
   `memory/prompts/dream.md` → DIFF.md; `apply_dream.py`; before/after
   repo check; timer; (owner) gate pass over the v1 09-04/09-05 proposals. TEST: one run produces a diff the gate can apply
   hunk by hunk; live memory/ unchanged until applied.
7. Cost ledger + `/status` cost line. TEST: rows match the API dashboard.
8. Swarm mode: web tools, sources contract, `/swarm`. TEST: a 4-lane
   question returns four sourced reports and one synthesis. BUILT
   2026-09-15 (suite 53). FLIGHT TEST PASSED 2026-09-16 on run 7
   (swarm-20260916-89cf, engine/minimal, Conrad's ruling): 3 of 4 lanes
   filed sourced reports (10/6/8 sources), all done-at-cap; synthesis with
   five CONTRADICTIONS; scorecard row, verdict 3/5; gsa answered on time
   and hit max-tokens on a 39k-token answer. Residuals as open threads,
   not gates: the meter from 12k with M from the projected curve; the
   brief's REPORT line stating the §4.1 ≤500-token contract with bulk to
   the notebook by path; parse_sources accepting ANY LINE
   CARRYING A URL, not only the dash-bullet form (Conrad, 2026-09-16,
   completing the cut-off ruling).
9. PROMOTION DONE 2026-09-16 (Conrad's plan): `SPEC-v2.md` → `SPEC.md`, the
   v1 spec → `SPEC-v3.1.md`; references swept in the live docs, code and
   tests; docs/history/ and memory/ untouched (memory/'s spec references
   are a gate item in HANDOFF.md). KICKOFF.md rewritten as the v2
   replication prompt 2026-09-16. MERGED to `main` 2026-09-16 (fast-forward
   at 153ccd4, suite green on main, pushed); work continues on main and
   `exp/v2` stays as the build record.
Later, on evidence: check mode · second model · Tailscale · data tiers
waking · Langfuse.

## Appendix A — Domain-onboarding pattern (general; part of the kit)

How ANY domain enters the system. Carried verbatim from SPEC v3.1 §2c.
The original owner's own planned domains are NOT part of the kit — they
live in DOMAINS-owner.md, outside the shared system, as worked examples
only. A builder adds the domains they want, or none.

(v3.1 §2c — decision 2026-08-27)

How the system grows a new capability (math is the planned first instance):
DOMAIN = CAPABILITY PLUGIN + WORKSPACE PROJECT.

- The CAPABILITY PLUGIN (small, in this repo — genome) bundles, as one
  installable/removable/branch-testable unit:
  1. Toolbox additions — domain CLIs, logged in configs/toolbox.md
     (bash-reachable, catalog-invisible, per the tool-surface policy).
  2. Skills — the craft of driving the domain's pipeline.
  3. AGENT DEFINITIONS AS FILES — named domain roles (e.g. sketcher,
     prover-manager, skeptic) as on-disk recipes (dsh cordis.yml / ZCode
     Markdown): persistent identity + tuned tool scope (one-knob: tuned
     cognition), zero idle cost, instantiated only when spawned — and ALWAYS
     spawned under the existing worker contract (briefs, evidence reports,
     ownership invariant, caps). Identity from the file, discipline from
     the contract.
  4. Verifier config — which verification tier the domain uses (formal
     checker > exact arithmetic > LLM judge; e.g. math: `lake build`
     outranks GLM).
  5. Milestone plan — phased adoption, entering via the exp branch.
- The WORKSPACE PROJECT (the domain's own repo, in ~/Desktop — body): the
  actual machinery, code, and campaign state. Independent git, testable
  standalone. The plugin is the BRIDGE: campaign runs carry task IDs into
  Langfuse, results flow up as worker reports, verified wins pass the
  curation gate into memory. Separate body, shared nervous system.
- REV PIN (2026-08-27): the plugin records the workspace repo's path AND its
  expected git rev (one line, updated deliberately). The genome always knows
  exactly which domain-stack version the system expects — drift-proof
  without monorepo weight. Separate repos are for HEAVY domains (own
  branching, own pins, bulky artifacts — math qualifies on all three); a
  trivial domain may live entirely inside its plugin.
- Matrix rows only for genuinely RECURRING session shapes (math earns two:
  sketch worker → Minimal; campaign worker → Standard); one-offs are
  handled by the brief. Keeps the matrix small at twenty domains.


v2 note on the pattern: agent-definition files become worker presets
(compositions, not dsh cordis / ZCode files); "verifier config" means
which checker rungs apply (§6) — there is no LLM-judge tier; a formal
checker (e.g. Lean) is rung R1 and is the only pass that ships alone;
"task IDs into Langfuse" means task IDs into `costs.jsonl` and the
trajectories (§10).
