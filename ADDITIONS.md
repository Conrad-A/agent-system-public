# ADDITIONS — research on what else belongs in v2

Status: research + recommendation, 2026-09-14. Nothing here is in SPEC yet.
Read SPEC.md first; section numbers below (§4 workers, §5 supervision,
§6 verification, §7 swarm, §8 memory, §10 observability, §16 build order)
refer to it.

Two sweeps were run: (A) the tested-and-true LLM-agent patterns of 2024–2026
— shipped systems, post-mortems, papers with numbers; (B) patterns from other
disciplines with decades of evidence (telecom, SRE, Toyota, aviation,
distributed systems, safety science, science practice, security, accounting).
Vendor-reported numbers are marked. URLs are in §7.

The test applied to every candidate: does it let the system SEE something it
currently cannot, using pieces already in the design — a file, a counter, a
timer, a regex — and does it cost zero novelty tokens (§14)? Everything that
passes is trivial to build. The risk is not any one item; it is adding thirty
of them. §6 therefore names a bounded set for the one-go build and parks the
rest on record.

---

## 1. Where v2 already stands against the evidence

The design was drawn from Fusion, Kimi's swarm, and Anthropic's harness
work. The sweep found independent evidence for each load-bearing choice:

| v2 choice | Evidence |
|---|---|
| Lead = orchestrator, workers via briefs/reports, lead never reads transcripts | Anthropic "Building effective agents" (orchestrator-workers); Anthropic research system (+90% over single agent on research; ~15× tokens); Cognition 2026: subagents that READ work, parallel WRITERS fail |
| No LLM judge; mechanical checker ladder | DeepMind FunSearch/AlphaEvolve — LLM proposes, program scores; production >1 yr, 0.7% of Google fleet recovered. "Reliability without Validity" (2026): LLM-judge agreement overstated by 33–41 points across 21 judges; position bias worst in small cheap models |
| Supervisor trip rules (repeat / stall / budget / stop) | MAST taxonomy (Cemri 2025, 1,600+ traces): step repetition 15.7%, no stopping condition 12.4%, verification failures 23.5% of all failures; adding objective verification +15.6% |
| Swarm ≤5 lanes, depth 1, spend cap | Anthropic: token spend explains ~80% of research-eval variance; explicit effort-scaling rules; "start wide then narrow". Kimi K2.6 300-subagent swarms are the wrong side of that curve for a personal budget |
| Dream on a copy, diff applied by hand | Generative Agents ablation (reflection matters: 29.9 vs 26.9 TrueSkill); every consolidation scheme drifts when nobody reviews it |
| Hooks over prose instructions | Claude Code best practices: CLAUDE.md is advisory and gets ignored when long; hooks are deterministic |
| Plain loop, no framework | AutoGen in maintenance mode (Apr 2026); MetaGPT/ChatDev were the 41–87%-failure systems in MAST; consensus: explicit state + vendor SDK + MCP |

One warning from Cognition applies directly: the setup that failed hardest
was "weak primary, strong assistant" — the weak model couldn't tell when to
escalate. v2 avoids it only because workers never decide to escalate; the
mechanical supervisor decides. Keep that line hard (it shapes the andon rule
in §4).

---

## 2. The seven, kept — with what the research added to each

