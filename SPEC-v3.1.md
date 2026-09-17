> SUPERSEDED 2026-09-16 — the v1 system's spec (its internal version 3.1), kept as history. The canonical spec is `SPEC.md` (v2).

# SPEC — canonical replication spec (v3.1, 2026-08-27)

Purpose: this file alone should let any AI system (or person) recreate the
design 1:1. If a detail conflicts with another file, SPEC.md wins. Visual
reference: `../agent-system-diagram.html` (same architecture, rendered).

## 1. Identity

Personal always-on agent system. One desktop host. Core system: no Claude /
no Anthropic dependency — the replication kit builds a complete system with
zero Anthropic accounts. AMENDED 2026-09-03 (Conrad, reversing the closed
no-Claude decision): THIS instance enables the FABLE MODULE (§2d) to the
full phase 0–6 scope. Two model stacks, both stable, remain the runtime.
Verification replaces a frontier escalation tier for generation; Fable
enters as judgment, audit, and (phase 6) command, never as the token mill.
All state and config in one git repo (this repo).
AUTONOMY PRINCIPLE (2026-08-27): "always-on" means 24/7 ACCESS, not
autonomy — NOTHING executes without Conrad initiating it. No self-starting
loops; the system waits, reachable from anywhere. ONE sanctioned exception:
the nightly CONSOLIDATION PASS (§3d) runs on schedule — permitted because it
cannot act: it only PROPOSES to the curation gate and writes nothing durable.

## 2. Models (exact)

| Stack | Harness | Model string | Mandatory setting |
|---|---|---|---|
| A | DeepSeek Harness (`dsh`), github.com/deepseek-ai/deepseek-harness, run: `npx @deepseek-ai/dsh web` | `deepseek-v4-flash-vision-exp` | thinking ON, effort `max`, every call |
| B | ZCode (Z.ai desktop ADE, z.ai) | `glm-5.3-flash` | max reasoning, every call |

- No tiers. No routing between models by task type (role split: TBD, see §8).
- **DeepSeek CoT presets (normal/api-output path only):** V4 produces two
  distinct chains-of-thought depending on the API-visible tool catalog:
  "We/Let's" (Minimal catalog; stronger — Project2 99/96) and "Let me"
  (Standard 25-tool catalog; 91/92). Policy: **default for agentic sessions =
  `anchored-standard`** (github.com/xiaobright/dsh-anchored-standard — anchors
  the We/Let's CoT on a Minimal-aligned first request, unlocks the full
  Standard catalog after the first tool call; 98/99 with all tools);
  **pure reasoning/planning sessions = plain Minimal**; **Standard = fallback
  and eval arm** (official composition, never stale — used if anchored breaks
  on a dsh upgrade, and kept in the eval matrix). Anchored is pinned to dsh
  0.1.0-rc.5 and snapshots the Standard composition — re-review on every dsh
  upgrade; catalog swap costs the prompt cache once per session; promotion
  happens only after the first tool call. Co-candidate under evaluation:
  `eternal-minimal` (same author family) — the visible catalog stays the
  Minimal pair for the WHOLE session while all Standard tools stay registered
  and execute for real behind a `dshx` bash gateway; zero extra calls, zero
  cache breaks; instruction files hinted at rather than injected (model reads
  them itself); gateway results capped at 12k chars (configurable).
  **Deep-think segments:** mid-session
  hard-reasoning is delegated to a Minimal-preset subagent (fresh context,
  bash+editor only → guaranteed We/Let's CoT) that returns a distilled
  conclusion to the main session; surface = `!think <q>` and/or agent-initiated
  delegation. Verifier layer (§3) wraps whichever preset the task runs under.
- Known quirks to preserve: DeepSeek thinking mode silently ignores
  temperature/top_p; if request includes `tools`, `reasoning_content` must be
  passed back every subsequent call or API returns 400. Vision-Exp has no FIM,
  no open weights, no version pin — fallback model if it degrades/disappears:
  `deepseek-v4-flash` (one-edit swap).
- API keys: `DEEPSEEK_API_KEY`, `GLM_API_KEY` in `.env` (gitignored). Never in
  configs, never in files agents casually read.
- Version pins: record exact dsh + ZCode versions in `configs/stable.md` once
  running; upgrade harnesses only via exp branch.

## 2b. Preset-assignment matrix (decision 2026-08-27 — closes most of the
tools & presets item; a "thinking choice" designed by Fable, accepted by
Conrad)

Principle: the CoT locks per session, but the SESSION is the unit of work —
modes are switched by SPAWNING, never mid-context. Second principle, the
one-knob rule: a worker brief's tool scope IS its cognition — the visible
catalog triggers the CoT, so choosing a worker's tools consciously chooses
its mind.

| Session type | Preset / condition | Why |
|---|---|---|
| Main window on DeepSeek | plain MINIMAL, permanently | direction/judgment is planning-shaped (We/Let's); the throne holds no tool-heavy work by design |
| Worker: planning / research / analysis / synthesis | MINIMAL | deliberation is the work |
| Worker: mechanical execution (clear path, tight brief) | STANDARD | "Let me" stepwise suits grinding a known plan; loop risk fenced by brief + 25-step cap — Standard's legitimate home |
| Worker: plan-then-execute | ANCHORED-STANDARD | We/Let's anchored, tools unlock at first call |
| `!think` | MINIMAL subagent | already specced (§2) |
| Verify candidates | TOOL-FREE (no catalog in request) | purest We/Let's condition; what generation-from-history does naturally |
| Dump-mode synthesis | MINIMAL condition, read-only tools | whole-context reading, no execution |

Eval arm: MODE-MIXED verify sampling (3 tool-free + 2 Standard-condition
candidates) — decorrelated CoT styles for the judge to harvest; same cost.

TOOL-SURFACE POLICY (decision 2026-08-27 — closes the plugin-surface item):
- ZERO MCP servers by default. The native catalogs cover the design, and in
  this architecture every added catalog entry has a COGNITION price (the
  visible catalog shapes the CoT — the one-knob principle).
- Capability gaps are solved CLI-FIRST: a command-line tool reached through
  bash adds full capability with zero new catalog entries and zero CoT cost.
- MCP is permitted ONLY for a specific service's own/official MCP server,
  when it meaningfully beats that service's CLI — and it enters through the
  exp branch like any change. Never general-purpose MCP tool packs.
- Install-time check: whether dsh speaks MCP natively is unconfirmed; ZCode
  plugins can bundle MCP servers per its docs.
- SCENARIO TOOLKITS (2026-08-27, e.g. Lean for math): domain tools enter as
  installed CLIs — on PATH, reachable through bash, catalog-invisible. Even
  Minimal workers can use them (bash+editor suffices), so deliberation-shaped
  domains keep the deep CoT AND the tool. The COMPETENCE (how to drive the
  tool well) lives as a dsh skill / procedures.md entry, not a catalog tool.
  Every installed domain CLI is recorded in `configs/toolbox.md` (tool,
  version, purpose, skill pointer) — PATH contents are behavior-defining,
  so they belong in the genome. Recurring scenarios may earn a matrix row
  (e.g. math-proof worker → Minimal + Lean + lean skill). Note: a formal
  checker like Lean is a PERFECT verifier for its domain — prefer it over
  LLM judging wherever it applies.
Remaining open from the tools item: only the dshx gateway design (if
eternal-minimal wins the preset eval).

## 2c. Domain-onboarding pattern (decision 2026-08-27)

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

## 2d. FABLE MODULE (enabled 2026-09-03; design: FABLE-MODULE.md +
FABLE-MODULE-MAX.md; this section is the SPEC-level contract)

