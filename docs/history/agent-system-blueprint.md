# Conrad's Agent System Blueprint

**A complete personal AI system: one stable build for daily use, one experimental build for testing new research.**
Written August 24, 2026 · Revised August 27, 2026 (v2) · Models: Claude Fable 5, Claude Opus 5, DeepSeek V4-Pro, V4-Flash, V4-Flash-Vision-Exp

**v2 revision log** — decisions made after v1, now reflected throughout: harness is **DeepSeek Harness (`dsh`)**, not a Claude-Agent-SDK-centric stack; LiteLLM demoted from required to optional; Claude runs as a **Claude Code subagent billed to the Max subscription quota**, not the API (the "Agent SDK credit" was announced then un-announced by Anthropic — current reality is regular sub quota); **verification scaling** (best-of-n Flash + LLM-as-a-Verifier) added as a first-class routing strategy; architecture is **always-on cheap, on-demand smart**; remote access layer added (self-hosted Headscale, phone via Tailscale apps, dsh's built-in web UI); host is the desktop; contingency defined for subscription cancellation. Implementation lives in the `agent-system/` repo next to this file.

**v3.2 deployment log (Aug 28)** — the infrastructure went LIVE; as-built deltas, canonical in `agent-system/SPEC.md`: **headscale now speaks HTTPS** at `https://YOUR-DOMAIN` (listen LAN-IP:443, Let's Encrypt via HTTP-01, embedded DERP on; router forwards TCP 80+443 and UDP 3478 — the original TCP 8080 forward is retired; `/etc/hosts` maps the domain to the LAN IP as the hairpin-NAT workaround). iOS refuses plain-http control servers, so HTTPS was the price of the phone — which is now joined via the Tailscale app's custom-server flow plus `headscale auth register --user conrad --auth-id <hskey-authreq-…>`. **dsh binds 127.0.0.1 only** (by design); remote access is a **Caddy relay** on 100.64.0.1:3080 carrying a real Let's Encrypt cert for `dsh.YOUR-DOMAIN` (acme.sh DuckDNS DNS-01, auto-renewing), rewriting `Host` to localhost:3080 and stripping `Origin` — dsh's configuration plane is loopback-same-origin (`--trusted-host` covers RPC only), and headscale's `dns.extra_records` serves the name tailnet-wide; device URL: `https://dsh.YOUR-DOMAIN:3080`. The workspace picker is a native dialog on the host screen, so remote use = resume existing sessions. **The verifier layer is live**, cross-check mode confirmed, with the Z.ai adaptation on record: the endpoint returns no logprobs and GLM can't disable thinking, so the judge runs thinking-low, the score is parsed from the answer text, and the expectation is approximated by a 3-sample average at temperature 0.6; generator calls use `max_tokens` 16384 everywhere (thinking counts against the cap). **`!do` is live in both forms** — a per-window opposite-CoT toggle (`!do on|off`: wide 16-tool catalog, "Let me" chain, `!verify` outranks it) and a one-shot `!do <task>` detached worker — and **`!rotate` is real** (auto-discovers the newest session file). **Langfuse is up**: the six-container stack lives at localhost:3000 (its metrics moved off 9090/9091 to 9095; MinIO holds 9090/9091). **The ZCode surface plugin is built** (`plugins/zcode-agent-system`, a UserPromptSubmit hook: ZCode's UI swallows block reasons, so `!commands` and verify/do modes all deliver by injecting the output as relay context — GLM repeats it verbatim, one small model call per command).

**v3.1 revision log (Aug 27, evening)** — remote access finalized as **three layers, narrow→full**: (1) **Signal** — a standalone watchdog service (independent of dsh, hardcoded recovery commands: restart/reboot/status, works even when the harness is down) plus a `dsh-signal-channel` plugin to build (no Signal support exists in dsh's channel ecosystem — no bot API — so it's DIY on signal-cli, modeled on the community Telegram channel plugin); bridge notifications deep-link into the tailnet UI. (2) **dsh web UI** over the tailnet — structured harness state. (3) **Remote desktop, 1:1 screen: Sunshine + Moonlight** over the tailnet (Wayland: KMS capture + setcap; RustDesk as fallback), Sunshine's AES inside the WireGuard tunnel. Encryption story: LUKS2 at rest (Conrad's disk), WireGuard in transit for everything, Signal E2EE on layer 1; unattended reboots wait at the LUKS prompt — accepted, no auto-unlock. Role split between the two stacks: still TBD.

**v3 revision log (Aug 27, later the same day)** — Conrad's calls, all live in the repo: **Claude is out of the setup entirely** (subscription being cancelled; no governor tier, no Anthropic API); DeepSeek side collapsed to a **single model, single setting** — `deepseek-v4-flash-vision-exp`, thinking always on at `max`, **no tiers**; **GLM-5.3-Flash in the ZCode harness added directly to the stable build** as a second stack (eval gate consciously skipped; first eval run will baseline both engines); **role split between the two stacks: TBD** — deliberately undecided. Capability substitutes for the removed frontier tier: best-of-5 self-verification, small checkable steps, and the two engines cross-checking each other. Chat channel decision (rev 2): **Signal via DIY `signal-cli` bridge** — the only E2EE option, feasible precisely because the bridge is DIY anyway (Discord/Telegram bot text is never E2EE; ZCode's native channels all route through Z.ai's servers). Bridge rules: allowlisted sender, low-privilege command set, confirmations for destructive actions, secrets never transit the channel. Sections below marked ⟨v3: superseded⟩ are kept for reference because the machinery they describe (tiers, routing, Claude escalation) can return via config at any time.

---

## 0. How to read this

Section 1 is the picture of the whole system. Section 2 is a glossary of every concept we covered in conversation, so your notes have definitions to anchor to. Sections 3–8 are the design itself. Section 9 is the build order — what to actually do first. Section 10 maps the AI Builder Club course you found onto this blueprint so you know which lessons to read when. Sources are at the end.

One framing note before anything else: the guide you linked is good, and its central claim is the right one — **an agent is a 60-line loop, not a framework**. Everything in this blueprint is built on that loop. The system below looks big on paper, but it's assembled from small parts you can understand completely, and you build it in phases, not all at once.

---

## 1. The system at a glance

You are building **one system with two builds**:

```
                    ACCESS LAYERS (outside the system)
  ┌───────┐
  │ phone │─1─ Signal (E2EE) ──────────► watchdog (recovery) +
  │       │                              dsh channel plugin (commands)
  │       │─2─ tailnet (WireGuard) ────► dsh web UI :3080 (HTTPS relay) · SSH/tmux
  │       │─3─ tailnet (WireGuard) ────► Sunshine ⇄ Moonlight (1:1 screen)
  └───────┘
   desktop use is local — no VPN, no bridge, straight to everything
                                   │
                                   ▼
        ┌────────────── SESSION MECHANICS ────────────────────────┐
        │  how chat windows work · main window rotates at 32k     │
        │  every task spawns its own fresh 32k worker session;    │
        │  tools run there; the distilled result returns here     │
        └────────────────────────────┬────────────────────────────┘
                                     │
                                     ▼
        ┌────────────────── MAIN WINDOW (LUKS2) ──────────────────┐
        │     full use of both models — no restrictions, the      │
        │     normal working mode (agentic runs, goals, chat)     │
        │  in DeepSeek's Harness or ZCode chat                    │
        │  compute via DeepSeek & Z.ai APIs                       │
        │  ┌──────────────────────────┬─────────────────────────┐ │
        │  │  DEEPSEEK HARNESS (dsh)  │  ZCODE (Z.ai harness)   │ │
        │  │  always-on service       │  Goal mode · batch      │ │
        │  │  V4-Flash-Vision-Exp     │  GLM-5.3-Flash          │ │
        │  │  thinking: max, always   │  reasoning: max, always │ │
        │  └──────────────────────────┬─────────────────────────┘ │
        └─────────────────────────────┼───────────────────────────┘
                                      │
                     ┌────────────────┴────────────────┐
                     │                                 │
                api output                  `!verify` toggle (on→off)
                     │                                 │
                     ▼                                 ▼
                 (result)            ┌────── LLM-AS-A-VERIFIER LAYER ────────────┐
                                     │  prompt + chat history → N candidates     │
   ┌────────────┐ ┌────────────┐     │  (default 5); GLM scores each one         │
   │ MATH STACK │ │ QUANT STACK│     │  independently; the winner is appended    │
   │ 1st domain │ │ 2nd domain │     │  back to the originating chat             │
   └────────────┘ └────────────┘     │ ┌────────────────────┬────────────────┐   │
   ┌────────────┐                    │ │ GENERATOR ×5:      │ JUDGE (always):│   │
   │ SECURITY   │                    │ │ Vision-Exp only    │ GLM-5.3-Flash  │   │
   │ WORK STACK │                    │ │ (any chat surface) │ 3-sample score │   │
   └────────────┘                    │ └────────────────────┴────────────────┘   │
                                     └─────────────────────┬─────────────────────┘
                                                           │
                                                           ▼
                                                   (verified result)

        ┌──────────────────────── MEMORY ─────────────────────────┐
        │   facts (bitemporal) · procedures · style · artifacts   │
        │   · archives + rotation log — supersede, never erase    │
        │   library/ — raw docs corpus, agentic retrieval only    │
        │   nightly consolidation proposes; curation gate decides │
        └────────────────────────────┬────────────────────────────┘
                                     │
        ┌──────────── OBSERVABILITY · EVALS ──────────────────────┐
        │  Langfuse hub · dsh trajectory JSONL · ~/.zcode logs    │
        │  status · regression + capability suites · preset matrix│
        │  evals gate promotion · run only when Conrad runs them  │
        └────────────────────────────┬────────────────────────────┘
                                     ▲
        ┌────────────────────────────┴─────────────────────────────┐
        │                                                          │
  ┌─────┴──────┐                                          ┌────────┴───────┐
  │   SYSTEM   │ ← promotion (normally through eval gates)│  EXPERIMENTAL  │
  │   BUILD    │                                          │     BUILD      │
  │ git: main  │ ────────────────────────────────────────►│  git: exp/*    │
  │ framework  │                                          │ try research   │
  │changes only│                                          │ & new models   │
  │by promotion│                                          │ can break      │
  └────────────┘                                          └────────────────┘
        │
   your daily work
```

No Claude anywhere in the running system (v3). Total spend: two cheap APIs — DeepSeek (off-peak scheduling, cache-hit pricing) and Z.ai (GLM-5.3-Flash at $0.15/$0.50 per M, promo-halved until Sep 9). In place of a frontier escalation tier, capability comes from **verification**: best-of-5 self-ranked attempts on checkable tasks, decomposition into small verifiable steps, and the two engines — different labs, different blind spots — cross-checking each other. The honest ceiling: unverifiable judgment tasks are capped at what these models can do; those outputs deserve your own eyes.

The two builds are **the same codebase on different git branches**. This is the single most important design decision, and it's nearly free: your agent's entire identity — which models it uses, its system prompts, its tools, its subagents, its skills — lives in plain files (YAML, Markdown, JSON) in one git repo. `main` is stable. `exp/*` branches are experiments. "Promoting" an experiment means passing eval gates and merging. "Rolling back" is `git revert`. You already know how this works, because it's just software.

The five models each have a job, and a **router** sends every task to the cheapest model that can do it well (this is the "router" question you asked about — here's where it becomes real):

**v3 roster — two models, two harnesses, no tiers:**

| Stack | Model | Setting | Job | Billed to |
|---|---|---|---|---|
| dsh | **DeepSeek V4-Flash-Vision-Exp** | thinking `max`, always | TBD — role split not yet decided | DeepSeek API |
| ZCode | **GLM-5.3-Flash** | max reasoning, always | TBD — role split not yet decided | Z.ai API |

Both engines are cheap, multimodal, 1M-context. GLM-5.3-Flash (320B-A18B MoE, MIT weights, video input) is versioned and pinnable; Vision-Exp is not — its pre-wired fallback is `deepseek-v4-flash`. If a stronger tier is ever needed again, V4-Pro (thinking max) or a spend-capped Anthropic API key are one-edit config additions.

⟨v3: superseded⟩ The v2 five-tier roster (V4-Flash engine / V4-Pro hard / Vision / Opus 5 governor / Fable 5 frontier on sub quota) is retired with the subscription. The tier *concepts* below remain worth knowing — they're how the system would re-grow if the two-engine ceiling starts to bite.

Everything else in this document is detail on how these parts work and how to build them in the right order.

---

## 2. Glossary — the concepts behind the design

These are the ideas from our conversation plus the handful of terms the 2026 literature uses that you'll keep running into. Definitions are short on purpose — good for flashcards.

**Agent.** An LLM in a loop with tools: call model → model requests a tool → execute tool → append result → repeat until done. The loop is the agent; the model is just the brain inside it.

**Agent loop / harness.** The code around the model: the loop itself plus error handling, step caps, logging, permissions, sandboxing. 2026 vocabulary: people now say "harness engineering" for the discipline of building this well. Key insight from Anthropic's Managed Agents work: harnesses encode assumptions that go stale as models improve — build the harness so parts can be swapped.

**Context window.** The model's working memory for a session. Cumulative within a session (your very first question in this conversation): every turn re-sends the whole history. Empty at the start of each new session.

**Context rot.** Measured degradation of model quality as context grows — starts around 50k tokens, well before the hard limit (Chroma tested 18 frontier models; all degrade). This is the empirical basis for everything below about compaction, subagents, and fresh sessions.

**Retrieval vs dumping.** Pulling only relevant excerpts into context vs pasting the whole document. Retrieval for needle-in-haystack tasks; dumping (in a dedicated session) for whole-document synthesis.

**Agentic search.** The 2026 winner over classic embedding-RAG for personal systems: instead of building a vector database, give the agent file tools (grep, glob, read) and let it find what it needs iteratively. Claude Code dropped vector RAG for exactly this. Embedding RAG still wins for very large corpora; you almost certainly don't need it to start.

**Throwaway session / distilled artifact.** Accept context-rot once, in a dedicated session whose only job is to mine a huge input down to a compact reusable output (the distilled artifact), then discard the session and work from the artifact in a clean one. Map-reduce for LLMs.

**Compaction.** The automated version of the same idea: when a session's context fills, summarize the old turns and continue with the summary. The Claude Agent SDK does this automatically. Related: Anthropic's **context editing** silently clears stale tool results from context without breaking prompt caching.

**Memory (files-as-memory).** Cross-session persistence done the simple way: the agent writes what it learns to Markdown/JSON files and reads them at session start. `CLAUDE.md` is the standing-instructions version of this. Anthropic's memory tool formalizes it. Vector-database memory is the last resort, not the first.

**Router.** The component that classifies each incoming task and dispatches it to a model tier or a specialized pipeline. Why frameworks have routers even though models can self-route: cost (10x savings), predictability (hard guarantees), specialization, and security (smaller blast radius).

**Orchestrator–worker (coordinator + workers).** The multi-agent pattern that works: one coordinator decomposes a goal, dispatches focused workers (often in parallel), and synthesizes results. Free-form agent-to-agent chat does not work. Multi-agent costs 3–15x tokens — pay it only for genuinely parallel, read-heavy work.

**Subagent.** A worker spawned with its own *fresh, isolated context window*. The orchestrator's context stays clean; the subagent returns only its conclusion. This is context-rot management as much as it is parallelism.

**MCP (Model Context Protocol).** Open standard for packaging tools so any agent client can use them. Build a tool once, every agent gets it.

**Skills.** Versioned folders of instructions (SKILL.md) an agent loads on demand — packaged expertise rather than packaged tools. Open standard since late 2025; progressive disclosure keeps them out of context until needed.

**Code execution as tool use.** Instead of the model calling 40 tools one at a time (each result flowing through context), the model writes a script that orchestrates the tools, and only the final result enters context. Anthropic measured a 98.7% token reduction on a real workflow. The single biggest efficiency lever documented in 2025–2026.

**Capability eval vs regression eval.** A capability suite is a hill you're climbing (starts at low pass rates). Once climbed, it graduates into the regression suite, which must stay at ~100% forever. This pair is the engine of your promotion pipeline.

**pass@k vs pass^k.** pass@k: succeeds at least once in k tries (good for "can it ever"). pass^k: succeeds all k times (the metric for a daily driver you rely on). Judge your stable build on pass^k.

**LLM-as-judge.** Using a model to grade another model's output against a rubric. Agrees with human graders ~85% of the time — above human-human agreement. Use for qualities code can't check; give the judge an "Unknown" escape hatch.

**Prompt caching.** Reusing an identical prompt prefix across calls at ~90% discount. Keep system prompt + tool definitions stable at the top of every request. On DeepSeek, cache-hit input is ~30x cheaper than cache-miss.

**Lethal trifecta.** Private data + untrusted content + an exfiltration channel in one agent context = exploitable by prompt injection regardless of how aligned the model is. Mitigation is structural: never let one context hold all three.

**Blast radius / containment.** Anthropic's 2026 security stance: model-level safeguards are probabilistic; deterministic environment-level defenses (sandboxes, egress controls, credentials kept outside the agent's reach) are what actually work. Don't supervise what the agent does — constrain what it *can* do.

---

## 3. The model roster in detail

### Anthropic ⟨v3: removed from the setup⟩

Claude Fable 5 and Opus 5 are out with the subscription cancellation — no governor tier, no Anthropic API key, no Claude Code subagent. Kept in mind, not in config: Opus 5 ($5/M input, matches or beats Fable 5 on most work) is the model you'd re-add first, as a spend-capped API key, if unverifiable-judgment tasks start failing in ways the two engines can't catch for each other.

### DeepSeek — the V4 family

DeepSeek replaced its whole lineup in 2026. The old `deepseek-chat` / `deepseek-reasoner` names were retired July 24, 2026. **R2 never existed** — V4's built-in thinking mode is the successor to the R-line. All three current models are hybrids: thinking mode on by default (effort `low`/`high`/`max`), disableable per call. All have 1M context / 384K max output. Pro and Flash are open-weights (MIT).

| | V4-Pro | V4-Flash | V4-Flash-Vision-Exp |
|---|---|---|---|
| API string | `deepseek-v4-pro` | `deepseek-v4-flash` | `deepseek-v4-flash-vision-exp` |
| Version | Pro-0813 (GA Aug 13, 2026) | Flash-0731 (Jul 31, 2026) | Aug 21, 2026 (experimental) |
| Architecture | MoE 1.6T total / 49B active | MoE 284B / 13B active | Flash backbone + vision |
| Input $/M (off-peak, miss/hit) | $0.66 / $0.022 | $0.22 / $0.007 | $0.22 / $0.007 |
| Output $/M (off-peak) | $1.98 | $0.66 | $0.66 |
| Concurrency | 500 | 2,500 | 2,500 |

Peak pricing (Mon–Fri 01:00–04:00 and 06:00–10:00 UTC) is 2x the off-peak numbers above. **Off-peak is 50% off — schedule batch jobs accordingly.** For you that means most of the US day is already off-peak; verify against your timezone.

Strengths: V4-Pro's agentic-coding numbers are strong (vendor-claimed SWE-bench Verified 80.6%, Terminal-Bench 87.9) and V4-Flash gets remarkably close at a third of the price. Vision-Exp reads screenshots/charts/GUIs at near-frontier level, billed at Flash rates, up to 384 tokens per image.

Honest caveats you should design around:

- Independent evals are cooler than vendor claims: Artificial Analysis puts V4-Pro ~20th overall; one independent Terminal-Bench run scored 78.7 vs DeepSeek's claimed 87.9; NIST placed it ~8 months behind the US frontier. Treat DeepSeek as your *cheap tier*, not your *equal tier* — which is exactly how the routing below uses it.
- Known weak spots: sandboxed terminal task completion, complex spreadsheet/financial modeling, and one reviewer found degraded coherence on long-document synthesis with Flash. Route those task types to Claude.
- API quirks that will bite you if you don't know them: (1) if a request includes `tools`, you **must** pass `reasoning_content` back on every subsequent request or you get a 400 error; (2) in thinking mode, `temperature`/`top_p` are silently ignored; (3) a beta `strict` mode enforces JSON-schema-valid tool arguments — use it; (4) Vision-Exp is API-only, no weights.
- DeepSeek ships an Anthropic-compatible API format, so Claude-oriented tooling (including Claude Code / Agent SDK) can point at DeepSeek models. Useful for the experimental build.

### The routing policy (write this down — it's the heart of the system)

**v3: there is no model routing right now — by design.** Every task in a stack gets the same model at max deliberation. The only dispatch decision is which *stack* a task goes to, and that split is TBD. What remains of the routing machinery is the **strategy** dimension:

```
incoming task
  │
  ├─ VERIFIABLE? (code with tests, terminal ops,
  │  data transforms — outcome checkable)   → best-of-5 samples,
  │                                            self-ranked by verifier
  │
  ├─ high-stakes but unverifiable?          → run on BOTH engines,
  │                                            agree-or-flag for Conrad
  │
  └─ everything else                        → single shot on its stack
```

The verifiable branch carries the system now: sampling a Flash-class model ~5x and self-ranking with a verifier beat Fable 5 single-shot on Terminal-Bench 2.1 at ~11x cheaper (LLM-as-a-Verifier, 2026). Wherever an outcome can be checked, compute-spread-cheap substitutes for compute-concentrated-expensive. Where verification is as hard as generation — judgment, taste, synthesis — no cheap trick recovers the gap anymore; cross-checking between the two engines catches *disagreements*, but a shared blind spot passes silently. That residual risk is the price of the no-Claude decision, and weekly transcript reading is what keeps it visible.

⟨v3: superseded⟩ The v2 cost-tiered routing tree (trivial→Flash-off, hard→Pro-max, judgment→Opus, tail→Fable) returns the day tiers do — it's config, not architecture.

---

## 3b. The Fable module (added 2026-09-04 — SPEC §2d)

The no-Claude rule was formally reversed on 2026-09-03. Claude Fable
(claude-fable-5-1, via the Claude Code CLI under the owner's Max
subscription) now sits above the two cheap stacks as the system's
judgment layer — never its token mill. Six roles, all add-only (any
failure degrades to the pre-Fable behavior; the core runs complete with
the module disabled):

`!escalate` — one deep answer on demand, rate-capped 10/day. Judge
calibration — weekly blind rescore of GLM's verify judgments from the
local judgment ledger; report-only. Verify arm — one Fable candidate
joins the 5-candidate pool (mode CROSS+FAM) to decorrelate model-family
blind spots; a DeepSeek co-judge (true logprob expectation, flag-gated)
averages with GLM's score. Handoff writer — rotation state rewrites and
retie merge reports (with explicit contradiction lists) come from fresh
long context instead of the 32k-degraded session. Consolidation author —
the nightly propose-only pass. Throne — a Claude Code session in the
repo may hold a lineage's main window (charter:
memory/prompts/throne.md); the inverted pyramid: costliest judgment
where tokens are fewest, DeepSeek/GLM workers everywhere tokens are many.

## 4. Architecture, layer by layer

### Layer 0 — the loop

The guide's core lesson stands. Before anything else exists, this exists, and you should write it yourself once so nothing above it is ever magic:

```python
while not done and step < MAX_STEPS:          # ALWAYS cap. 10–25.
    response = llm.call(messages, tools)
    messages.append(response)
    if response.stop_reason == "end_turn":
        return response.text
    if response.stop_reason == "tool_use":
        for call in response.tool_calls:
            result = execute_tool(call)        # returns a STRING
            messages.append(result)
```

Rules that live at this layer, from the guide and confirmed everywhere in the 2026 literature: always cap `MAX_STEPS` (uncapped confused agents loop forever and burn money); tool results are strings, never raw objects; tool descriptions are half the engineering — they are the only thing telling the model when to call what; log every tool call, every result, every token spend from day one.

### Layer 1 — providers and billing (v3: two native stacks, no gateway)

- **DeepSeek** is dsh's native adapter — one API key in `.env`, off-peak scheduling for batch, cache-hit pricing doing the heavy lifting.
- **Z.ai/GLM** is ZCode's native model — its own key (also `.env`), promo pricing until Sep 9; if usage runs heavy, a GLM Coding Plan (~$12.60/mo Lite) with its idle-time free queue may beat pay-as-you-go.
- **No Claude, no Anthropic billing of any kind.** (v2's Claude-Code-subagent-on-sub-quota mechanism — the pi-claude-bridge pattern — is documented in the revision history and works if a subscription ever returns.)
- **Config lives in `configs/`** per branch — swapping a build's model mix stays a one-line edit.
- **Budget caps:** per-key spend limits on both provider platforms; log per-stack usage for the weekly review.
- **LiteLLM remains the fallback plan**, not a component — relevant only if the system grows past two providers.

### Layer 2 — the harness (DeepSeek Harness, `dsh`)

v2 substrate: **dsh** (MIT, released Aug 13, 2026 — 195k GitHub stars in under two weeks). Its design principle is "everything is a plugin," built on the Cordis composability framework: the model adapter, tool registry, session log, sandbox, scheduling, UI, *and the agent loop itself* are replaceable plugins. For the two-build design this is ideal — an experiment is literally one plugin swapped on a branch. It ships a web UI (`npx @deepseek-ai/dsh web`, port 3080), and it can spawn **Claude Code as a subagent** natively, which is the governor tier's entry point.

The honest trade you accepted with dsh: it is a **developer preview with promised breaking changes**. Discipline that follows: pin the dsh version on `main` (record it in `configs/`), upgrade dsh itself through the experimental track like any other change, and keep your own logic in your own plugins/files rather than forks of internals.

The critical property survives the substrate swap: *everything is files and plugins in one git repo*. Prompts, configs, plugins, memory, evals — a directory tree. That's what makes git branches a complete stable/experimental mechanism. (The Claude Agent SDK patterns v1 leaned on — subagents, hooks, CLAUDE.md-style memory files, compaction — remain the right *concepts*; they now live as dsh plugins and repo conventions instead of SDK features.)

Two 2026 upgrades to adopt early, because they're the biggest token levers documented anywhere:

1. **Tool Search** — don't load 50 tool definitions into every context; let the agent search for tools on demand.
2. **Code execution over MCP / programmatic tool calling** — for multi-step tool workflows, the agent writes a script that calls the tools and returns only the final answer to context. Anthropic measured 150k tokens → 2k on a real workflow.

### Layer 3 — context and memory

The policy, in order of preference (this operationalizes our whole conversation):

1. **Keep it out of context.** Agentic search over your files instead of pre-loading; Tool Search instead of tool dumps; code execution instead of tool-result chains.
2. **Isolate it.** Anything big and separable goes to a subagent with a fresh window that returns only conclusions. Research fan-outs, large-file digestion, verification passes.
3. **Distill it.** Whole-document synthesis gets a throwaway session that produces a distilled artifact; the artifact is what enters your working sessions. Store artifacts as files in the repo (`memory/artifacts/`).
4. **Compact it.** For long-running sessions, SDK auto-compaction plus a progress file. Anthropic's long-horizon harness pattern: a JSON task list with pass/fail flags + descriptive git commits + an init script = a new session can re-orient from durable artifacts instead of inheriting a polluted window. Prefer JSON over prose for state files — models are less tempted to editorialize in JSON.
5. **Remember it.** Cross-session memory is Markdown/JSON files the agent reads at start and updates when it learns something: `CLAUDE.md` for standing instructions and preferences, `memory/` for accumulated facts. No vector database until files become genuinely unmanageable — most personal systems never get there.

Session hygiene rules (your "100% intelligence 24/7" question, answered as policy): reset at task boundaries, not on a timer; never converse inside a polluted context — mine it and leave; every heavy session ends by writing its distilled artifact before you close it.

### Layer 4 — safety and containment

You're giving agents your files and real credentials, so adopt the 2026 stance: **constrain what agents can do, don't just watch what they do.**

- Run agent code execution in a sandbox (the SDK's sandboxing, or a container/VM for the experimental build — experiments should be *structurally* unable to touch things that matter).
- Credentials live outside the agent's casual reach: the DeepSeek key in `.env` loaded by the service (gitignored, never in configs or memory files); Claude auth held by Claude Code's own login, never an exportable key in the repo.
- Break the lethal trifecta: an agent processing untrusted web content should not simultaneously hold private data and an exfiltration channel. Least-privilege tools per subagent — the researcher gets web access, not your files; the file-organizer gets your files, not the web.
- Human approval gates (SDK hooks) on irreversible actions: sending, deleting, purchasing, deploying.
- Cap everything: max_steps per loop, budget per virtual key, timeout per session.

---

## 5. The two builds

### Repo layout

This repo now **exists** (scaffolded Aug 27, `main` + `exp/first-experiment` branches live). Current state plus planned growth:

```
agent-system/                  # ✅ = scaffolded, ○ = to build
├── README.md                ✅ # architecture, setup order, rules
├── .env.example             ✅ # DeepSeek key template (.env gitignored)
├── setup/                   ✅ # 01 headscale · 02 join devices · 03 agent host
├── configs/
│   ├── stable.md            ✅ # tier table, escalation, contingency, pins TBD
│   └── experimental.md      ○
├── plugins/                 ✅ # zcode-agent-system + zcode-marketplace built · dsh plugins ○
├── memory/                  ○  # facts.md + artifacts/ (distilled artifacts)
├── evals/                   ○  # regression/ + capability/ + run.py
└── logs/                    ✅ # gitignored
```

### The stable build (`main`)

Boring on purpose. Everything pinned that *can* be pinned: the dsh and ZCode versions, GLM-5.3-Flash (versioned, MIT), prompt versions, tool schemas — with Vision-Exp as the one unpinnable exception (fallback: `deepseek-v4-flash`, one edit). Normally changes only via promotion; v3 note: GLM entered stable by decision rather than through the eval gate, so the first eval run baselines both engines and retroactively earns that promotion. Judged on **pass^k** — works every time — not pass@k.

### The experimental build (`exp/*`)

One branch per experiment, e.g. `exp/v4-pro-as-main`, `exp/new-memory-scheme`, `exp/parallel-research`. Allowed to break. Runs under its own budget-capped virtual key and a stricter sandbox. This is where new research gets tried the week it drops: a new DeepSeek release is a one-line alias change on a branch; a new orchestration paper is a new subagent definition; a new context-management trick is a CLAUDE.md edit. Nothing touches your daily driver until it survives the gauntlet:

### The promotion pipeline

1. **Eval gate.** Experimental must beat stable on the relevant capability suite AND hold the regression suite at ~100%. No regression, no discussion.
2. **Shadow week.** Run both builds on the same real tasks for several days — stable's output is what you actually use; experimental runs the same jobs in parallel (off-peak DeepSeek pricing makes this cheap). An LLM judge diffs the outputs; you skim the diffs.
3. **Canary.** Route a slice of real, low-stakes work to experimental for a few days. Watch cost, failure rate, and your own annoyance level.
4. **Promote.** Merge to `main`, tag the release (`v1.4.0`), note what changed and why in a CHANGELOG. The capability suite it just climbed graduates into the regression suite.
5. **Rollback** is `git revert` plus re-pinning the config. Instant, and the reason none of this is scary.

The lifecycle in one line: **research → exp branch → evals → shadow → canary → merge → the eval graduates → next experiment.** This is the same loop Anthropic describes for its own agent products, scaled down to one person — and it's what "utilizing the latest research" means in practice: a standing, low-cost procedure for absorbing new ideas without ever betting your working system on them.

---

## 6. Evaluation — how you know experimental beat stable

Without evals, "is the new build better?" is vibes, and vibes are exactly what context rot and silent regressions exploit. The good news from Anthropic's January 2026 evals guide: a solo builder needs far less than you'd think.

**Start with 20–50 tasks harvested from real failures.** Every time the stable build embarrasses itself, that becomes a test case. Early on, effect sizes are large, so small suites separate builds cleanly. Each task needs: the input, a reference solution proving it's solvable, and a grading rule two reasonable people would apply identically.

**Grade outcomes, not transcripts.** Check the end state — the file is correct, the answer matches, the code passes tests — not whether the agent *said* it succeeded. Agents declare premature victory constantly; never let the agent's self-report be the grade.

**Prefer deterministic graders; use LLM judges for the rest.** String/number checks and unit tests where possible. For qualities code can't check (tone, usefulness, judgment), an LLM judge with a written rubric, one judge per dimension, an "Unknown" escape hatch, and partial credit.

**Run multiple trials.** Agent performance is high-variance; single runs lie. Use pass@k for capability ("can it do this at all") and pass^k for the stable gate ("does it do this every time").

**Balance both directions.** Include should-act cases AND shouldn't-act cases — an agent that never overreaches but also never acts passes half your suite and is useless. Test both failure modes.

**Read transcripts weekly.** The highest-value 30 minutes in the whole system. A 0% pass rate usually means a broken task, not a broken agent; weird tool-call patterns predict failures before they show in scores. Tooling: Langfuse is already in place — the self-hosted six-container stack runs at localhost:3000 as the observability hub, and its datasets + judge scoring will host this suite; promptfoo (YAML evals in-repo, CI-friendly) remains an option beside it.

**The layered picture:** evals before promotion + spend/failure monitoring in production + transcript sampling + your own experience using it daily. No single layer catches everything; together they catch almost everything. And the payoff compounds: a solid suite is what lets you adopt a brand-new model in days — run the suite, read the diffs, decide — instead of weeks of cautious poking.

---

## 7. Cost discipline

The levers, in order of impact:

1. **Prompt caching.** Keep system prompt and tool definitions byte-stable at the top of every request. ~90% off cached input on Anthropic; on DeepSeek, cache-hit input is $0.007/M vs $0.22/M — effectively free.
2. **Routing.** 60–80% of real workloads run fine on cheap models. The tier table in §3 is the design; the savings reported by teams doing this are 40–85%.
3. **DeepSeek off-peak scheduling.** 50% off outside peak windows (peak: Mon–Fri 01:00–04:00 and 06:00–10:00 UTC). Batch jobs, shadow runs, and eval suites run on the off-peak clock.
4. **Caps everywhere.** max_steps on every loop; budgeted virtual keys per build; alerts at 50/80/100% of monthly budget. A confused agent without caps is a money-burning machine — this is the guide's most repeated warning and every production team's scar tissue.
5. **Context efficiency as cost efficiency.** Every technique in §4 Layer 3 (Tool Search, code execution, subagent isolation, compaction) is also a cost lever — tokens not in context are tokens not billed, turn after turn.
6. **Multi-agent only when it pays.** 3–15x token cost. Breadth-first research: worth it. Sequential tasks: one agent is better. Ask "would parallel workers beat one focused agent here?" before every fan-out.

Rough expectations for *this* system (v3, no-Claude, always-max): the whole bill is two cheap APIs — DeepSeek plus Z.ai — realistically single digits to a few tens of dollars monthly even with thinking always at max (both models are Flash-class on output pricing; always-max costs more latency than money), plus desktop electricity. The $200/month subscription goes away entirely. Watch two things: the Sep 9 end of GLM's promo pricing when deciding the role split, and best-of-5 runs multiplying token spend 5x on whatever task class you apply them to — cheap per task, noticeable if it becomes every task.

---

## 8. Failure modes and their mitigations

The ten ways systems like this actually break, from Berkeley's MAST taxonomy (1,600+ analyzed failure traces), Anthropic's postmortems, and the guide's pitfall list — each with its structural fix already present in this design:

1. **Over-architecting.** More agents = more latency, cost, and debug surface. Fix: single agent + subagents on demand; add structure only when a measurement says so.
2. **Context rot.** Fix: the entire Layer 3 policy.
3. **Telephone-game handoffs.** Lossy summaries between sessions lose the plot. Fix: durable artifacts — progress JSON, git log, distilled-artifact files — not prose summaries alone.
4. **Premature victory.** Agent marks work done without verifying. Fix: outcome-graded evals; a verifier subagent for important output; feature-list JSON the agent may only flip after end-to-end self-verification.
5. **Reward hacking.** Agent satisfies the letter of the check. Fix: make verifiers near-perfect and cheat-resistant; audit surprising passes as skeptically as failures.
6. **Prompt injection / lethal trifecta.** Fix: structural separation per §4 Layer 4; approval gates on irreversible actions.
7. **Uncapped blast radius.** Fix: sandboxes, egress limits, credentials at the gateway — containment over supervision.
8. **Runaway cost.** Fix: §7's caps; escalation-only routing so expensive models are the exception path.
9. **Silent regression.** "It feels dumber lately" with no data. Fix: the regression suite and weekly transcript reads.
10. **Stale harness assumptions.** Workarounds built for one model generation become dead weight on the next (Anthropic hit this themselves). Fix: document every hack with the model it was built for; re-test hacks on every model upgrade; keep interfaces stable and implementations swappable.

---

## 9. Build order

Resist building all of this at once. Each phase produces something you use daily before the next phase starts.

**Phase 0 — the loop (one evening).** Write the 60-line agent from scratch against the Anthropic API. Give it two tools (read file, web search). Run it on a real task. Cap the steps. This is load-bearing understanding for everything else.

**Phase 1 — access + harnesses up (a weekend). ✅ DONE (Aug 28).** As deployed: headscale serves HTTPS at `YOUR-DOMAIN` (listen LAN-IP:443, Let's Encrypt, embedded DERP; router forwards TCP 80+443 + UDP 3478 — the old TCP 8080 forward is retired), the desktop rejoined and the phone enrolled via `headscale auth register`. dsh runs as a service bound to loopback only, published to the tailnet by the Caddy relay at `https://dsh.YOUR-DOMAIN:3080` (real cert, auto-renewing); remote use resumes existing sessions, since the workspace picker is a native host dialog. ZCode installed with its GLM key. Pin both harness versions once working.

**Phase 2 — verification + dispatch (a week of evenings). ✅ MOSTLY DONE (Aug 28).** The best-of-5 verifier lane is live — GLM judges on Z.ai at thinking-low with a text-parsed score, 3-sample average at temp 0.6 (the endpoint returns no logprobs); the cross-check mode is confirmed working; generator calls run `max_tokens` 16384 everywhere. `!do` (toggle + one-shot) and `!rotate` are real, the ZCode surface plugin is built, and Langfuse (six containers, localhost:3000) logs every call and per-stack spend. Still open, deliberately: the role split between the stacks. You now have the stable build, v1.0 — start using it daily.

**Phase 3 — evals (a weekend). ← YOU ARE HERE.** Harvest your first ~20 tasks from whatever annoyed you in Phase 2. Write the grading script. Baseline the stable build. You now have the gate.

**Phase 4 — the experimental track (ongoing, this is the fun part).** First experiment, and it's a natural one: `exp/deepseek-bulk` — route batch coding to V4-Pro off-peak and measure quality-per-dollar against Opus 5 on your own suite (trust your evals over both vendors' benchmarks). Then run the promotion pipeline for the first time, end to end, even if the answer is "don't promote" — the pipeline itself is what you're commissioning.

**Phase 5 — compounding (steady state).** Weekly: read transcripts, harvest eval tasks, check spend. When new research drops: exp branch, gauntlet, promote or discard. The system now improves on a schedule instead of by mood.

---

## 10. Reading path — the AI Builder Club course, mapped to this blueprint

The guide you found is the hub of a real course, and it's well-sequenced. Read it in this order, matched to the phases above:

**With Phase 0:** 1.2 What Is an AI Agent → 1.3–1.4 Function Calling → 2.1 Build an Agent in 60 Lines of Python. Skip frameworks entirely for now (the guide agrees: default to raw API).

**With Phase 1:** 4.32 Why Your Agent Bill Is Wrong (cost discipline) and 3.9 Prompt Engineering 2026.

**With Phase 2:** 1.5–1.6 Memory → 3.6 Context Engineering: The Real Bottleneck → 3.7 RAG vs Long Context vs Fine-Tuning (this trio is our whole retrieval-vs-dumping conversation, formalized) → 3.1 MCP 101 → 3.4 Skills (their "MCP is dead" framing is overheated — you'll use both — but the skills content is right) → 1.9–1.12, the Karpathy lessons (agents.md, LLM wiki = the files-as-memory pattern).
**Also:** Anthropic's "Building Effective Agents" and "Effective context engineering for AI agents" — the two primary sources under most of this blueprint.

**With Phase 3:** 4.26 How to Evaluate AI Agents → 4.8 Loop Engineering: Write Verifiers, Not Prompts (the single best mindset shift in the production module: invest in checking, not in begging the model) → Anthropic's "Demystifying evals for AI agents."

**With Phases 4–5:** 1.7 Multi-Agent Orchestration → 2.2 Coordinator + Workers in 200 lines → 4.1 Agent Modes → 4.2 Agent Sandbox → 4.4 Harness: The 6 Components → 4.16–4.18 Graph Engineering (when your workflows outgrow a single loop) → 3.3 MCP Security → 4.33 A Role Label Is Not a Sandbox.

One calibration note: the course's model references (Sonnet 4.5, GPT-4o, Opus 4.5) date from before the current generation — read those as placeholders for the roster in §3. The patterns are current; the model names aren't. That gap is itself a lesson this blueprint is built around: **patterns outlive models, so pin models in config and let the patterns stand.**

---

## 11. Sources

**Primary — Anthropic engineering** (the load-bearing sources): [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) · [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) · [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) · [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents) · [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) · [Advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use) · [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) · [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) · [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) · [Managed Agents](https://www.anthropic.com/engineering/managed-agents) · [How we contain Claude](https://www.anthropic.com/engineering/how-we-contain-claude) · [Building a C compiler with parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler) · [Claude Opus 5 announcement](https://www.anthropic.com/news/claude-opus-5)

**DeepSeek — official**: [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing) · [Change Log](https://api-docs.deepseek.com/updates/) · [V4-Pro GA announcement](https://api-docs.deepseek.com/news/news260813) · [Vision-Exp announcement](https://api-docs.deepseek.com/news/news260821) · [Thinking Mode guide](https://api-docs.deepseek.com/guides/thinking_mode) · [Tool Calls guide](https://api-docs.deepseek.com/guides/tool_calls) · [V4 tech report](https://arxiv.org/pdf/2606.19348) · [Hugging Face: deepseek-ai](https://huggingface.co/deepseek-ai)

**Independent checks on DeepSeek claims**: [OrcaRouter benchmark ledger](https://www.orcarouter.ai/blog/deepseek-v4-pro-benchmark) · [NIST CAISI evaluation](https://www.nist.gov/news-events/news/2026/05/caisi-evaluation-deepseek-v4-pro) · [SCMP on independent benchmarks](https://www.scmp.com/tech/big-tech/article/3363895/deepseeks-updated-v4-pro-ai-model-struggles-benchmarks-shines-cybersecurity) · [Bloomberg on Vision-Exp](https://www.bloomberg.com/news/articles/2026-08-21/deepseek-unveils-test-model-to-rival-anthropic-s-opus-4-8)

**Research & ecosystem**: [Chroma: context rot](https://research.trychroma.com/context-rot) · [Berkeley MAST failure taxonomy (arXiv 2503.13657)](https://arxiv.org/abs/2503.13657) · [Agentic RAG survey (arXiv 2501.09136)](https://arxiv.org/abs/2501.09136) · [Cognition: Don't Build Multi-Agents](https://jxnl.co/writing/2025/09/11/why-cognition-does-not-use-multi-agent-systems/) · [LangChain: how and when to build multi-agent](https://www.langchain.com/blog/how-and-when-to-build-multi-agent-systems) · [LiteLLM + Claude Code setup](https://www.morphllm.com/claude-code-litellm) · [Claude Agent SDK docs](https://platform.claude.com/docs/en/agent-sdk)

**v2 additions**: [DeepSeek Harness repo](https://github.com/deepseek-ai/deepseek-harness) · [LLM-as-a-Verifier](https://github.com/llm-as-a-verifier/llm-as-a-verifier) ([result thread](https://x.com/jackyk02/status/2089421448784023553)) · [Agent SDK + Claude plan (Anthropic help center)](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) · [pi-claude-bridge (the subscription-through-Claude-Code mechanism)](https://github.com/elidickinson/pi-claude-bridge) · [Headscale](https://github.com/juanfont/headscale)

**v3 additions**: [GLM-5.3-Flash release (MarkTechPost)](https://www.marktechpost.com/2026/08/26/z-ai-releases-glm-5-3-flash-a-320b-a18b-natively-multimodal-moe-with-a-1m-token-context/amp/) · [GLM-5.3-Flash pricing (OpenRouter)](https://openrouter.ai/z-ai/glm-5.3-flash) · [ZCode overview](https://tokenstead.ai/agent-harnesses/zcode) · [ZCode review (Flowtivity)](https://flowtivity.ai/blog/zcode-glm-coding-agent-harness/) · [ZCode data-jurisdiction note (TechTimes)](https://www.techtimes.com/articles/319707/20260704/ai-coding-assistant-zcode-launches-free-china-data-law-applies-every-glm-52-api-call.htm)

**The course**: [AI Agents in 2026 — AI Builder Club](https://www.aibuilderclub.com/blog/ai-agents)

*Flag on sourcing: DeepSeek's agentic benchmark numbers are largely vendor-reported and at least one independent reproduction came in 9 points lower; NIST and Artificial Analysis place V4-Pro solidly behind the frontier. The design treats DeepSeek as the value tier accordingly. Anthropic "Managed Agents" details partly come from press coverage. Verify pricing against the official pages before hardcoding — it changed twice this summer alone.*