| # | Addition | Origin | Refinement from the sweep | Slot |
|---|---|---|---|---|
| 1 | Preflight check — SessionStart runs a fixed 10-second brief; key, model id, runtime, tool calls verified against a known answer | Aviation checklists (Gawande: deaths 1.5→0.8%, complications 11→7%) | Verified by the SUPERVISOR (regex on the output), never self-reported by the worker. ≤9 items | step 5 |
| 2 | Canary brief + instrument fingerprint — one fixed brief per day; ledger records the model id the API RETURNS; `/status` flags any change | SRE synthetic monitoring; lab practice of recording the instrument | Pair with Western Electric rule 4 (eight consecutive briefs above the class mean on tokens) — catches drift the canary's exact-match misses | step 7 |
| 3 | Deferrable queue — briefs tagged `deferrable` wait in a directory for the DeepSeek off-peak window | Grid demand-response; HPC batch; Toyota heijunka | Cap the queue depth (Little's law) so the lead can't outrun the checker | step 2/7 |
| 4 | Circuit breaker per brief class — counter file; class stops dispatching past threshold until manual reset | Nygard, *Release It!* | Hysteresis: trip at N failures, re-arm only after M consecutive passes; never one threshold | step 3 |
| 5 | Pre-mortem line + read-back — lead writes "most likely way this fails"; report opens with what the worker understood the task to be | Klein; crew resource management; railway pointing-and-calling (−85% errors) | Add `expect:` (pre-registration, below) as the outcome-side twin | step 2 |
| 6 | Trip → postmortem → eval case — every takeover gets a 5-line postmortem; the brief becomes a regression case | SRE blameless postmortems | Every postmortem ends with ≥1 action item that NAMES A FILE (rule, template, checker) or it's rejected; NASA flight-rules convention: each trip rule cites the postmortem that created it | step 4 |
| 7 | Second-opinion mode — on demand, same coding brief on both runtimes, diff, both through the ladder | N-version programming (flight control) | Unchanged | step 2 |

---

## 3. New candidates from the LLM-agent evidence (sweep A)

**A1. Tight worker interface (ACI).** SWE-agent, same GPT-4: 12.5% vs 1.3%
on SWE-bench from tool design alone. Ablations: lint-on-edit +3pp, capped
search results +6pp, 100-line file window best, collapsing old observations
+3pp. Cheap models are the ones most helped. → Worker edit tool lints on
write and rejects the edit; search/list outputs capped; observations older
than 5 turns collapsed. Slot: step 2, compositions. *Adopt.*

**A2. Feature-list stop condition for long briefs.** Anthropic's long-running
harness: a JSON list of items all starting "failing"; each pass flips one to
passing with a test; premature "done" becomes mechanically impossible. →
Briefs over a size threshold must carry `items:`; the supervisor's finish
rule reads it. Slot: step 3. *Adopt.*

**A3. Max-iterations + "two corrections → restart with a better brief".**
Ralph loop (Anthropic shipped it as a Stop-hook plugin with
`--max-iterations`); Claude Code best practices: after two failed
corrections, `/clear` and re-brief rather than push a third. → Two trip
rules, both counters. Slot: step 3. *Adopt.*

**A4. MAST code on every failure.** Tag each trip/rejection with its MAST
failure mode (FM-1.3 step repetition, FM-3.2 no verification, …). The weekly
architect entry gets a distribution instead of anecdotes. → One column in the
ledger, a 14-line lookup. Slot: step 7. *Adopt.*

**A5. Effort-scaling table in the swarm brief.** Anthropic's rule set: simple
fact → 1 lane, 3–10 calls; comparison → 2–4 lanes; complex → 5+; and the
4×/15× token multipliers as budget defaults. → A table in the swarm brief
template; the decomposability gate already asks the question, this gives it
numbers. Slot: step 8. *Adopt.*

**A6. Perspective lanes, not topic lanes.** STORM's actual mechanism: each
lane researches from a distinct perspective (skeptic, practitioner,
historian…), which is what produced +25% organization / +10% coverage. Its
dominant error was red herrings and source-bias transfer, not hallucination
— which the CONTRADICTIONS section already targets. → A `perspective:` line
per lane brief. Slot: step 8. *Adopt.*

**A7. Library of verified scripts.** Voyager: a skill library of code that
passed verification gave 3.3× items and 15× speed; removing verification
hurt as much as removing the library. → `library/`: worker scripts that
passed the full ladder, filed with their brief, reusable by reference.
Nothing new to build — a directory and a rule. Slot: step 4. *Adopt later,
when the ledger shows repeated briefs.*

**A8. Reflexion only with a real evaluator.** Reflexion's 91% vs 80%
HumanEval came from unit-test feedback; with self-generated critique it
hallucinates. → Confirms the design: worker retries are fed checker output,
never their own assessment. *Already covered.*

Rejected from sweep A: Tree of Thoughts (b^d cost; absorbed into reasoning
models); decentralized handoffs (loses the synthesis point); LLM judge as a
gate in any form (advisory diff comment stays where it is: the optional
self-review pass, default off); framework adoption of any kind.

---

## 4. New candidates from other disciplines (sweep B)

Grouped by which v2 mechanism they extend.

### 4a. Supervision (§5) — the failure governor, unified

The sweep surfaced four retry/stop mechanisms at different time scales. Built
separately they'd be redundant; built as one ladder they are one counters
file and four rules:

| Level | Scale | Rule | Origin |
|---|---|---|---|
| L0 | per API call | Provider 429/5xx only: retry with full jitter, cap 3. Anything else is not transient — trip, don't retry | AWS Brooker 2015 |
| L1 | per brief | Restart intensity: >MaxR restarts in MaxT minutes → stop the lane and ESCALATE to the lead; never retry harder. Briefs are `transient` (retry on error) or `temporary` (research lanes: report failure, no retry) | Erlang/OTP supervisors |
| L2 | per class, hours | Circuit breaker with hysteresis (the seven, #4) | Nygard |
| L3 | per class, weekly | Error budget: SLO on first-pass ladder success per class (e.g. ≥70%) and cost per accepted brief. Budget spent → class demoted to read-only briefs until the weekly entry resets it | Google SRE |

Plus, in the same file:

- **B1. Dead-letter directory.** Briefs that tripped twice go to `dead/` with
  `reason:` and `attempts:`; the weekly entry reviews `dead/`, not the lead at
  trip time. Kills "retry forever" and "quietly forgotten" at once. (Hohpe &
  Woolf 2003.) *Adopt.*
- **B2. Progress-based watchdog kick.** Embedded-systems rule: a hung loop
  that still fires timers looks alive. Stall = no NEW file hash and no new
  ladder rung in T minutes, not "no tool call in T minutes". (Barr Group.)
  *Adopt — a one-line change to the stall rule.*
- **B3. Worker andon: `STOP: <reason>`.** A reserved report line the
  supervisor treats as a trip, not an error. A worker that finds a bad
  premise is rewarded for stopping. Consistent with the Cognition rule: the
  worker doesn't ROUTE, it stops; the supervisor decides. Count pulls per
  class — a class with zero pulls and many ladder failures has workers that
  don't stop. (Toyota jidoka.) *Adopt.*
- **B4. Sterile flag.** During the ladder and during merge, dispatch nothing
  and read no reports; a flag file blocks dispatch. Prevents interleaving a
  new brief into a half-merged tree. (FAR 121.542.) *Adopt.*
- **B5. Sagas: mandatory `undo:` on mutating briefs.** The brief names its
  compensation (`git checkout -- paths` / `git revert`); the supervisor runs
  it on trip, before the postmortem. Workers on a branch per brief make this
  one line. (Garcia-Molina & Salem 1987.) *Adopt.*

### 4b. Brief and report contract (§4)

- **B6. Mission-command headers.** Brief must carry `Purpose`, `End state`
  (how the ladder will know), `Constraints`, `Budget`; `Method: your choice`
  is the default; a `Risk:` line says what the worker may do without asking
  (rewrite a test: yes; add a dependency: no). (ADP 6-0.) *Adopt — this is
  mostly the template v2 implies, made explicit.*
- **B7. Poka-yoke validators.** A regex validator refuses to dispatch a brief
  missing required headers, and refuses to hand the lead a report missing
  required sections. Cheapest defect prevention available. (Shingo.) *Adopt.*
- **B8. `expect:` pre-registration.** Research briefs carry the lead's
  predicted answer; reports put `found:` beside it; the weekly entry counts
  surprises. Calibrates the lead. (Nosek 2018.) *Adopt.*
- **B9. Receipts.** Every claim in a report cites `cmd#N` — the command and
  the first lines of its output, which are in the trajectory. A report with
  uncited claims fails the validator. (Lab-notebook practice; accounting.)
  *Adopt.*
- **B10. `notes_for_eval:` block.** Never parsed for trips, never read by the
  lead mid-session; only the weekly entry reads it. Workers can say "the brief
  was contradictory" without it costing a retry. (NASA ASRS, 500k reports —
  run by NASA precisely because the regulator would chill reporting.) *Adopt.*
- **B11. `domain:` routing line.** Cynefin: clear/complicated → one worker;
  complex → swarm (probes); chaotic → lead does it. The weekly entry can then
  see whether swarms went to complex problems or were wasted on complicated
  ones. *Adopt — one line.*
- **B12. Fencing token.** Dispatch sequence number in the brief, echoed in
  the report; a stale number is discarded. (Kleppmann.) *Later — only matters
  once briefs are re-dispatched automatically.*

### 4c. Verification (§6)

- **B13. Independence of layers.** Swiss-cheese: layers that trust the same
  input are one slice. Rule: the ladder never runs only the tests the worker
  wrote in the same brief — the pre-existing suite always runs too; and the
  diff-review rung never sees the worker's self-summary (strip it first).
  (Reason 1990.) *Adopt.*
- **B14. Four-eyes on the system's own files.** A brief that touches
  `plumbing/supervisor*`, `rules`, checker code or hooks cannot be merged by
  the lead alone; it waits for the weekly entry (the human). (Saltzer &
  Schroeder 1975.) *Adopt.*
- **B15. Near-miss counter.** Briefs that passed only on the last rung, or
  passed after two retries, counted separately. (HRO "preoccupation with
  failure".) *Adopt — one ledger column.*

### 4d. Observability and ledger (§10)

- **B16. Journal as the single source of truth.** `runtime/events.jsonl`
  already exists; make it a write-ahead log: `DISPATCH id class budget`
  BEFORE the call, `DONE id tokens outcome` after. The cost ledger, the
  breaker counters and the weekly entry are folds over the journal, never
  separately mutated files. Crash recovery = read the tail. (ARIES 1992.)
  *Adopt — a unification, not an addition.*
- **B17. Double-entry reconciliation.** Two sides per brief: `budgeted` (from
  the brief) and `spent` (from usage fields). Nightly: sum(spent) vs the
  DeepSeek balance endpoint (`GET /user/balance`) within tolerance; a
  mismatch is a trip on the ledger itself. The only way to notice the ledger
  lying. (Pacioli 1494.) *Adopt.*
- **B18. Control-chart drift rule.** Western Electric rule 4 on
  tokens-per-brief per class (eight consecutive above the mean) — `statistics`
  module, nothing else. *Adopt.*
- **B19. Bulkhead budgets.** Separate token budgets per class AND per swarm
  lane so a runaway research lane cannot starve coding briefs. Log/size caps
  on `board/` and worker output dirs enforced nightly. (Nygard.) *Adopt.*
- **B20. Unread-reports gate.** Theory of Constraints: the constraint is the
  lead's reading time, not worker tokens. Dispatch only when unread reports
  < N. The weekly entry measures where briefs wait longest. *Adopt.*

### 4e. Weekly architect entry (§10)

- **B21. Safety-II sampling.** Each week sample three SUCCESSFUL briefs and
  ask what the worker did that the brief didn't say; deltas become template
  changes. Without this the system only learns from trips. (Hollnagel.)
  *Adopt.*
- **B22. AAR shape for postmortems.** Intended / actual / why / sustain-or-
  improve, plus a five-line "5 whys" block. (US Army AAR; Ohno.) *Adopt as
  the postmortem template.*
- **B23. MAPE-K separation.** Supervisor as three functions — monitor writes
  facts, analyze is pure rules over those facts, execute is the only thing
  with side effects — so the weekly entry can REPLAY analyze over old
  journals when a rule changes. (Kephart & Chess 2003.) *Adopt as a
  structuring rule for supervisor.py.*

### 4f. Swarm (§7)

- **B24. Leveled board.** Hearsay-II: fixed three levels per lane report —
  `evidence:` lines with URLs, `claims:` referencing evidence IDs, `open:`
  unresolved — so synthesis is mechanical. *Adopt as the lane report shape.*

### 4g. Parked (on record, not now)

- Tamper-evident hash chain on the journal — when more than one script
  writes it.
- Content-addressed brief cache (brief hash → prior report) — when identical
  re-dispatches show up in the ledger.
- Least-privilege scratch dirs per brief — belongs with the data-tier rule
  (§9), which is dormant.
- Library of verified scripts (A7) — when repeats appear.
- OODA, 12-factor, Unix philosophy, kanban WIP beyond the ≤5 lanes — already
  covered by existing rules; nothing to build.

---

## 5. Counting the cost

Everything marked *adopt* is a header, a regex, a counter, a column, or a
timer. Zero new dependencies; zero novelty tokens. But there are ~35 of them,
and each is a line in a template, a rule in a file, and a test. The build
order absorbs them only if they are grouped per step, so:

| Step | Additions folded in |
|---|---|
| 2 Workers | brief/report template (B6, B7, B8, B9, B10, B11, pre-mortem/read-back), ACI (A1), second-opinion (7), deferrable tag (3) |
| 3 Supervision | governor ladder L0–L3 (incl. breaker 4), B1 dead-letter, B2 progress kick, B3 andon, B4 sterile, B5 undo, A2 items, A3 max-iter/two-corrections, B23 structure |
| 4 Checker | B13 independence, B14 four-eyes, B15 near-miss, postmortem→eval (6) with B22 template |
| 5 Hooks | preflight (1) |
| 7 Ledger | B16 journal-as-truth, B17 reconciliation, B18 drift, B19 bulkheads, B20 unread gate, A4 MAST codes, canary+fingerprint (2), deferrable timer (3) |
| 8 Swarm | A5 effort table, A6 perspectives, B24 leveled board |
| weekly | B21 Safety-II sampling |

Each step's flight test grows by one or two lines. Nothing changes in the
step order or in what must be green before promotion.

---

## 6. Recommendation

Put into SPEC for the one-go build: the seven, plus everything marked
*adopt* in §3 and §4 — as amendments to the sections they belong to, not a
bolt-on section — and grow the KICKOFF flight tests accordingly. Three
things to hold onto while doing that:

1. **One governor, not four.** L0–L3 plus dead-letter live in one counters
   file with one reader. If it turns into four modules, it failed the boring
   rule.
2. **The journal is the truth.** Ledger, breaker state, canary history,
   near-miss counts, MAST distribution — all folds over `events.jsonl`. No
   second mutable state file.
3. **Templates before mechanisms.** Most of the value in §4b is the brief and
   report shape. Write those two templates first (step 2), with the validator;
   the supervisor and ledger rules then read fields that already exist.

Parked items stay in §4g with their triggers. The weekly entry is where they
get promoted.

---

## 7. Sources

Sweep A (LLM agents)
- Anthropic, Building effective agents (2024) — https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, How we built our multi-agent research system (2025) — https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic, Effective context engineering (2025) — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic, Effective harnesses for long-running agents (2025) — https://anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic, Writing tools for agents (2025) — https://www.anthropic.com/engineering/writing-tools-for-agents
- Anthropic, Demystifying evals for AI agents — https://anthropic.com/engineering/demystifying-evals-for-ai-agents
- Claude Code best practices — https://code.claude.com/docs/en/best-practices
- Cognition, Don't build multi-agents (2025) — https://cognition.com/blog/dont-build-multi-agents
- Cognition, Multi-agents: what's actually working (2026) — https://cognition.com/blog/multi-agents-working
- OpenAI, A practical guide to building agents (2025) — https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
- Cemri et al., Why do multi-agent LLM systems fail? (2025) — https://arxiv.org/abs/2503.13657
- DeepMind, FunSearch (2023) — https://deepmind.google/blog/funsearch-making-new-discoveries-in-mathematical-sciences-using-large-language-models/
- DeepMind, AlphaEvolve (2025) — https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/
- Reliability without validity (LLM judges, 2026) — https://arxiv.org/html/2606.19544v1
- Self-preference bias in LLM-as-a-judge (2024) — https://arxiv.org/abs/2410.21819
- SWE-agent (2024) — https://www.alphaxiv.org/overview/2405.15793
- Huntley, Ralph — https://ghuntley.com/ralph/ ; Anthropic ralph-wiggum plugin — https://github.com/anthropics/claude-code/blob/main/plugins/ralph-wiggum/README.md
- Park et al., Generative Agents (2023) — https://arxiv.org/html/2304.03442
- MemGPT (2023) — https://ar5iv.labs.arxiv.org/html/2310.08560 ; Voyager (2023) — https://voyager.minedojo.org/
- Reflexion (2023) — https://arxiv.org/abs/2303.11366 ; Weng, LLM-powered autonomous agents — https://lilianweng.github.io/posts/2023-06-23-agent/
- STORM (Stanford) — https://storm-project.stanford.edu/research/storm/
- Kimi agent swarm docs — https://github.com/MoonshotAI/kimi-help-center/blob/master/en-US/agent/swarm.md (vendor-reported)
- Framework landscape 2026 — https://dev.to/gabrielanhaia/crewai-vs-autogen-vs-the-rest-the-2026-multi-agent-framework-landscape-14hb ; https://pearpages.com/blog/2026/07/24/from-agent-loops-to-agent-graphs

Sweep B (other disciplines)
- Erlang/OTP supervisor principles — https://www.erlang.org/doc/system/sup_princ.html
- Kephart & Chess, The vision of autonomic computing (2003) — https://jmvidal.cse.sc.edu/lib/kephart03a.html
- Nii, The blackboard model of problem solving (1986) — https://dl.acm.org/doi/10.1609/aimag.v7i2.537
- US Army ADP 6-0 Mission Command — https://www.armypubs.org/adp-6-0-mission-command-command-and-control-of-army-forces/
- Google SRE book, Embracing risk — https://sre.google/sre-book/embracing-risk/ ; SRE workbook, Postmortem culture — https://sre.google/workbook/postmortem-culture/
- Toyota, Jidoka — https://mag.toyota.co.uk/jidoka-toyota-production-system/ ; TPS — https://global.toyota/en/company/vision-and-philosophy/production-system/index.html
- Nygard, Release It! (2nd ed.) — https://pragprog.com/titles/mnee2/release-it-second-edition/
- Hohpe & Woolf, Dead letter channel — https://www.enterpriseintegrationpatterns.com/patterns/messaging/DeadLetterChannel.html
- Brooker, Exponential backoff and jitter (2015) — https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- Garcia-Molina & Salem, Sagas (1987) — https://dl.acm.org/doi/10.1145/38713.38742
- Haynes et al., surgical safety checklist (2009) — https://news.harvard.edu/gazette/story/2009/01/surgical-safety-checklist-drops-deaths-and-complications-by-more-than-one-third/
- Hollnagel, From Safety-I to Safety-II (2013) — https://skybrary.aero/sites/default/files/bookshelf/2437.pdf
- Weick & Sutcliffe, HRO principles — https://www.high-reliability.org/the-five-principles-of-weick-sutcliffe
- Reason, Human error: models and management (2000) — https://psnet.ahrq.gov/issue/human-error-models-and-management
- Nosek et al., The preregistration revolution (2018) — https://www.pnas.org/doi/10.1073/pnas.1708274114
- Saltzer & Schroeder, The protection of information in computer systems (1975) — https://www.cs.virginia.edu/~evans/cs551/saltzer/
- Crosby & Wallach, Tamper-evident logging (2009) — https://static.usenix.org/event/sec09/tech/full_papers/crosby.pdf
- Barr Group, Introduction to watchdog timers — https://barrgroup.com/blog/introduction-watchdog-timers
- Pointing and calling (RTRI 1994) — https://en.wikipedia.org/wiki/Pointing_and_calling
- Sterile flight deck, FAR 121.542 — https://skybrary.aero/articles/sterile-flight-deck
- NASA ASRS, the case for confidential incident reporting — https://asrs.arc.nasa.gov/docs/rs/60_Case_for_Confidential_Incident_Reporting.pdf
- Western Electric rules — https://en.wikipedia.org/wiki/Western_Electric_rules
- Snowden & Boone, A leader's framework for decision making (2007) — https://hbr.org/2007/11/a-leaders-framework-for-decision-making
- Goldratt, Theory of Constraints — http://www.scholarpedia.org/article/Theory_of_Constraints
- Bazel, Hermeticity — https://bazel.build/basics/hermeticity
- Pacioli, Summa (1494), Geijsbeek translation — https://archive.org/details/ancientdoubleent00geij
