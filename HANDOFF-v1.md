# HANDOFF — session continuity file (updated 2026-09-14; v1 body below from 2026-09-04)

## 2026-09-14 — v2 DESIGNED, NOT YET BUILT. Start here.

- The v1 system below no longer runs: Linux was reinstalled ~09-07; the
  Desktop folders are the backup. Nothing v1 is live on this host.
- v2 = Claude Code (Fable 5.1) as the lead, DeepSeek V4.1 Flash workers
  (`deepseek-flash`) in the dsh engine or a plain loop, mechanical
  supervisor + checker ladder, swarm mode, nightly dream on a copy. The
  design is `SPEC.md` (wins every conflict); `MIGRATION.md` maps v1
  files to v2; `KICKOFF.md` is the build prompt (Linux + macOS blocks);
  `memory/prompts/dream.md` is the nightly prompt. `ADDITIONS.md` is
  research on record, nothing from it is in the spec. `OWNER-NOTES.md`
  and `DOMAINS-owner.md` are owner-only, not part of the kit.
- All of it is committed on `exp/v2` and pushed to `backup` (head
  2ce8ecc). Three cold review passes were run on SPEC today; the last
  scoped pass converged. Decisions of the day are in the spec with
  "(Conrad, 2026-09-14)" markers — rotation numbers (lead 100k/128k,
  workers 26k/32k), lineage commands dropped, hooks as §14 item 4.
- NEXT: open Claude Code in this directory and paste the Linux block from
  `KICKOFF.md`. Step 1 rewrites this file for v2 (keep this one as
  `HANDOFF-v1.md`). When the prompt reaches "rotate the PAT": done
  2026-09-14, lives in `~/.git-credentials`.
- Owner chores, not build steps: delete `~/Desktop/_to_delete/` and the
  four scratch files on the Desktop (`rotation.diff`, `*.current.md`);
  rule by hand on the two v1 proposal files in `runtime/` at step 6; the
  RAM is due for replacement (the drive is fine).
- The v1 open items below are history: superseded by MIGRATION.md.

---

# v1 HANDOFF (2026-09-04) — history only

For the next working session (human or AI): read this, then SPEC-v3.1.md, then
whatever the task needs. Decision-relevant compression of where things
stand; history lives in git and memory/.

## System status: COMPLETE and live

Every SPEC layer is deployed and flight-tested on the Fedora 44 host as of
2026-09-01. Both surfaces (dsh + ZCode) run the full `!` command registry;
verifier runs CROSS mode with real score spread; Langfuse traces
everything; consolidation timer runs nightly 19:45; three access layers
work from anywhere (tailnet web via https://dsh.YOUR-DOMAIN:3080,
Sunshine/Moonlight, Signal watchdog on +1BOTNUMBER — `status` answered
end-to-end). Genome mirrors to the private GitHub remote `backup`
(github.com/YOUR-GITHUB-USER/agent-system) — push after every meaningful commit.
Current head at handoff: FABLE MODULE phases 0-6 all built and
flight-tested on exp/fable-max (2026-09-03/04) — see open item 1;
promotion to main awaits soak + the first architect session.

## Document map (what to read when)

- `SPEC-v3.1.md` — canonical design; wins every conflict. §8 = open decisions.
- `FIELD-NOTES.md` — deployment ground truth + §0 replication kickoff
  prompt. Read before touching infra; every layer's failure signatures.
- `OPERATIONS.md` — daily/weekly command cheat sheet (health check,
  timer, Signal, certs, tests, disk watch).
- `FABLE-MODULE.md` + `FABLE-MODULE-MAX.md` — original proposals, now
  BUILT AND EXCEEDED (2026-09-03/04): the no-Claude rule was removed and
  the full phase 0-6 plan (incl. verify arm + throne, overriding two
  anti-goals) shipped on exp/fable-max. SPEC-v3.1 §2d is the living contract;
  read these two files as design history. `CLAUDE.md` +
  `memory/prompts/{throne,architect}.md` are the operating docs.
- `agent-system-blueprint.md` / `agent-system-diagram.html` — narrative +
  visual; synced through review round 2.
- `memory/facts.md` — the build diary; newest entries cover infra final
  shape, disk suspicion, milestone.
- Share artifacts: `../agent-system-v1.0.zip` (clean, no secrets) +
  GitHub collaborator invites for update-tracking peers.

