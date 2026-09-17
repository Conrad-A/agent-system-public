# MIGRATION — v1 (SPEC v3.1, exp/fable-max @ a7b4f4f) → v2 (SPEC.md)

Written 2026-09-14 from the backup analysis. Companion to SPEC.md.
Nothing here is applied yet; it is the file-by-file plan for the rebuild.

## 0. Ground truth at the start

- Genome: `exp/fable-max` @ `a7b4f4f` (2026-09-04), clean tree, 39/39
  tests green on the backup copy, GitHub remote `backup` in sync
  (`main` @ `2e5f565` is the pre-Fable Sep 1 system — do NOT rebuild from it).
- Body: `~/Desktop/agent-system-runtime/` survived through 2026-09-05
  (two lineages, judgment ledger, fable log, two unruled consolidation
  proposals, watchdog log).
- Host: lost (reinstalled ~2026-09-07). Every service must be recreated —
  most are NOT being recreated (see §3).
- `.env` with live keys is in the disk backup (gitignored — never in a clone). The GitHub PAT that sat in `.git/config`
  was rotated 2026-09-14 and now lives in `~/.git-credentials`; rotate again only if a token ever sits in a remote URL.
- `agent-system-v1.0.zip` is the Sep 1 system: stale, keep as an artifact
  only.

## 1. Plumbing — file by file

| File | Action | Notes |
|---|---|---|
| `plumbing/worker.py` | REWRITE as adapter; loop MOVES to `runtimes/plain.py` | brief → runtime.run() → report via lineage. Workspace = brief scope, never `~/Desktop`. |
| `plumbing/runtimes/engine.py` | NEW | `DeepSeekHarness(dsh_home=$AGENT_RUNTIME/dsh-home, cwd=<scope>, profile=sdk-minimal or sdk, patches=(<composition>.patch.yml,), model="deepseek-flash", reasoning_effort, max_tokens)`; `run(brief, session_id=<worker id>)`; maps RunResult + events to the report; the trajectory is the runtime's own session JSONL (SPEC §4.2, corrected against 0.1.5rc1 on 2026-09-14 — there is no `cordis=` argument). |
| `plumbing/runtimes/plain.py` | NEW (moved code) | today's loop; tool catalog stays; API via `clients.py` (this host has no `openai` package); jail = the brief's scope. |
| `plumbing/runtimes/__init__.py` | NEW | select(): flag > `WORKER_RUNTIME` > `engine`; narrow auto-fallback on engine start failure, stamped. |
| `plumbing/compositions/minimal.patch.yml`, `standard.patch.yml` | NEW | PATCH files over the shipped `sdk-minimal` / `sdk` profiles (no cordis.yml copies): sandbox `workspace-write`; in standard also approval `never`, compaction / web / ralph / workflow off, bash 300 s. `DSH_SESSION_DIR` is gone; `DSH_HOME` = `$AGENT_RUNTIME/dsh-home`. |
| `plumbing/do.py` | KEEP, extend | `--preset`, `--runtime`, `--n` (later), launches the worker DETACHED (`setsid`/`nohup` — a Claude Code background task dies with the session; same for `swarm.py`); the lead starts the `Monitor` on events.jsonl after it returns (a script cannot). |
| `plumbing/lineage.py`, `lineage_cmd.py` | KEEP | add `waiting` state, ask-back/answer files, trajectory path, `runtime`/`data_tier`/`cost` report fields. |
| `plumbing/supervisor.py` | NEW | Layer 1 (SPEC §5.1): trip rules table, pause (engine) / stop (plain), `context` rule (26k steer / 32k stop on both runtimes), events.jsonl. |
| `plumbing/steer.py`, `stop.py`, `resume.py` | NEW (tiny) | the lead's three verbs. |
| `plumbing/check.py` | NEW | checker ladder R1–R5; stamps results into the report. |
| `plumbing/status.py` | KEEP, extend | workers incl. `waiting`, runtime, cost line; drops verify/fable/calibration lines. |
| `plumbing/think.py` | KEEP | becomes the `think` preset (tool-free call). Pin `deepseek-flash`. |
| `plumbing/consolidate.py` | REWRITE | copy durable memory files + 7 days of trajectories/handoffs → `claude -p --allowedTools Read,Grep,Glob,Write,Edit` in the copy → DIFF.md; whole-repo `git status --porcelain` + `git diff HEAD` before/after — any change outside the copy = night FAILED, no DIFF.md, no auto-revert. No fallback: CLI unavailable = skip the night (SPEC §8.2). |
| `plumbing/apply_dream.py` | NEW | applies DIFF.md hunks (all, or `--hunks 2,5`); removed lines → audit section with the dream's reason; hunks touching style/adjudication/audit/prompts rejected. |
| `plumbing/ingest.py` | KEEP | unchanged. |
| `plumbing/fable.py` | SHRINK | only the `claude -p` transport + log, used by consolidate; rate cap can go. |
| `plumbing/rotate.py` | REWRITE | becomes `/rotate` (SPEC §3): rewrite state.md, write `runtime/handoffs/<timestamp>.md`, end the session; the PreCompact hook is the backstop (same handoff + a `compaction` EVENT); SessionStart injects. Discovery/zstd code deleted (no dsh sessions to find). |
| `plumbing/toggle.py`, `standard_chat.py` | DELETE | window toggles and opposite-CoT chat mode were dsh-surface features. |
| `plumbing/verify.py`, `calibrate.py` | DELETE | LLM-judge layer removed (SPEC §6). Pull the DeepSeek/Z.ai clients out into `clients.py` first. |
| `plumbing/escalate.py` | DELETE | the lead is the escalation. |
| `plumbing/clients.py` + `envfile.py` | NEW | one OpenAI-compatible client per provider, stdlib `urllib` (DeepSeek now; GLM reserved); `envfile.load_env()` reads `.env` into the environment for every plumbing entry point. |
| `plumbing/costs.py` | NEW | usage fields → `runtime/costs.jsonl`. |
| `plumbing/swarm.py` + `tools/web_fetch.py`, `web_search.py` | BUILT 2026-09-15 (step 8) | SPEC §7; plus `plumbing/sanitize.py` (the report sanitizer, every filed report) and `configs/data-tiers.md` (§9, empty). |
| `plumbing/watchdog/` | DELETE | Signal watchdog dropped. |
| `plumbing/tests/run_tests.py` | KEEP, prune + extend | drop verify/calibrate/escalate/toggle/rotate-discovery tests (~15); add: runtime contract test (both runtimes), supervisor trip rules, check.py rungs, ask-back, costs, data-tier refusal (dormant until §9 wakes). |