- SCOPE (Conrad, 2026-09-03): full phase 0–6 plan approved. Phases land one
  at a time via exp/fable-max, each flight-tested before the next:
  0 governance (this section) · 1 transport + `!escalate` · 2 judge
  calibration · 3 one Fable candidate in the verify pool (family
  decorrelation) · 4 rotation/handoff + dump-mode delegation · 5 nightly
  consolidation on Fable (still propose-only) · 6 Fable throne (main
  window). Standing practice: weekly architect session.
- TRANSPORT (Conrad, 2026-09-03): Claude Code CLI headless (`claude -p`)
  under the owner's Max subscription — flat rate; raw API key path kept as
  a fallback flag only. Model pin: `claude-fable-5-1` (hyphens — the
  dotted form is rejected), automatic fallback `claude-fable-5`; exact
  string recorded per call in the fable log.
- CAPS: rate caps, not dollar caps (subscription transport): `!escalate`
  10 calls/day default; calibration weekly; caps visible in `!status`.
  Per-question friction is deliberate — escalation never becomes a mode.
- ANTI-GOAL AMENDMENTS: the module docs' "not a verify arm" and "not the
  main window" anti-goals are OVERRIDDEN by the 2026-09-03 decision
  (phases 3 and 6). Still binding: NOT a generation tier or router target;
  NOT the ×5 verify generator (Vision-Exp invariant stands — Fable is ONE
  added candidate, not the pool); GLM stays the standing judge (Fable
  audits and tie-breaks); NOT autonomous beyond the sanctioned scheduled
  class (calibration, consolidation — both propose/report-only).
- LOAD-BEARING INVARIANT (survives all phases, incl. the throne): with
  Claude Code logged out and no API key, the full test suite and both
  surfaces stay green; every Fable feature reports "module disabled";
  the throne falls back to the §2b DeepSeek main window. A lapsed
  subscription costs the system its scalpel and its architect, never its
  function. Flight-test this at every phase promotion.
- Autonomy principle (§1) unchanged: no Fable call fires without Conrad
  except the scheduled propose-only passes.

## 3. Verifier layer (TOGGLE — on until turned off, never automatic)

- Normal mode: full unrestricted use of either stack; output returns directly.
  No verifier involved.
- `!verify on` (available from every access layer) switches to verified mode:
  each prompt, packaged with its full chat history, runs as N independent
  candidate generations on `deepseek-v4-flash-vision-exp` — the ONLY
  generator, regardless of which chat surface the prompt came from.
  N SETTINGS (decision 2026-09-04, returns-curve rationale): `!verify on`
  = N=8 (end of the steep coverage zone — the cheap wins); `!verify max`
  = N=16 (the band's ceiling under an imperfect LLM judge; gains past ~20
  are eaten by selection noise unless the checker is formal). The
  interior is featureless — two settings only. Candidates are judged in
  PARALLEL (one thread per candidate), so verify latency is ~independent
  of N; cost scales ~linearly in N (output tokens + judge calls; input
  rides cache-hit pricing).
  **GLM is ALWAYS the verifier.** It scores each candidate
  independently: fresh context per candidate, rubric criteria, score computed
  as the expectation over the logprob distribution of score tokens, repeated
  and averaged — never side-by-side ranking. *Z.ai adaptation (probed live,
  flight-tested 2026-08-28): the endpoint returns no logprobs and
  GLM-5.3-flash cannot disable thinking (only low/high/max effort), so the
  judge runs thinking-low, the 1–9 score is parsed from the answer text, and
  the expectation is approximated by averaging 3 samples at temperature 0.6.* The winner is appended to the
  originating chat as the reply; conversation continues normally from it
  (chat history is a shared document; the next model reads it regardless of
  who wrote which turn). Framework reference:
  github.com/llm-as-a-verifier/llm-as-a-verifier. `!verify off` returns to
  normal mode. Sole exception: Z.ai API unavailable → the generating model
  self-scores (fallback). Toggle lives on both chat surfaces: a dsh plugin,
  and a ZCode plugin (ZCode is MIT open-source with a plugin system —
  zcode.z.ai/en/docs/plugin). State persists across sessions until changed
  and must be visible in `status` and the web UI. Cost: ≈×5 generation +
  scoring while on; the 5 candidates share one prompt prefix, so DeepSeek
  cache-hit pricing keeps the marginal input cost low.
- Optional flag for high-stakes output: cross-check — the OTHER stack reviews
  the winner; disagreement is flagged to the human, never silently resolved.
- FABLE VERIFY ARM (§2d phase 3, built 2026-09-04, flag-gated OFF by
  default): with `FABLE_VERIFY_ARM=on` in .env, ONE Fable candidate joins
  the pool per verified prompt (mode tag `CROSS+FAM`; winner provenance
  shown). Rationale: the ×5 pool's failures are correlated within one model
  family; one cross-family candidate decorrelates them — the
  llm-as-a-verifier paper's own heterogeneous-pool result. Vision-Exp
  remains the ×N generator; the arm is ADD-ONLY (any failure or cap hit →
  plain ×5, never blocks verify), capped separately (FABLE_VERIFY_CAP,
  default 20/day, not the escalate budget), visible in `!status`.
