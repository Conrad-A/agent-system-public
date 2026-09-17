# prices.md — the rate table costs.py prices from (SPEC §10; editable)

USD per 1M tokens. When the provider changes a price, edit the number and
the `checked` date; rows already in `$AGENT_RUNTIME/costs.jsonl` keep the
price they were written at (a ledger is never repriced). Source: the
provider's pricing page, read on the `checked` date.

| model | tier | cache hit | cache miss | output | checked |
|---|---|---|---|---|---|
| deepseek-flash | peak | 0.006 | 0.30 | 1.20 | 2026-09-15 |
| deepseek-flash | off-peak | 0.003 | 0.15 | 0.60 | 2026-09-15 |
| claude-fable-5-1 | subscription | 0 | 0 | 0 | 2026-09-15 |

Peak hours (UTC, Mon–Fri): 01:00–04:00, 06:00–10:00. Every other hour and
the whole weekend are off-peak at half the peak rate (SPEC §2).
costs.py reads the spans from that line; keep its shape.

## Web search (SPEC §7; the sweep spend cap counts requests as well as tokens)

USD per 1k requests, from the vendors' pricing pages read on the `checked`
date. `mode` is the backend's own search mode (what tools/web_search.py
sends). Ten results are included; results past ten cost the `extra` rate
per 1k results (the tool never asks for more than ten).

| backend | mode | usd per 1k requests | extra results per 1k | checked |
|---|---|---|---|---|
| parallel | basic | 5.00 | 1.00 | 2026-09-15 |
| exa | auto | 7.00 | 1.00 | 2026-09-15 |

costs.py prices a lane's search log (one JSON line per backend call) at
these rates; a call that errored still counts as a request.

Rules the ledger applies (costs.py):
- Output includes reasoning: DeepSeek bills reasoning as completion
  tokens and the engine's `outputTokens` already contains `reasoningTokens`.
- Cache miss = whole prompt − cache hit; the runtimes record the whole
  prompt as `input_tokens` and the hit part as `cache_read_tokens`.
- A worker is priced at the tier of its START time (the runtimes sum usage
  without per-call stamps; workers run minutes, not hours).
- `subscription` rows (the dream's `claude -p` on Max) cost $0; the ledger
  counts calls and seconds for them instead.
