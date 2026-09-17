# FABLE MODULE — proposal (2026-09-01; STATUS 2026-09-04: BUILT AND
# EXCEEDED — no-Claude rule removed, phases 0-6 shipped on exp/fable-max;
# SPEC §2d is the living contract, this file is design history)

Adding Claude Fable 5 (Anthropic's Mythos-class model) to the system as an
OPTIONAL capability plugin. Designed by Fable itself — read with that bias
in mind; the anti-goals section is the honest half.

## 1. Why, and why only this much

The system's own research verdict stands: for GENERATION, 4-5 verified
Vision-Exp candidates match a frontier model at a fraction of the cost —
that is why the verifier layer replaced a frontier escalation tier, and
nothing here reverses that. The cheap stacks' remaining weakness is
long-horizon JUDGMENT: architecture decisions, drift detection, evidence
review. Fable enters only there — a scalpel, never a daily driver.

Cost frame: the owner rejected Fable at subscription prices ($200/mo) as a
daily driver — correctly. The uses below total an estimated **$3–10/month**
at API pay-per-use, metered and visible per call.

## 2. Governance (this reverses a closed decision — do it formally)

- SPEC §1 currently says "No Claude / no Anthropic dependency." Amend to:
  "Core system: no Anthropic dependency. An OPTIONAL Fable module (this
  file) may be enabled per-instance; the system degrades to fully
  functional without it."
- Enters via the §2c capability-plugin pattern: one removable unit, exp
  branch first, `ANTHROPIC_API_KEY` in `.env` (gitignored). Key absent =
  every Fable feature reports "module disabled" and nothing else changes.
- The shareable replication kit stays Claude-free: replicators build the
  identical system and may enable this module or ignore it.
- Autonomy principle unchanged: no Fable call ever fires without Conrad
  initiating it, except the weekly calibration sample (same sanctioned
  class as nightly consolidation: scheduled, read-only, only reports).

## 3. Use 1 — Architect sessions (no API, no code; a practice)

A recurring session (monthly, or after any major change) in Claude with
this repo attached. Fixed agenda, becomes `memory/prompts/architect.md`:

1. Read SPEC §8 open decisions; for each, check whether Langfuse now holds
   enough evidence to close one (e.g. anchored-standard vs eternal-minimal:
   compare task success + cost per preset arm).
2. Review the exp branch diff since last session; recommend promote/hold
   per the two-key rule.
3. Audit: adjudication log contradictions, curation-gate rejections,
   cost-cap hits, judge-calibration reports (use 3 below), disk-health
   counters.
4. Output: a dated entry in `memory/architect-log.md` — decisions
   recommended, evidence cited, SPEC edits proposed. Conrad approves;
   nothing self-executes.

This is the highest-leverage use and it is free of integration work.

## 4. Use 2 — `!escalate <question>` (the scalpel)

Manual command, both surfaces, same plumbing pattern as `!think`:

- `plumbing/escalate.py`: one tool-free call to `claude-fable-5` via the
  Anthropic API. System prompt mirrors think.py's distilled-conclusion
  contract. No history by default (`!escalate` is for questions that stand
  alone); a `--history` flag exists for deliberate exceptions.
- Reply is relayed with the cost printed: `[fable · $0.31]` — every use
  shows its price, keeping the scalpel honest.
- Caps (SPEC §3e2 pattern): $1/call alert threshold, $10/month hard stop —
  the module refuses above it with a one-line message. Usage logged to
  Langfuse like everything else (trace ID = task ID).
- Registry entry (§3g): `!escalate <q>` — one Mythos-class deep answer;
  owner-initiated only; prints cost; disabled without ANTHROPIC_API_KEY.
- NOT a toggle. Escalation-as-a-mode is the slippery slope back to a
  $200/month habit; per-question friction is a feature.

## 5. Use 3 — Judge calibration (trust, quantified)

The cross-family design's blind spot: nothing checks the judge. Weekly,
scheduled (calibrate.timer, same sanctioned class as consolidation):

- `plumbing/calibrate.py`: sample ~20 recent verify judgments from
  Langfuse (candidate + GLM score). Fable re-scores each with the same
  rubric, blind to GLM's score. Report: score correlation, mean absolute
  difference, and the 3 largest disagreements with excerpts.
- Output: `memory/calibration/YYYY-WW.md` + one-line summary in `!status`
  ("judge calibration: r=0.87, last checked <date>"). Reviewed in
  architect sessions. It only reports — never adjusts anything.
- Cost: ~20 short scoring calls/week ≈ $1–2/month.
- Drift response is a HUMAN decision: rubric edit, judge-model swap, or
  accepting the difference — logged in the adjudication log either way.

## 6. Anti-goals (what this module must never become)

- NOT the main window; NOT a router target; NOT a generation tier — the
  no-tiers / no-routing decisions stay closed.
- NOT a verify generator (Vision-Exp-only invariant stands) and NOT the
  standing judge (GLM stays; Fable only audits the judge).
- NOT autonomous: no Fable call without Conrad except the weekly
  calibration sample, which cannot act.
- NOT load-bearing: pulling the API key must leave a complete system.
  Flight test for this: remove the key, run the full test suite + one
  session on each surface — everything green, `!escalate` politely dead.

## 7. Build plan (when approved)

1. SPEC edits: §1 amendment, §2d "Fable module" section (pointer to this
   file), §3g registry entry, §8 note (escalation-tier decision: still
   closed for generation; reopened only as judgment-scalpel).
2. Code: `plumbing/escalate.py`, `plumbing/calibrate.py`, cost-cap lib
   shared between them; `!escalate` wiring in both surface plugins
   (dsh relay pattern / ZCode relay-context pattern).
3. `memory/prompts/architect.md` + empty `memory/architect-log.md`,
   `memory/calibration/`.
4. systemd user timer `calibrate.timer` (weekly, Sunday morning).
5. Tests: escalate.py refuses without key; cap logic; calibrate sampling
   (mocked); registry sync test.
6. Flight tests: `!escalate` on both surfaces with cost line; forced
   over-cap refusal; one manual calibration run; the key-removal test
   in §6. Then exp → main per the two-key rule.

## 8. Open decisions for the owner

- Enable which parts? (Architect practice is free; escalate and calibrate
  each stand alone.)
- Monthly Fable budget cap: proposed $10 hard stop — right number?
- Calibration cadence: weekly proposed; monthly is defensible and cheaper.
- Model pin: `claude-fable-5` vs letting architect sessions choose per
  Anthropic's current lineup (models change; the module should record the
  exact model string per call in Langfuse regardless).