## 2. Plugins, configs, docs

| Path | Action |
|---|---|
| `plugins/dsh-agent-system/`, `plugins/zcode-agent-system/`, `plugins/zcode-marketplace/`, `plugins/dsh-signal-channel/` | DELETE (surfaces gone). |
| `.claude/commands/` or `.claude/skills/` | NEW: `/worker`, `/status`, `/steer`, `/stop`, `/resume`, `/check`, `/swarm`, `/consolidate`, `/ingest`, `/rotate`. (Lineage commands dropped — SPEC §3.) |
| `.claude/hooks/` | NEW: PreCompact (handoff backstop + `compaction` EVENT), SessionStart (inject state + newest handoff), UserPromptSubmit (one line calling `status.py --line`: lead context size, state.md age, worker lines). |
| `CLAUDE.md` | REWRITE: lead role, working agreements, boring-by-default + the §14 novelty budget, style.md + adaptivemem imports, "talk to workers only via plumbing/". |
| `HANDOFF.md` | REWRITE at first v2 session; keep the v1 file as `HANDOFF-v1.md` for history. |
| `SPEC.md` | PROMOTED 2026-09-16: `SPEC-v2.md` → `SPEC.md`, the v1 spec → `SPEC-v3.1.md` (kept as the v3.1 record); references swept in the live docs, code and tests; docs/history/ and memory/ untouched (gate item in HANDOFF.md). |
| `FIELD-NOTES.md` | KEEP; prune remote-access/Signal/ZCode sections to an "historical" appendix; ADD: V4.1 quirks, SDK pin/bump notes, the exact Minimal composition. |
| `OPERATIONS.md` | REWRITE (much shorter): health check = app link + timer; SDK bump; credential hygiene. |
| `FABLE-MODULE*.md` | ARCHIVE under `docs/history/`. (`VERIFIER2.md` was an empty placeholder — removed.) |
| `configs/stable.md` | REWRITE: `deepseek-flash` pin + date, SDK version pin, claude CLI version; remove the no-Claude text and the ZCode table. |
| `configs/experimental.md` | RESET to template. |
| `configs/toolbox.md` | KEEP (empty); web tools become its first rows. |
| `configs/data-tiers.md` | NEW, empty registry (SPEC §9). |
| `systemd/calibrate.*` | DELETE. `systemd/consolidate.*` NEW in repo (v1's was hand-written on the host). |
| `setup/01,02,04,05,06` | ARCHIVE (headscale, join, signal, remote desktop, langfuse). `setup/03` REWRITE as `setup/host.sh`: Claude Code, python deps, SDK pin, timer install. |
| `evals/` | KEEP (3 tasks); grows from real failures. |
| `memory/` | KEEP everything. Rule the two pending proposal files through the gate in step 6. Delete junk archives 0135/0139 (owner's call, flagged since 09-04). |
| `agent-system-blueprint.md`, `agent-system-diagram.html` | ARCHIVED under `docs/history/`; REDRAWN for v2 2026-09-16 as `agent-system-diagram.html` at the repo root (one self-contained page, inline SVG, from SPEC §1-§8 and §11 as built; generated by `plumbing/gen_diagram.py` since 2026-09-16, which also copies KICKOFF.md's Linux block into the page's "Replicate this system" section — the suite asserts the page equals the generator's output and the block equals KICKOFF.md). |

## 3. Host services

| v1 service | v2 |
|---|---|
| `agent-system` (dsh in tmux) | gone — engine runs per worker as a subprocess |
| `dsh-tailnet-relay` (Caddy) + acme.sh cert | gone |
| headscale + tailscaled (self-hosted) + DuckDNS cron + router forwards | gone — close the forwards (80/443/3478) |
| Sunshine | gone |
| signal-daemon + watchdog | gone — let the bot number lapse |
| Langfuse docker ×6 | gone (optional later) |
| consolidate.timer | KEEP (unit now ships in repo) |
| calibrate.timer | gone |
| Claude Code CLI + desktop app | already installed on the fresh host — record the CLI version in configs/stable.md; the desktop app holds the phone link (+ sleep inhibitor while linked) |
| Optional later | official Tailscale + SSH |

## 4. Runtime state (body)

- `runtime/…` in SPEC and in this file means `$AGENT_RUNTIME/…` (from
  `.env`) — the body, outside the repo; never `<repo>/runtime/`.
- Keep `~/Desktop/agent-system-runtime/` as is. Lineages carry over.
- `verify/judgments.jsonl`, `fable/log.jsonl`, `windows/*.json`: historical;
  nothing in v2 reads them. Leave in place.
- New files: `events.jsonl`, `costs.jsonl`, `scorecard.jsonl`, `handoffs/<timestamp>.md`, `swarms/<sweep>/` (log, status, the search-auth file while a sweep runs); trajectories stay where the runtimes write them — engine `dsh-home/sessions/<cwd-mangled>/<wid>/session.v3.jsonl`, plain `lineages/<id>/worker-<hex>.log` (SPEC §4.2).

## 5. Sequence (matches SPEC §16)

1 clone + .env + SDK pin + CLAUDE.md → 2 workers (both runtimes) +
CoT flight test → 3 supervision → 4 checker ladder → 5 rotation →
6 consolidation + gate pass → 7 cost ledger → 8 swarm.
Working agreements unchanged: one change at a time; flight test before the
next; suite green before promoting; commit + push `backup` after each
meaningful change; paste-safe commands; `rm -f .git/*.lock` before local
commits after sandbox sessions.

## 6. Kickoff line for the first v2 session

"Read HANDOFF.md, then SPEC.md, then MIGRATION.md; the repo is at
~/Desktop/'Project 2'/agent-system on the fresh Fedora host, branch
exp/v2. Start at MIGRATION §5 step 1; confirm the step before acting."
