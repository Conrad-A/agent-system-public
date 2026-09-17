# FABLE MODULE under a Max subscription — amendment (2026-09-01; STATUS
# 2026-09-04: BUILT — transport is this file's claude -p design; SPEC §2d
# is the living contract, this file is design history)

Read `FABLE-MODULE.md` first; this file changes it given the new fact:
the owner holds a Claude Max subscription ($200/mo flat). That flips the
economics of every Fable use from "metered scalpel" to "sunk cost —
extract value," without changing a single anti-goal.

## 1. What the subscription actually covers (and doesn't)

- Covers: Claude apps — claude.ai, Claude Code (CLI on the desktop), and
  Cowork-style sessions — at flat rate within generous usage limits.
- Does NOT cover: raw Anthropic API calls. Any plumbing that hits the API
  directly still bills per token on a separate meter.
- Consequence: the module's transport changes. Prefer **Claude Code in
  headless mode** (`claude -p "question"`) — Fable on this machine, billed
  to the subscription — with the raw API as optional fallback only.
  Caveat honestly: subscriptions carry fair-use/rate limits; scalpel-grade
  automation is fine, grinding agent workloads through it is not (and
  would violate the anti-goals anyway).

## 2. Revised use 1 — Architect sessions: from monthly to STANDING

The biggest change. At zero marginal cost, the architect practice stops
being a monthly luxury:

- WEEKLY architect session (Cowork/claude.ai with the repo attached),
  agenda unchanged from FABLE-MODULE §3, plus: review the week's
  consolidation proposals and calibration report.
- Build rounds return: exp-branch features, plugin work, doc maintenance
  run as Fable sessions like the original build did. The genome's author
  stays its editor. Two-key rule unchanged — Fable proposes and writes on
  exp; Conrad promotes.
- This session pattern IS the precedent: the entire system was built this
  way on the subscription's predecessor.

## 3. Revised use 2 — `!escalate` at flat rate

- `plumbing/escalate.py` transport becomes: shell out to
  `claude -p --model claude-fable-5 "<distilled-conclusion prompt>"`,
  which bills the subscription. No per-call dollar anxiety.
- The cost line in the reply changes meaning: print latency + the model
  string instead of dollars (`[fable · claude-fable-5 · 41s]`).
- The $10 hard-stop cap is replaced by a RATE cap: default 10 calls/day —
  not for money now, but to protect the design (per-question friction is
  what keeps escalation a scalpel; see anti-goals) and stay well inside
  subscription fair use.
- Still owner-initiated only. Still NOT a toggle. Same registry entry.

## 4. Revised use 3 — Calibration: weekly, without the meter

- `plumbing/calibrate.py` uses the same `claude -p` transport; the ~$1-2
  monthly API cost disappears. Weekly cadence confirmed (was the
  cost-cautious question; the caution is moot).
- Optionally deepen: sample 30 judgments instead of 20, and add a monthly
  "judge the generator" pass — Fable reviews 10 verify WINNERS for
  quality, auditing the whole pipeline rather than only the judge.

## 5. New use 4 — Claude Code as the MAINTENANCE harness (new, Max-only)

Install Claude Code on the Fedora box, authenticated to the subscription.
Role: the workshop, never the factory floor —

- Upgrades, migrations, incident response (e.g. the next Safari-grade
  saga) run as Claude Code sessions in the repo with full tool access —
  what the original build did through Cowork, now native on the machine.
- Explicitly NOT a third runtime surface: no `!` router plugin for it, no
  place in the session-mechanics layer, not in the two-stack identity.
  DeepSeek + GLM remain the system; Fable remains its engineer.
- Practical note: it is also the escalate/calibrate transport binary, so
  installing it is step 1 of the build plan.

## 6. Unchanged — every anti-goal, verbatim

Not the main window; not a router target; not a generation tier; not a
verify generator or standing judge; not autonomous beyond the calibration
sample; not load-bearing. The load-bearing flight test tightens: with
Claude Code logged out AND no API key, full test suite + both surfaces
green, `!escalate` politely dead. A lapsed subscription must cost the
system nothing but its scalpel.

The replication kit also stays Claude-free: both FABLE files ship as
optional reading; a replicator without any Anthropic account builds the
identical core system.

## 7. Honest thoughts section (the part the owner asked for)

The owner's own earlier verdict was that $200/mo is poor value against
DeepSeek-priced tokens — and that verdict was CORRECT for token-grinding,
which is why the runtime stays DeepSeek/GLM. The subscription justifies
itself only one way: used deliberately as the system's judgment layer and
standing engineer — weekly architect sessions that actually close §8
decisions with Langfuse evidence, build rounds that keep the exp branch
moving, calibration that keeps the judge honest. Used that way, the sub
is the salary of the system's architect while marginal runtime costs stay
near zero. Left idle as a chat toy, it is exactly the scam price the
owner once called it. The system now has the instrumentation to tell
which one is happening: if two consecutive architect logs are empty, the
honest move is to cancel again — this file is designed to survive that.

## 8. Build plan deltas (on top of FABLE-MODULE §7)

1. Install Claude Code on the host; verify `claude -p "ping"` answers on
   subscription auth. Record the version in configs/stable.md.
2. escalate.py/calibrate.py call the CLI (subprocess) instead of the API;
   API-key path kept behind a flag as fallback.
3. Rate-cap lib (calls/day) replaces the dollar-cap lib.
4. `memory/architect-log.md` gains a standing WEEKLY entry template; add
   a calendar reminder or scheduled Cowork task for the session — the
   sub only pays for itself if this actually happens.
5. Flight tests: FABLE-MODULE §7 set, plus the logged-out test in §6, plus
   one full weekly architect session executed end-to-end as the acceptance
   test of the whole module.

## 9. Open decisions (revised)

- Escalate rate cap: 10/day proposed.
- Architect cadence: weekly proposed; commit to a fixed day.
- Enable use 4's incident-response role now, or after the first month's
  architect logs prove the rhythm sticks?
- Keep the API-key fallback path at all, or subscription-only transport?