## Open items (all of them)

1. FABLE module: DECIDED 2026-09-03 — no-Claude rule removed by Conrad;
   FULL phase 0–6 plan approved (incl. verify-arm + throne, overriding
   those two anti-goals); transport = Claude Code CLI under the Max sub,
   API key as fallback flag only. SPEC-v3.1 §2d is the contract. Phase 0
   (governance) DONE on exp/fable-max. Phase 1 DONE + FLIGHT-TESTED
   2026-09-03: fable.py (claude -p transport, model claude-fable-5-1 —
   hyphens, dotted form silently falls back — rate cap, log.jsonl) +
   escalate.py; `!escalate` on both surfaces; fable line in !status;
   22 tests green; CLI 2.1.259 recorded in configs/experimental.md.
   Phase 2 BUILT 2026-09-04: judgment ledger (verify.py appends per-scored
   candidate to runtime/verify/judgments.jsonl via calibrate.record_judgment),
   calibrate.py (blind Fable rescore, r/mad/top-3 disagreements report to
   memory/calibration/ + latest.json in !status), `!calibrate` on both
   surfaces, systemd/calibrate.{service,timer} (install: OPERATIONS.md),
   calibration calls exempt from the escalate cap; 26 tests green.
   Phase 2 FLIGHT-TESTED 2026-09-04: live calibration run n=20, mad=0.15,
   r=n/a (zero GLM score variance on softball prompts — expected; real
   traffic will spread), escalate cap untouched by 20 calibration calls.
   Owner still to install calibrate.timer (OPERATIONS.md). During the
   flight test: Langfuse ClickHouse corruption found + fixed (see open
   item 3 — drive verdict now REPLACE).
   Phase 3 FLIGHT-TESTED 2026-09-04: flag flipped ON in .env; live
   CROSS+FAM run with 6 scores, winner_from=deepseek (expected on easy
   tasks — the arm is blind-spot insurance), arm cap 1/20, escalate 0/10
   untouched. Watch winner_from rates in the ledger as architect-session
   evidence. dsh restart still needed for the surfaces to see the flag.
   CO-JUDGE BUILT 2026-09-04 (flag VERIFY_COJUDGE, default off): DeepSeek
   scores each candidate as a true logprob expectation, averaged 50/50
   with GLM; mode +CJ; ledger keeps pure GLM (+ds_score column) so
   calibration still audits the standing judge; paper-fidelity upgrades
   beyond this (granularity, criteria decomposition, ring-pairwise+BT)
   deferred to eval per SPEC-v3.1 §3 note. Co-judge FLIGHT-TESTED 2026-09-04
   after one bug fix (Vision-Exp thinks by default — see facts.md): task
   f41f5f69 scored glm 7.33 / ds 7.91, six candidates spread 7.62-8.25
   (real score variance at last — calibration r becomes meaningful).
   VERIFIER WORK COMPLETE. Phase 4 DONE + FLIGHT-TESTED 2026-09-04: Fable
   writes rotation handoffs + !retie merge reports (CONTRADICTIONS
   section); THREE discovery misses fixed en route (stats dotfile,
   node_modules package.json, preset template) — final shape: content
   sniff + path filters + DSH_SESSION_DIR pin (= ~/.dsh/sessions,
   .jsonl.zstd, decompression built in) + state.prev.md backup before
   every overwrite. Live test distilled a real session; the handoff
   itself found two bugs we fixed: relay no longer claims VERIFIED
   OUTPUT on plumbing failure (both surfaces), and memory/archives/ +
   runtime/ are now gitignored per the §7 genome/body boundary
   (rotation-log.md untracked). Open from that handoff: dsh first-turn
   'prepareCall is not a function' race (reproduce with !verify on as
   first command on a fresh window). Phase 5 BUILT 2026-09-04:
   consolidate._propose delegates to Fable (author stamped in proposals
   header, kind=consolidation, add-only fallback, propose-only intact).
   FLIGHT-TESTED 2026-09-04: live pass, confidence-tagged proposals, flagged its own junk inputs (archives 0135/0139 from the bad rotations — owner may delete them).
   GATE 2026-09-04: first procedure promoted (input-side-first, in
   procedures.md); other proposals left for Conrad's own pass.
   Phase 6 BUILT 2026-09-04: throne charter (memory/prompts/throne.md),
   repo CLAUDE.md (engineer/throne/architect roles), architect agenda +
   empty log, SPEC-v3.1 §3c FABLE THRONE rules (32k-exempt, state-discipline
   bound, DeepSeek fallback). FLIGHT TEST = open Claude Code in the repo,
   say the kickoff line, claim the throne (lineage_cmd throne
   claude-main), confirm in !status. FLIGHT-TESTED 2026-09-04: throne
   claimed as claude-main under NEW lineage 20260904-a25b9c (deliberately
   did not take over dsh-main's lineage — retie is Conrad's call), state
   file written, and the session found + reported the suite's
   DSH_SESSION_DIR hermeticity leak (fixed same day, engineer session).
   ALL PHASES 0-6 BUILT AND FLIGHT-TESTED. Remaining before promotion to
   main: owner chores (calibrate.timer install, dsh restart for the arm
   flag, vaultwarden, DRIVE REPLACEMENT), a soak period accumulating
   winner_from + calibration evidence, then the FIRST ARCHITECT SESSION
   reviews exp/fable-max and recommends promote/hold (two-key rule).
   Open gate items: remaining 2026-09-04 consolidation proposals; retie
   claude-main ↔ dsh-main lineages or keep separate. Still defaulted:
   caps, Sun 09:00 calibration, architect day TBD. ALSO 2026-09-04: verify N settings on=8/max=16 + parallel judging (owner decision after full paper read); eval row registered mentally: 8+1 vs 16+1 winner_from rates. FLIGHT-TESTED: 17 candidates in 38s (task b8cb1df2, correct answer, one 4.38 outlier correctly punished); chat-surface half (dsh restart, !verify max) still owner-side.
