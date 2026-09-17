# Experimental build config (exp/* branches)

## Current experiment: the v2 build on `exp/v2` (started 2026-09-14)

| Piece | Detail |
|---|---|
| Branch | `exp/v2` |
| What differs from stable | everything: v2 replaces the v1 system (design `SPEC.md`, file map `MIGRATION.md`, build order `KICKOFF.md`) |
| Pins under test | the table in `configs/stable.md` (recorded at step 1; v2 has no separate stable yet) |
| Gate | each step's flight test + `python3 plumbing/tests/run_tests.py` green before the next step |
| Promotion | DONE 2026-09-16 after step 8's flight test: `SPEC-v2.md` → `SPEC.md`, the v1 spec → `SPEC-v3.1.md`; MERGED to `main` 2026-09-16 (fast-forward at 153ccd4, suite green on main, pushed); work continues on main |

## Template for the next experiment

| Piece | Detail |
|---|---|
| Model / pin | |
| Runtime / harness | |
| Hypothesis | |
| Eval | `evals/` tasks, outcome-graded; pass^k is the bar for `main` (SPEC §12) |
| Decision date | |
| Result | |
