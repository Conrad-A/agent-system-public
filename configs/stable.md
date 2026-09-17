# Stable build config — v2 pins (SPEC §2, §4.2, §14)

Exact strings with the date they were recorded. Never pin an alias. Bump
only on an `exp/` branch: suite green, one live worker on EACH runtime,
then commit (SPEC §4.2). `claude` bumps follow the same path (§11).

| Role | Pin | Recorded | Notes |
|---|---|---|---|
| LEAD | `claude-fable-5-1` (auto-fallback `claude-fable-5`) | 2026-09-14 | Claude Code interactive session in this repo, Max subscription. Hyphens, never a dotted form (the dotted string is rejected and silently falls back). `claude -p` only for the nightly dream. |
| Claude Code CLI | `2.1.272` | 2026-09-14 | `claude --version`. It auto-updated from 2.1.271 between steps 1 and 2; `DISABLE_AUTOUPDATER=1` is set on this host (Conrad, 2026-09-14) so the pin holds from here — bumps go through the §11 path. `claude auth status` reports `subscriptionType: max`. The `Monitor` tool exists in this version (the step 3 wake). |
| WORKER (the only worker model) | `deepseek-flash` (DeepSeek V4.1 Flash, released 2026-09-10) | 2026-09-14 | `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` are temporary aliases routing to V4.1 — never pin them. `deepseek-v4-pro` retired 2026-09-14 (routes to Flash). |
| Worker ENGINE SDK | `deepseek-harness-sdk==0.1.5rc1` | 2026-09-14 | Installed with `python3 -m pip install --user`; pulls `deepseek-harness-runtime-bin==0.1.5rc1` (the bundled runtime binary, manylinux x86_64) and `pydantic` (2.13.5 landed). EVERY SDK RELEASE TO DATE IS A PRE-RELEASE (rc / alpha; 0.1.5rc1 is the newest, 2026-09-10). SPEC §14 item 1 already rates the engine rc-grade; the plain-loop fallback and this exact pin are what pay for it. |
| Python | `3.14.7` (host `/usr/bin/python3`) | 2026-09-14 | ≥ 3.10 required. pip was bootstrapped with `python3 -m ensurepip --user` (Fedora ships no pip by default). |

DeepSeek V4.1 quirks that bind every worker call (confirmed 2026-09-14; the
full list is SPEC §2 and FIELD-NOTES.md):
- thinking via `reasoning_effort` low/high/max + `thinking: {type: enabled|disabled}`;
- with `tools` present, `reasoning_content` is replayed on EVERY later request;
- thinking mode ignores temperature and floors `top_p` at 0.95;
- thinking tokens count against `max_tokens` — use ≥ 16384;
- Mon–Fri 01:00–04:00 and 06:00–10:00 UTC are PEAK at full price; every other hour and the weekend are off-peak at half (rates: configs/prices.md).

Presets: `think` / `minimal` / `standard` (SPEC §4.4) — a COGNITION knob
on V4.1, per the step-2 CoT flight test below; §4.4 stands as three presets.

CoT FLIGHT TEST ON V4.1 (step 2, 2026-09-14): one fizzbuzz brief (write a
module + a test, run it), `reasoning_effort=max` on both, one trajectory per
preset read once. The v1 split SURVIVES and is stark:
- `minimal` (sdk-minimal, persistent bash only): a `reasoning` block on
  EVERY call — the clipped "We/Let's" chain ("We need act. Need work only
  inside given dir… Let's use bash pwd/ls… We'll cd to path?… Let's
  execute."), 519 and 536 chars on the first two calls, 132 and 151
  reasoning tokens; 4 calls, 3 tool steps, test passed.
- `standard` (sdk, wide catalog): reasoningTokens 0 on the first two calls
  — NO reasoning block at all — narrated in visible text instead ("I'll
  create both files and run the test."), one 5-token "Done. Test passes."
  at the end; 3 calls, 3 tool steps, test passed. The catalog costs about
  seven times the prompt on call 1 (5989 vs 825 input tokens).
- Same thinking setting on both (checked 2026-09-14 in the `request/header`
  events): `reasoningEffort: max`, `maxTokens: 16384`, same model and
  provider; the only difference between the two requests is the tool
  catalog (1 tool vs 21). The catalog alone flips the reasoning off.
- Sample size: one brief per preset; the minimal-preset probe run showed the
  same deep chain (4.7k output tokens deliberating a scope conflict before
  asking back). Re-check on a harder brief once the cost ledger has data.

History: the v1 stable config (two stacks, GLM as the verifier, dsh
0.1.1-rc.2, the no-Claude rule) is in git history on `exp/fable-max`.