2. First weekly ARCHITECT SESSION once ~a week of Langfuse traces exists:
   agenda in FABLE-MODULE §3 — close a SPEC-v3.1 §8 decision with evidence
   (anchored-standard vs eternal-minimal is the ripest).
3. Hardware — CORRECTED 2026-09-14 (Conrad): the drive was never failing;
   the "replace the drive" verdict is withdrawn. It is the RAM that needs
   replacing (owner chore). Also: vaultwarden container Exited(12) ~7 days
   — restart it.
4. Consolidation timer: nudge 19:45→19:15 when EDT→EST (November) to stay
   in DeepSeek's off-peak window.
5. Watchdog stubs: `restart zcode` targets a unit that doesn't exist;
   `reboot`/`vpn up` need polkit/sudoers before they work remotely.
6. dsh-signal-channel plugin: scaffolded (plugins/dsh-signal-channel,
   UNTESTED banner, 6 TODO(verify-on-dsh) markers) — first live test
   pending appetite.
7. SPEC-v3.1 §8 design decisions: role split between stacks; preset eval;
   eval-task accumulation; dshx gateway only if eternal-minimal wins.
8. GitHub PAT used for `backup` was exposed in a chat once; owner chose to
   keep it — flagged for the next key-rotation pass (SPEC-v3.1 §6b).
9. Math + quant capability modules: specs registered, zero code — future
   domain onboarding per SPEC-v3.1 §2c.

## Working agreements (learned, non-negotiable)

- One layer/change at a time; flight-test before moving on; commit + push
  `backup` (current branch) after each meaningful change; run
  `plumbing/tests/run_tests.py` (38 tests as of 2026-09-04) before
  promoting anything.
- Paste-safe commands: no line-continuation backslashes; single-quote
  anything with `!`; placeholders clearly marked (prefixes included in
  pasted values).
- Sandbox sessions leave `.git/*.lock` files — owner runs
  `rm -f .git/*.lock` before committing locally.
- Keep the three doc surfaces in sync (SPEC, diagram HTML, blueprint) and
  append hard-won facts to memory/facts.md as they land.
- Credentials never in chat; anything that lands there gets rotated;
  minimum scopes always.
- Autonomy principle: nothing executes without the owner except nightly
  consolidation and (if built) weekly calibration — both report-only.

## Kickoff line for a fresh session

"Read HANDOFF.md, then SPEC-v3.1.md; the repo is at ~/Desktop/'Project 2'/
agent-system on the Fedora host (bash may see it under a mounted path).
Continue from the open items above; confirm which one before acting."