- DEEPSEEK CO-JUDGE (built 2026-09-04, flag `VERIFY_COJUDGE`, default OFF):
  each candidate additionally scored by a non-thinking DeepSeek call as a
  TRUE expectation over digit-token logprobs (the llm-as-a-verifier
  method, which GLM cannot run — Z.ai exposes no logprobs); final score =
  mean of GLM and DeepSeek scores; mode tag gains `+CJ`. Add-only, never
  blocks. Known cost: same-family scoring for DeepSeek candidates, diluted
  by the GLM half. The judgment ledger keeps the PURE GLM score (plus
  ds_score) so calibration keeps auditing the standing judge. 1-9 scale
  retained deliberately: single-token digits keep the expectation clean
  (the paper's own footnote resorts to letters for its 1-20 scale).
  Deferred to eval (§8): finer granularity, criteria decomposition,
  ring-debiased pairwise + Bradley-Terry (would reverse this section's
  never-side-by-side rule — formal decision required).

## 3b. Session rotation (decision 2026-08-27)

- HARD LIMIT: 32k tokens of context per session — chosen well under the ~50k
  context-rot onset. Applies to both chat surfaces (dsh + ZCode, via plugin;
  dsh's native tokenMeter is the trigger source).
- Crossing 32k ARMS rotation; it FIRES at the next quiet boundary (turn end /
  tool loop settled), never mid-thought.
- On fire, the session writes a STRUCTURED handoff (JSON-leaning, not prose):
  decisions, current task state, key facts, open threads — plus any facts
  worth promoting to memory/facts.md. A fresh session opens seeded with the
  handoff; the old session is ARCHIVED (never deleted; the new session may
  read the archive on demand if the handoff missed something).
- Side effect by design: caps verify-mode cost — candidate generations carry
  chat history, so history is never >32k.
- Composes with compaction/tool-result pruning (those stretch a session's
  life; rotation is the backstop).

ROTATION PROTOCOL (rev 2, 2026-08-27) — for the MAIN window especially:
1. CONTINUOUS STATE, not big-bang summary: the session maintains a running
   state file (decisions, open threads incl. parked ideas, current focus)
   updated as it goes; rotation FINALIZES it. Never ask the 32k-degraded
   model to write the whole handoff from scratch. (§2d phase 4, built
   2026-09-04: when the Fable module is enabled, FABLE writes the holistic
   state rewrite and !retie merge reports — fresh long context, no
   degradation, author stamped in the rotation log; add-only fallback to
   the Vision-Exp path. Merge reports gain an explicit CONTRADICTIONS
   section per §3c rule 5.) Updates REGENERATE the
   state file holistically — never append/patch (append-style edits fragment
   memory; arXiv 2308.15022).
2. RAW-TAIL CARRYOVER: the new session receives the state file PLUS the last
   ~6–8k tokens of conversation VERBATIM. Recent/tacit context survives
   literally; only older context is distilled. New session starts ~8k.
3. DURABLE vs SESSION-LOCAL: durable knowledge lives in memory files updated
   in place and is NEVER re-distilled through handoffs (prevents
   photocopy-drift). Handoffs carry session-local state + pointers only.
   COMPRESSION PRINCIPLE (rate-distortion, arXiv 2605.10870): state files
   and handoffs compress toward DECISION-RELEVANCE, not descriptive
   fidelity — keep what changes future choices, drop what merely describes.
4. LINEAGE-KEYED WORKERS: the worker registry keys to the main-window
   lineage, not the session instance — in-flight workers report to whichever
   session currently holds the throne.
5. TIMING: rotation arms at cap but is DEFERRABLE by the user mid-thread,
   and EAGER during idle moments (rotate at ~26k when quiet rather than 32k
   mid-thought).
6. ROTATION LOG: an index entry per rotation (when, why, coverage summary,
   archive path) so archive retrieval is a lookup, not a dig.
7. ANNOUNCE: every rotation posts a one-line notice in chat (old→new session,
   what was carried). First post-rotation call pays cache-miss pricing once —
   accepted, negligible.
8. DUMP-MODE EXEMPTION (2026-08-27): rotation is default-on, with PER-SESSION
   exemptions only — never a global off switch. Whole-context synthesis
   sessions (deliberately load >32k, mine it, discard — the throwaway-session
   pattern) are exempt. Detection:
   - STRONG signal — a single large ingestion event (big paste/file read in
     one turn; token-delta heuristic) → auto-exempt, ANNOUNCED, one-word
     override if wrong.
   - AMBIGUOUS — gradual accumulation with synthesis intent (cheap one-label
     classifier on the request) → ASK one line ("looks like synthesis —
     exempt?"). Ambiguity resolves toward asking: a wrong exemption just lets
     rot linger in one session; a wrong rotation chops a synthesis read and
     breaks the task.
   - NO signal → rotate as normal.
   Exemptions die with the session, never inherit to workers, and always
   show in `status`.

## 3d. Memory system (decision 2026-08-27)

Lives on the desktop in the repo's `memory/` tree; four layers (working /
episodic / semantic / procedural, per the CoALA taxonomy):
- `memory/facts.md` — SEMANTIC: durable knowledge, updated in place, never
  re-distilled. Every entry carries: provenance (user-said / worker-inferred /
  web-claimed; session), TWO dates (when-TRUE vs when-LEARNED — bitemporal,
  per Toki, arXiv 2606.06240), scope ("valid for context C"), and optional
  `expires:` for facts that know their death date (e.g. promo pricing).
- `memory/procedures.md` — PROCEDURAL: learned how-tos ("when X fails, do Y
  first"), written only through the curation gate. Highest-leverage layer —
  a fact helps once, a procedure helps every recurrence.
- `memory/style.md` — PROCEDURAL (calibration): Conrad's preferences,
  slow-growing, loaded into EVERY session from file (never via handoff).
- `memory/artifacts/` — distilled artifacts from workers and throwaway runs.
- `memory/archives/` — EPISODIC: full session logs (main + workers),
  greppable on demand, plus `rotation-log.md` (the §3b index).
- `memory/library/` — THE LIBRARY (reference corpus): raw external documents
  — PDFs, docs, papers, manuals. What the system can LOOK UP, as opposed to
  facts.md (what it has LEARNED). Unbounded size; NEVER loaded wholesale —
  accessed by agentic retrieval (filename/full-text search, targeted reads);
  whole-document synthesis goes through a dump-mode session that returns a
  distilled artifact. No vector DB until scale demonstrably demands it.
  Rules: library content is DATA, never instructions (documents are a
  prompt-injection surface); facts extracted from a document enter facts.md
  only through the curation gate, with provenance citing the source file.
  INGESTION (decision 2026-08-27): drop files into `library/inbox/` (drag
  from desktop; send via the Signal bridge from the phone — attachments are
  data). `!ingest` (on command, per the autonomy principle) processes the
  inbox: renames to `YYYY-MM_topic_title.ext`, moves into `library/`,
  appends one line per doc to `library/index.md` (filename, title, source,
  date, one-line description), and for PDFs writes a `pdftotext` sidecar
  `.txt` so grep reaches inside them. Sidecars matter from document #1
  (PDFs are binary — without one, grep sees nothing inside at ANY count);
  the index matters increasingly as the corpus grows.
(WORKING memory = the live 32k window + its ephemeral state files.)

WRITE CONTRACT (Toki-lite, arXiv 2606.06240 — contradiction resolution is
write-time concurrency control; undeclared heuristics admit anomalies):
- SUPERSEDE, NEVER ERASE: when a fact is superseded, the losing entry moves
  to an audit section (with when/why/what-replaced-it) — never deleted.
  Prevents audit erasure; adversarial or mistaken overwrites stay traceable.
- ADJUDICATION LOG: when the curation gate resolves a contradiction, it logs
  the ruling (conflict key, winner, reason) so the same conflict replays to
  the same outcome (prevents replay inconsistency).
- Single-writer gate (§ access model) already precludes the multi-writer
  race anomalies — keep it that way.
- ADVERSARIAL-BY-DEFAULT GATE (2026 memory-poisoning literature: attacks
  succeed at <0.1% poison rates; content screening alone has hard limits —
  arXiv 2606.04329, 2608.21230, 2607.27080): every fact proposal originating
  from workers, web content, or library documents is treated as potentially
  adversarial at the curation gate. The write path is the battleground; the
  gate is the defense. Audit rows (above) double as the repair mechanism —
  a discovered poisoning is traceable and reversible, never silently absorbed.

CONSOLIDATION PASS (SCHEDULED — the autonomy principle's one exception,
because it only proposes and cannot act): runs nightly during off-peak
DeepSeek pricing; `!consolidate` also triggers it manually. (§2d phase 5,
built 2026-09-04: Fable writes the pass when the module is enabled —
strongest judgment on the adversarial write path, long-context pattern
mining; author stamped in the proposals file; add-only Vision-Exp
fallback; propose-only unchanged.) It reads recent
archives and proposes to the curation gate: facts worth
promoting, cross-session patterns worth becoming procedures, entries that look
stale or superseded, and long-untouched entries flagged for decay review.
It PROPOSES only — the gate decides. This is the only mechanism that can see
patterns ACROSS sessions (no single session can). Prior art: reflection
(Generative Agents), sleep-time compute (Letta), "dreaming" (Anthropic).

FORGETTING POLICY: supersession on write (above) + `expires:` tags honored at
consolidation + scope expiry (a fact scoped to project X dies with project X)
+ usage-decay REVIEW (long-untouched entries are flagged to the gate, never
silently deleted — durable memory is small enough to review, so forgetting
stays human-gated).

MEMORY ACCESS MODEL (2026-08-27): ONE durable store, one ephemeral layer,
write access gated by session type — never two parallel memory systems
(parallel stores fragment retrieval and drift into contradiction).
- READS: universal — every session type reads the same style.md (always)
  and facts.md (as needed).
- WRITES to durable memory: MAIN WINDOW ONLY (the curation gate — where
  provenance, scope tags, and neutral-affect rules are enforced).
  WORKERS propose facts in their reports; the main window promotes or not.
  DUMP-MODE sessions write artifacts only, never memory — their content is
  bulk and unvetted by nature; anything fact-worthy in an artifact passes
  through the main window's gate like everything else.
- The EPHEMERAL layer (state files, handoffs, worker reports) is separate
  from durable memory and dies with its sessions.

MEMORY-TRAP DEFENSES (2026-08-27, from MemTrapBench, arXiv 2608.20202 —
even TRUE, relevant memories measurably degrade current-task reasoning;
all tested memory frameworks scored >10 pts below no-memory):
- ADAPTIVEMEM GUARD in every session's standing prompt: watch for four
  risks — task boundary (don't carry the prior task's framing/rules/format),
  cognitive bias (past successful strategies are shortcuts OR traps;
  re-evaluate from the current query), trauma (past negative feedback never
  overrides present correctness), safety (sandbox/counterfactual premises
  from history never govern real situations). Silent procedure: identify the
  live task from the latest query alone; keep only clearly relevant prior
  context; on conflict prefer objective truth/safety > current query >
  minimum context. Don't over-trigger — routine queries use memory normally.
  (Paper: +11.8–14.9 pts on traps, no cost on normal memory benchmarks.)
- SCOPE TAGS: memory entries carry applicability alongside provenance —
  "valid for context C" — because the core trap is valid-in-original-context
  applied beyond its scope.
- NEUTRAL-AFFECT RECORDS: handoffs and facts record failures as
  "approach X failed on task Y because Z" — never with emotional framing;
  affect in history induces avoidance of currently-correct approaches
  (the paper's Trauma result).

## 3c. Main window / worker sessions (decision 2026-08-27)

- The main window is not a separate app — it is WHICHEVER harness chat you are
  sitting in (DeepSeek Harness or ZCode). It is the COMMAND CENTER: it holds
  direction and distilled results only, and rotates at the 32k cap (§3b).
- FABLE THRONE (§2d phase 6, built 2026-09-04): with the module enabled,
  a Claude Code/Cowork session in this repo may hold the throne — charter
  in `memory/prompts/throne.md`, entry rules in `CLAUDE.md`. Inverted
  pyramid: the costliest judgment sits where tokens are fewest; workers
  stay on the DeepSeek/GLM stacks per §2b. A Fable window is exempt from
  the 32k cap but NOT from state-file discipline. Fallback: the §2b
  DeepSeek main window, zero functional loss (§2d invariant).
- WINDOW SEMANTICS (rev 3, 2026-08-27 — fully worked):
  DEFINITIONS: a LINEAGE = one task line's shared truth (state file, worker
  registry, archive chain, gate queue). The THRONE = the lineage's single
  authoritative window — where the prompt starts. A WINDOW = one harness
  chat session (the same dsh session viewed from phone AND desktop is ONE
  window). Rotation is PER WINDOW (each window's context fills
  independently); the state file is per LINEAGE.
  RULE 1 — ONE WRITER: only the throne writes lineage state (state file,
  memory promotions). Same single-writer principle as the curation gate.
  RULE 2 — SATELLITES ARE HUMAN-DRIVEN WORKERS: every tied non-throne
  window behaves under the existing worker contract — it reads lineage
  state, spawns workers into the shared registry (tagged with its window
  id; reports deliver to the spawning window, with a copy to the lineage
  event log so the throne stays complete), and on rotation or close it
  distills its session into a report-shaped handoff delivered to the
  throne. No new machinery: everything that isn't the throne is a worker —
  automated or human-driven.
  RULE 3 — THRONE MIGRATION: `!throne` in any tied window moves the crown
  there (atomic pointer flip, announced in both windows; old throne becomes
  a satellite). Closing the throne without migrating leaves the lineage
  DORMANT (state intact); any window may resume it or claim the throne.
  Simultaneous claims: last write wins, both announced.
  RULE 4 — UNTIE: `!untie` makes the current window a NEW lineage — fresh
  state file seeded from its own context, fresh registry. Workers it
  spawned FOLLOW it (they were its sub-tasks); the old lineage logs their
  departure.
  RULE 5 — RETIE (merge, fully defined): `!retie <lineage>` merges lineage
  B into A. B's state file is regenerated as a decision-relevant handoff
  and delivered to A's throne AS A WORKER-STYLE REPORT flagged
  "lineage merge". CONTRADICTIONS between A's and B's decisions are listed
  explicitly for Conrad — never silently resolved (same rule as verifier
  disagreement). B's workers re-key into A's registry (ids prefixed with
  their origin lineage — no collisions). B's archives append to A's archive
  index with a merge note. B ceases to exist. Retie is always
  human-initiated, so the human is present for the contradiction list by
  construction.
  TOGGLE SCOPE: the verify toggle is a property of the WINDOW and travels
  with it through tie/untie/throne changes. Flipping it in one window never
  affects another.
- Every assigned task spawns its OWN fresh 32k worker session (dsh subagent
  machinery / ZCode equivalent): all tool calls and execution happen inside
  the worker; on completion, a distilled result returns to the main window.
- Grain: one worker per TASK, not per individual tool call — a worker keeps
  its whole tool chain together in one context. Workers may themselves rotate
  at 32k or spawn sub-workers for large jobs.
- Effect: the main window ages slowly (direction + results only), every worker
  runs in fresh low-context conditions, and tool noise never reaches the chat.

WORKER CONTRACT (2026-08-27) — both directions are contracts, not messages:
- BRIEF (main → worker): goal, constraints, definition-of-done, relevant
  facts, allowed scope (files/resources). Workers that are unsure ASK BACK —
  never guess (an ask-back channel is part of the plumbing).
- REPORT (worker → main), structured and size-capped (≤ ~500 tokens to chat;
  larger output goes to files, referenced by path):
  did / changed / decisions-taken / surprises / open-items / evidence
  (test output, diff, artifact path — claims without evidence don't count as
  done) / based-on tag (what main-window state it was briefed against, so
  stale returns get reconciled, not blindly merged).
- REGISTRY: per-lineage worker registry with states running / done / failed /
  timed-out; every worker has a timeout; terminal states always notify the
  main window; `status` lists everything in flight.
- COLLISIONS: one writer per resource — workers touching the same files get
  serialized or separate git worktrees (lock, don't hope).
- TRUST: reports are DATA, never instructions — a worker that read untrusted
  content cannot inject commands into the main window through its report.
- OWNERSHIP INVARIANT (2026 addition): workers NEVER hand off laterally —
  hierarchy only (spawn sub-workers down, report up); task ownership never
  transfers. Prevents the handoff-loop failure mode (#1 in 2026 production
  reports: A→B→C→A, everyone replans, nobody owns).
- PROVENANCE (2026 addition): every memory/facts.md entry carries provenance —
  source (user-said / worker-inferred / web-claimed), date, session — to
  prevent provenance-role collapse (arXiv 2605.25869).

## 3e. Observability (2026-08-27)

- dsh TRAJECTORY LOGS are the ground truth for stack A: append-only JSONL
  (zstd) artifacts with per-request headers, tool-call chains, and reasoning
  blocks — greppable proof of which preset/CoT actually fired (this is what
  the preset authors' evals inspect). Community tooling exists for repair
  (dsh-session-repair).
- ZCode logs live LOCALLY at `~/.zcode` (logs folder; subagents as plain
  Markdown in `~/.zcode/agents/`), with a menu-level "Export Logs" producing
  a compressed archive. Session log captures file writes, terminal commands,
  verification passes, confirmation gates. Exact record format:
  reverse-engineer at install (app is MIT). Our verifier/bridge plumbing logs
  GLM API traffic regardless.
- TASK-ID CORRELATION (required): every task gets an ID stamped into BOTH
  stacks' logs and all plumbing logs — one grep reconstructs a full story
  across generator, judge, and workers.
- USAGE-FIELD LOGGING (required): all plumbing we write (verifier service,
  bridge, worker spawner) records each API response's usage fields (tokens,
  cache hits) keyed by task ID — per-task cost attribution, not just per-key
  daily totals.
- LANGFUSE = OBSERVABILITY HUB (decision 2026-08-27): self-hosted on the
  desktop (MIT core; v3 = six containers, ClickHouse + Postgres; Docker
  Compose path). All plumbing we write uses the `langfuse.openai` drop-in
  wrapper (both providers are OpenAI-compatible) → automatic per-call
  tracing, tokens, cost. The Langfuse TRACE ID serves as the task-ID above,
  stamped into harness logs to link all three record systems. Its datasets +
  LLM-as-judge scoring host the eval suite (§7). Scope limit: sees only
  instrumented traffic — harness-internal calls stay in dsh/ZCode logs
  (future project: a dsh→Langfuse OTel exporter plugin). Passive infra, so
  no autonomy-principle conflict.
- Plus: per-stack spend tracking (Langfuse per-trace + provider dashboards
  as cross-check); the `status` surface (verify toggle state, rotation
  exemptions, workers in flight); weekly transcript reads (the standing
  early-warning ritual).

## 3e2. Runaway caps (decision 2026-08-27)

- STEP CAPS per loop: workers default 25 steps; coding goals 64. Hitting a
  cap = stop + report, never silent continuation.
- PROVENANCE OF THESE NUMBERS (honest): none are research-derived. 25 =
  long-standing practitioner heuristic ("cap at 10–25"); 64 = one community
  preset's default (dsh tool-ralph maxRounds); dollar figures = judgment
  scaled to this system's costs. They are starting TRIPWIRES only — the
  load-bearing mechanism is the tuning method below, which replaces them
  with numbers measured from THIS system's own behavior.
- TOKEN/SPEND CEILINGS per task: alert at ~$1, hard stop at ~$5 (verified
  tasks: ×5 applies — ceilings are per TASK, not per candidate).
- PROVIDER-SIDE monthly spend caps on both API keys (start ~$30 each).
- TUNING METHOD: run two weeks, read Langfuse per-task distributions, set
  caps at ~2× the p95 of each task class, revisit quarterly. Caps exist to
  catch runaways, not to squeeze normal work.

## 3f. Workspace & permissions (decision 2026-08-27)

- WORKSPACE ROOT: `~/Desktop`. Agents have access to everything under it;
  the agent-system repo lives inside it. Outside the root, access is
  read-nothing by default (see also the privacy gap, §8).
- PERMISSION MODES, Claude-Code-style, set PER SESSION:
  - MANUAL (default): every file write, shell command, and irreversible
    action is confirmed by Conrad before execution. ZCode's confirmation
    gates and dsh's approval stack both map to this mode.
  - AUTO: the session acts without per-action confirmation, within its scope
    (workspace root, its git worktree if a worker). Destructive/irreversible
    actions (delete, push, send, purchase) still require confirmation even
    in auto.
  - Mode is visible in `status`; workers inherit the mode of their brief
    unless the brief narrows it.

## 3g. Command registry (all surfaces unless noted)

- `!verify on` / `!verify max` / `!verify off` — verifier toggle (§3);
  on = 8 candidates, max = 16 (high-stakes; ~2× cost, same latency).
- `!think <question>` — deep-think delegation to a Minimal-preset subagent.
- `!do on` / `!do off` — opposite-CoT toggle (per window, like `!verify`).
  There are exactly two CoT conditions (§2b): `!think` = tool-free deep
  chain ("We/Let's"); `!do` = Standard — the WIDE tool catalog conditions
  the stepwise "Let me" chain. While on, every plain prompt is answered by
  a Standard subagent with the full 16-tool catalog visible and usable
  (10-step cap). `!verify` outranks `!do` when both are on.
- `!do <task>` — one-shot: fires the task into a detached Standard worker
  (25-step cap, evidence-backed report filed through lineage). Exact
  `on`/`off` matches the toggle first; anything else is a task.
- `!consolidate` — manual trigger of the consolidation pass (§3d).
- `!status` — verify state, rotation exemptions + session token counts,
  workers in flight, permission mode, active build/branch. (Chat surfaces
  use the `!` prefix so the bare word stays usable in conversation; the
  Signal WATCHDOG keeps plain `status` — its channel is commands-only.)
- `!rotate` — manual rotation now (§3b): auto-discovers the newest dsh
  session file, holistic state rewrite + raw-tail seed + archive, token
  counter reset.
- Rotation prompts — reply to defer, or confirm/deny a dump-mode exemption.
- `!throne` — move the lineage's crown to this window (§3c rule 3).
- `!untie` / `!retie <lineage>` — detach this window into its own lineage /
  merge a lineage back into this one (§3c rules 4–5).
- `!ingest` — process `library/inbox/` (§3d).
- `!calibrate` — manual trigger of the weekly judge-calibration pass
  (§2d phase 2): Fable blind-rescores recent verify judgments from the
  judgment ledger; report to memory/calibration/, line in `!status`.
  Report-only. Scheduled twin: calibrate.timer (Sun 09:00).
- `!escalate <question>` — one Mythos-class deep answer from the Fable
  module (§2d); owner-initiated only; prints model + latency; rate-capped
  10/day; politely dead when the module is disabled. STATUS: built and
  FLIGHT-TESTED 2026-09-03 (plumbing/escalate.py + fable.py; live
  claude-fable-5-1 answers confirmed on the host, owner-verified on the
  surfaces).
- Signal WATCHDOG only (standalone service, hardcoded): `restart dsh` ·
  `restart zcode` · `reboot` · `status` · `vpn up`.
- ZCode surface (BUILT 2026-08-28): the same registry runs on ZCode via
  `plugins/zcode-agent-system` — a UserPromptSubmit hook
  (zcode.z.ai/en/docs/hooks) since ZCode hooks cannot rewrite prompts:
  `!commands` block the model call and surface output as the block reason
  (zero model tokens); verify/do modes inject the pipeline's answer as
  additionalContext with a relay-verbatim instruction (GLM is the
  messenger). Window id `zcode-<session[:12]>` shares runtime state with
  dsh windows. Install: Settings→Plugins→Create→Add marketplace→
  `plugins/zcode-marketplace` dir. v1 verify is single-turn on ZCode
  (transcript parse: later).
- Rule: this registry is the single source of truth for commands; new
  commands are added HERE first.

## 4. Network / remote access (three layers, narrow → full)

| # | Channel | Transport | Gives | Depends on |
|---|---|---|---|---|
| 1 | Signal | Signal E2EE (signal-cli, SECOND phone number, daemon/JSON-RPC) | coarse commands + recovery | nothing else running |
| 2 | Tailnet | WireGuard via self-hosted Headscale (github.com/juanfont/headscale) | dsh web UI :3080, SSH/tmux | headscale reachable |
| 3 | Tailnet | Sunshine host + Moonlight client (github.com/LizardByte/Sunshine) | 1:1 screen, full control | VPN + machine up |

- Layer 1 is TWO processes: (a) standalone watchdog service, independent of
  dsh, hardcoded commands only: `restart dsh` / `restart zcode` / `reboot` /
  `status` / `vpn up`; (b) a dsh channel plugin (to build: `dsh-signal-channel`,
  modeled on github.com/hi-wenw/dsh-telegram-channel) for richer session
  commands. Build order: watchdog first.
- Headscale server on the desktop itself (decision 2026-08-27: home-hosted;
  domain YOUR-DOMAIN + cron IP updater). AS DEPLOYED 2026-08-28 (HTTPS —
  iOS refuses plain-http control servers): server_url
  https://YOUR-DOMAIN, listen_addr LAN-IP:443 (not 0.0.0.0 — tailscaled
  holds 443 on tailnet IPs for the owner's Vaultwarden serve), Let's Encrypt
  via HTTP-01, embedded DERP enabled (needs TLS; relay fallback for the
  phone). Router forwards TCP 80 (ACME) + TCP 443 + UDP 3478; the original
  TCP 8080 forward is retired — close it. /etc/hosts maps YOUR-DOMAIN →
  LAN IP (hairpin-NAT workaround; set a static hostname or the machine
  adopts the DuckDNS label as its transient name). Desktop rejoined via
  `tailscale up --login-server https://YOUR-DOMAIN`; iOS joins via the
  app's custom-server flow + `headscale auth register --user conrad
  --auth-id <hskey-authreq-...>` (v0.29 syntax; preauthkeys still want the
  numeric user ID). headscale's unit is Restart=always (port-drift guard);
  close the router forwards the day headscale retires.
  KEPT AS IDEA (declined for cost): headscale on a ~€3/mo VPS = zero home
  ports open, TLS trivial — the cleaner posture if exposure ever bothers
  Conrad. Clients: official Tailscale apps pointed at the custom server.
- Sunshine bound/firewalled to the tailnet interface only
  (TCP 47984-47990, UDP 47998-48010). dsh web UI likewise never exposed
  beyond localhost/tailnet.
- dsh phone access AS DEPLOYED (final): dsh itself binds 127.0.0.1 only (it
  refuses 0.0.0.0 by design — "would expose remote code execution"; the
  owner's instinct, vindicated). Relay = Caddy (user service
  `dsh-tailnet-relay`; earlier socat retired), binds 100.64.0.1:3080 with a
  REAL Let's Encrypt cert for `dsh.YOUR-DOMAIN` (acme.sh + DuckDNS
  DNS-01, auto-renews via cron; reloadcmd rebuilds/restarts the relay), and
  proxies to 127.0.0.1:3080 rewriting `Host: localhost:3080` + stripping
  `Origin`. Why: dsh's CONFIGURATION plane (host.pickDirectory etc.) is
  loopback-same-origin by design — `--trusted-host` covers RPC only — so
  the relay grants tailnet devices localhost-grade access (acceptable:
  owner-only tailnet; remember before enrolling less-trusted devices).
  headscale `dns.extra_records` serves the name as 100.64.0.1 tailnet-wide.
  Device URL: https://dsh.YOUR-DOMAIN:3080 (the NAME — cert matches).
  TLS is mandatory (plain-http origins lack crypto.randomUUID → app
  breaks); iOS Safari silently falls back to http on untrusted certs
  (self-signed dead end — real cert required). host.pickDirectory opens a
  NATIVE dialog on the host screen: new workspaces are created at the desk
  or via Moonlight; remote use resumes existing sessions (session list),
  whose workspaces persist. firewalld: tailscale0 in the trusted zone;
  rich rule rejects 3080 from 192.168.0.0/16.
- Notifications may deep-link into layer-2 URLs. Nothing tunnels THROUGH
  Signal; it is messaging only.

## 5. Security invariants (non-negotiable)

1. Chat-channel senders allowlisted to owner's Signal number; all else ignored+logged.
2. Chat channels carry a coarse command set only — no raw shell passthrough;
   message content treated as untrusted (prompt-injection surface).
3. Destructive/irreversible actions require an explicit second confirmation.
4. Secrets never transit chat channels.
5. Disk: LUKS2 full-disk encryption. Reboots wait at the passphrase prompt —
   accepted; NO auto-unlock (no TPM enrollment).
6. Transit: everything rides WireGuard except Signal (E2EE on its own).
7. Watchdog/bridge processes run unprivileged (no sudo).

## 6. Host & lifecycle

- HOST HARDWARE (confirmed 2026-08-27): Fedora Linux, AMD Ryzen (Matisse),
  32 GB RAM, NVMe SSD, NVIDIA RTX 2080 Ti. Package manager = dnf (setup
  scripts adapted). Sunshine encoder = NVENC (H.264/HEVC; requires the
  proprietary driver — RPM Fusion akmod-nvidia). Wayland+NVIDIA KMS capture
  is the finicky corner; X11 session is the fallback. 11 GB VRAM cannot
  self-host the V4/GLM flagship MoEs — self-hosting stays future-only.
- Single desktop host (Wayland session), sleep/suspend masked, runs 24/7.
- dsh runs as a user systemd service inside tmux session `agents`
  (see `setup/03-agent-host.sh`), linger enabled.
- Sunshine on Wayland needs KMS capture: `setcap cap_sys_admin+p` on the
  binary + input group/uinput perms. Hardware encoder required (VAAPI/NVENC).
- RESOURCE BUDGET (estimates; verify on the actual machine):
  Langfuse stack (ClickHouse+Postgres+Redis+MinIO+web+worker) ~2.5–4 GB ·
  dsh ~0.3–0.8 GB · ZCode ~0.5–1.5 GB · signal-cli (JVM) ~0.2–0.4 GB ·
  Sunshine ~0.1–0.3 GB (+GPU encoder) · headscale/tailscale ~0.1 GB ·
  plumbing ~0.1 GB → system total ≈ 4–7 GB on top of OS + desktop (~2–3 GB).
  HOST HAS 32 GB RAM (confirmed 2026-08-27) — everything runs concurrently
  with lots of headroom; no trimming needed. Langfuse runs 24/7 alongside
  the system (passive infra — it can only record what's up when work
  happens; traces from downtime are lost).
- BACKUPS (two tiers, both required):
  - TIER 1 — LOCAL HISTORY: snapper snapshots (already in place). Protects
    against deletion/bad upgrades; VERIFY it covers /home (distros commonly
    snapshot root only) and therefore the repo + memory tree. Snapshots on
    the same disk are NOT backups.
  - TIER 2 — OFF-MACHINE: PARTIALLY REVERSED (Conrad, 2026-08-31). Trigger:
    the NVMe reported 11 Media and Data Integrity Errors and four separate
    data-corruption events hit in one day (docker layer, .pyc, ClickHouse
    binary checksum, rpmdb) — the accepted risk stopped being hypothetical.
    Genome now mirrors to a PRIVATE GitHub remote: `git push backup main`
    to github.com/YOUR-GITHUB-USER/agent-system (remote name `backup`; classic PAT,
    repo scope only, stored in .git/config — rotate per §6b keys policy).
    Push after every meaningful commit. STILL single-disk by choice: runtime
    state, archives, library corpus, Langfuse DB (body, not genome).
    Hardware verdict, corrected 2026-09-14 (Conrad): the drive is fine;
    the RAM is what needs replacing.

## 6b. Maintenance notices (recurring duties — shown top-right of the guide)

- `signal-cli`: update MONTHLY — Signal's servers enforce client currency;
  a stale signal-cli eventually stops working, and it is the recovery
  channel (you'd discover the rot exactly when you need it remotely).
- NVIDIA driver / kernel: after any Fedora kernel update, verify the akmod
  rebuilt and Sunshine capture still works BEFORE leaving the house.
- Langfuse containers: update on release, casually.
- Relay cert: real Let's Encrypt cert (dsh.YOUR-DOMAIN) — acme.sh's
  cron renews it and its reloadcmd rebuilds/restarts `dsh-tailnet-relay`
  automatically; spot-check after ~Oct 27 renewals. Headscale's own LE cert
  renews itself too (keep router TCP 80 forwarded for both).
- dsh / ZCode: upgrades ONLY via the exp branch (re-review preset snapshots).
- KEYS & IDENTITY: rotate API keys if ever suspected leaked (one .env edit);
  expire old headscale preauth keys and Sunshine pairings quarterly; keep
  the Signal bridge NUMBER alive (VoIP/eSIM numbers get recycled if unused
  or unpaid — set a reminder to keep it active).

## 7. Two builds

- `main` = stable: everything pinnable pinned; changes land normally via
  promotion from `exp/*` after evals (regression suite stays ~100%, capability
  suite improves). Rollback = `git revert`.
- `exp/*` = experiments: one branch per experiment; allowed to break.
- Exception on record: GLM/ZCode entered stable directly by owner decision on
  2026-08-27, eval gate skipped; first eval run baselines both engines.
- Evals (to build, `evals/`): 20–50 tasks harvested from real failures;
  outcome-graded, not transcript-graded; pass^k for stable, pass@k for
  capability; weekly transcript reads.
- PLUMBING QA (2026-08-27; built 2026-08-31): the eval suite tests MODELS;
  our own code — verifier service, rotation logic, worker registry, curation
  gate, bridge, watchdog — gets zero-dependency unit tests (the preset repos'
  style), built at `plumbing/tests/run_tests.py` and run as the regression
  gate before any promotion. The components that enforce the spec's
  guarantees must themselves be tested.
- REPO = GENOME, RUNTIME STATE = BODY (boundary rule, 2026-08-27): anything
  that DEFINES BEHAVIOR must live in the repo and be branch-versioned —
  configs, prompts, presets, plugins, memory rules, eval task DEFINITIONS
  (synced into Langfuse; Langfuse holds results, which are rebuildable
  telemetry, never source of truth), and ZCode's exportable settings/agents
  mirrored in. Anything that RECORDS HISTORY (traces, archives/, library/)
  lives outside git — gitignored, with its own backup story. NOTHING
  behavioral may exist only inside an app's internal storage. This preserves
  the original property the two-build design depends on: branches version
  everything that makes the system act the way it acts.

## 8. Open decisions (deliberately undecided)

- Role split between stack A and stack B (which tasks go where). Decided so
  far: GLM is always the verifier-layer judge; everything else TBD.
- Agentic preset default, final call: `anchored-standard` (current default)
  vs `eternal-minimal` (session-long Minimal surface + dshx gateway, zero
  cache cost — github.com/Greenhand-monster/dsh-deliberation-presets).
  Both are candidates; the eval matrix decides (vs plain Minimal and
  Standard as baselines).
- Eval task set (accumulates from real use).
- Math capability module — planned first instance of the domain-onboarding
  pattern (§2c), source: the "Frontier stack for math and physics" guide.
  Adaptations on record: prover = Goedel-V2-8B 4-bit (11 GB VRAM;
  gpu-memory-utilization ≤0.85, GPU shared with desktop + Sunshine);
  frontier-LLM layer = GLM/Vision-Exp + verify machinery (lower solve rate
  expected, never false claims — the kernel is a perfect verifier);
  Part I baseline only, Part II extensions later; Fedora-native (skip WSL).
  Not yet installed.
- Quant capability module — SECOND planned domain instance (§2c), source:
  the "Stock market tools frontier" folder (frontier_quant_stack v6.0 +
  three-market v7.6 + stack_operations_manual v1.2 — finished spec, zero
  code; prices verified Aug 5 2026, regime-watch calendar pre-loaded).
  Three wrinkles on record: (1) verifier tier is STATISTICAL, not formal —
  Deflated Sharpe + CPCV + the append-only trial registry (overfitting is
  the adversary; the registry is this domain's planted-false suite); tier
  rank: statistical gates > fill-log reconciliation > LLM judgment.
  (2) The RISK LAYER IS PLUMBING, never agents — pod rules, kill switches,
  stage-gates are deterministic code in the workspace, outside any LLM's
  reach (Millennium principle: nobody overrides the risk desk). Agents do
  research only. (3) LIVE TRADING requires, before it ever starts: an
  autonomy-principle amendment sanctioning protective automation
  (kill switches / auto-flatten fire without Conrad — automation that
  reduces consequence), and manual-mode confirmation on all orders until
  stage-gates say otherwise. Research tier ($0) touches none of this.
  Ops-manual [EDIT] fields = Conrad's pre-commitments, set once while calm.
  Separate workspace repo (heavy on all three §2c criteria), rev-pinned.
  Not yet installed.
- Security Work capability module — THIRD planned domain instance (§2c).
  Label registered; source material and contents TBD.
- Tools & presets: CLOSED by the preset-assignment matrix + tool-surface
  policy (§2b). Remaining: only the dshx gateway design, if eternal-minimal
  wins the preset eval.

CLOSED BY DECISION (2026-08-27, on record):
- Data-egress/privacy policy: none, by choice — all content may flow to the
  DeepSeek and Z.ai APIs. (2026-09-03: extended to Anthropic via the Fable
  module transport.)
- Frontier escalation tier: REOPENED and resolved 2026-09-03 — closed for
  generation (verifier verdict stands), opened as the Fable module's
  judgment/audit/command roles (§2d).
- Degraded-mode playbook: none — if a provider is down, that stack simply
  isn't used until it returns (verifier's self-score fallback stays).
  Revisit only if self-hosting (both models are open-weights).
- Off-machine backups: declined — see §6 tier 2.

## 9. Cost posture

Two cheap APIs only. DeepSeek: off-peak (UTC Mon–Fri 01:00–04:00, 06:00–10:00
= peak; everything else 50% off) + cache-hit pricing. GLM promo pricing ends
Sep 9, 2026 — re-evaluate costs then. Watch: best-of-5 multiplies spend ×5 per
verified task.

---

\* **OS portability:** the reference scripts in `setup/` target Debian/Ubuntu
Linux, but nothing in this design is OS-bound. Every component is
cross-platform: headscale + Tailscale clients (Linux/macOS/Windows/iOS/
Android), Node + dsh (any OS), ZCode (desktop app, Win/macOS/Linux),
signal-cli (JVM, any OS), Sunshine/Moonlight (Win/macOS/Linux hosts, all
mobile clients), git, tmux (or any process supervisor). For non-Linux hosts
substitute: systemd units → launchd (macOS) / Task Scheduler or NSSM
(Windows); LUKS2 → FileVault (macOS) / BitLocker (Windows); Wayland capture
notes → native capture (other OSes need no setcap step). An AI recreating
this system on another OS should preserve §2–§8 exactly and re-derive §6
mechanics for the target platform.
