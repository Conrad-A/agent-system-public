#!/usr/bin/env python3
"""costs — the ledger: usage fields -> $AGENT_RUNTIME/costs.jsonl (SPEC §10).

One row per worker, appended by worker.py when the report is filed, priced
at the rate table in configs/prices.md (editable; peak vs off-peak per
SPEC §2). The dream's `claude -p` runs land as rows too: Max
subscription, so usd 0 — calls and seconds are what get counted.

Usage:  python3 plumbing/costs.py              totals: today · 7 days · all
        python3 plumbing/costs.py --backfill   a row for every filed report not
                                               yet in the ledger — engine workers
                                               from their trajectory when it
                                               exists (the ground truth), else
                                               the report's cost dict
        python3 plumbing/costs.py --rows       every row, one line each

Row: ts (the worker's start — the tier's time), lineage, worker, model,
runtime, preset, data_tier, tier (peak | off-peak | subscription), calls,
input_tokens (whole prompt), cache_read_tokens, cache_miss_tokens,
output_tokens (reasoning included), reasoning_tokens, usd, source, seconds
(dream rows), search_requests + search_usd (step 8: a swarm lane's web
searches, priced from the same file's search table and included in usd).
Never reads a transcript's text: the backfill sums usage fields only.
"""

import json
import re
import sys
import time
from pathlib import Path

import lineage  # noqa: E402
from clients import WORKER_MODEL  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
PRICES = REPO / "configs" / "prices.md"
LEDGER = lineage.RUNTIME / "costs.jsonl"
DSH_HOME = lineage.RUNTIME / "dsh-home"          # engine trajectories (engine.py)
TIERS = ("peak", "off-peak", "subscription")
_SPAN = re.compile(r"(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})")
_EMPTY = {"calls": 0, "input_tokens": 0, "cache_read_tokens": 0,
          "output_tokens": 0, "reasoning_tokens": 0}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ── the rate table ───────────────────────────────────────────────────────────

def rates(path=None) -> dict:
    """configs/prices.md -> {"table": {(model, tier): {cache_hit, cache_miss,
    output}} in USD per 1M tokens, "peak": [(from_min, to_min), ...] UTC
    minutes of the day, weekdays only}."""
    table, peak = {}, []
    for line in Path(path or PRICES).read_text().splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[1] in TIERS:
            try:
                table[(cells[0], cells[1])] = {"cache_hit": float(cells[2]),
                                               "cache_miss": float(cells[3]),
                                               "output": float(cells[4])}
            except ValueError:
                continue
        elif line.lower().startswith("peak hours"):
            peak = [(int(a) * 60 + int(b), int(c) * 60 + int(d))
                    for a, b, c, d in _SPAN.findall(line)]
    if not table:
        raise ValueError(f"no rate rows in {path or PRICES}")
    return {"table": table, "peak": peak}


def search_rates(path=None) -> dict:
    """The web-search table of configs/prices.md -> {(backend, mode): usd per
    request}. The table is the one whose header starts with `backend`."""
    table, in_table = {}, False
    for line in Path(path or PRICES).read_text().splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if not line.strip().startswith("|"):
            in_table = False
            continue
        if cells[0].lower() == "backend":
            in_table = True
            continue
        if in_table and len(cells) >= 3:
            try:
                table[(cells[0].lower(), cells[1].lower())] = float(cells[2]) / 1000
            except ValueError:
                continue                                      # the |---| row
    return table


def search_usage(log_path, r=None) -> dict:
    """A lane's search log (tools/web_search.py: one JSON line per backend
    call) -> {requests, usd, unpriced}; every call counts as a request, an
    errored one too. Missing log = nothing searched."""
    out = {"requests": 0, "usd": 0.0, "unpriced": 0}
    if not log_path or not Path(log_path).exists():
        return out
    r = r if r is not None else search_rates()
    for line in Path(log_path).read_text().splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        out["requests"] += 1
        key = (str(o.get("backend", "")).lower(), str(o.get("backend_mode", "")).lower())
        if key in r:
            out["usd"] = round(out["usd"] + r[key], 6)
        else:
            out["unpriced"] += 1
    return out


def tier(ts: str, r=None) -> str:
    """peak | off-peak for an ISO UTC stamp: Mon-Fri inside a peak span."""
    r = r or rates()
    t = time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    minute = t.tm_hour * 60 + t.tm_min
    if t.tm_wday < 5 and any(a <= minute < b for a, b in r["peak"]):
        return "peak"
    return "off-peak"


def price(model: str, tier_: str, cost: dict, r=None) -> float:
    """USD for a usage dict at (model, tier); KeyError when the table lacks it."""
    r = r or rates()
    if (model, tier_) not in r["table"]:
        raise KeyError(f"no rate for {model} at {tier_} in {PRICES}")
    p = r["table"][(model, tier_)]
    hit = int(cost.get("cache_read_tokens") or 0)
    miss = int(cost.get("input_tokens") or 0) - hit
    out = int(cost.get("output_tokens") or 0)
    return round((hit * p["cache_hit"] + miss * p["cache_miss"] + out * p["output"]) / 1e6, 6)


# ── the ledger ───────────────────────────────────────────────────────────────

def rows() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]


def _append(row: dict) -> dict:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def record_worker(lid: str, wid: str, report: dict, started: str, *,
                  preset=None, source="worker", cost=None, searches=None) -> dict | None:
    """One ledger row for a filed report; None when nothing was billed
    (no calls and no searches). `started` decides the tier; `searches` is
    search_usage() of the worker's search log (swarm lanes)."""
    cost = cost or report.get("cost") or {}
    searches = searches or {"requests": 0, "usd": 0.0}
    if not int(cost.get("calls") or 0) and not searches["requests"]:
        return None
    t = tier(started)
    hit = int(cost.get("cache_read_tokens") or 0)
    row = {"ts": started, "lineage": lid, "worker": wid, "model": WORKER_MODEL,
           "runtime": str(report.get("runtime") or "?"), "preset": preset,
           "data_tier": report.get("data_tier"), "tier": t,
           "calls": int(cost["calls"]),
           "input_tokens": int(cost.get("input_tokens") or 0),
           "cache_read_tokens": hit,
           "cache_miss_tokens": int(cost.get("input_tokens") or 0) - hit,
           "output_tokens": int(cost.get("output_tokens") or 0),
           "reasoning_tokens": int(cost.get("reasoning_tokens") or 0),
           "search_requests": int(searches["requests"]),
           "search_usd": round(float(searches["usd"]), 6),
           "usd": round(price(WORKER_MODEL, t, cost) + float(searches["usd"]), 6),
           "source": source}
    return _append(row)


def record_dream(lid: str, name: str, model: str, seconds: float, rc: int) -> dict:
    """The dream's one `claude -p` call: subscription, usd 0, seconds counted."""
    row = {"ts": _now(), "lineage": lid, "worker": "lead", "model": model,
           "runtime": "claude -p", "preset": None, "data_tier": None,
           "tier": "subscription", "calls": 1, "input_tokens": 0,
           "cache_read_tokens": 0, "cache_miss_tokens": 0, "output_tokens": 0,
           "reasoning_tokens": 0, "usd": 0.0, "source": f"dream {name} exit {rc}",
           "seconds": round(seconds)}
    return _append(row)


# ── backfill from what is on disk ────────────────────────────────────────────

def trajectory_usage(wid: str) -> dict | None:
    """Usage summed over an engine worker's session JSONL (assistant/message
    events only — never the text); None when no trajectory exists."""
    hits = list(DSH_HOME.glob(f"sessions/*/{wid}/session.v3.jsonl")) + \
        list(DSH_HOME.glob(f"sessions-zstd-archive/{wid}/session.v3.jsonl.zstd"))
    if not hits:
        return None
    p = hits[0]
    if p.suffix == ".zstd":
        from compression import zstd            # stdlib since Python 3.14
        text = zstd.decompress(p.read_bytes()).decode(errors="replace")
    else:
        text = p.read_text(errors="replace")
    cost = dict(_EMPTY)
    for line in text.splitlines():
        if '"assistant/message"' not in line:
            continue
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("type") != "assistant/message":
            continue
        u = (o.get("data") or {}).get("usage") or {}
        cached = int(u.get("cacheReadTokens") or 0)
        cost["calls"] += 1
        cost["input_tokens"] += int(u.get("inputTokens") or 0) + cached
        cost["cache_read_tokens"] += cached
        cost["output_tokens"] += int(u.get("outputTokens") or 0)
        cost["reasoning_tokens"] += int(u.get("reasoningTokens") or 0)
    return cost if cost["calls"] else None


def backfill() -> list[dict]:
    """A row for every registry worker with a filed v2 report and no row yet."""
    have = {(r["lineage"], r["worker"]) for r in rows()}
    added = []
    for reg_p in sorted(lineage.LINEAGES.glob("*/registry.json")):
        lid = reg_p.parent.name
        for wid, w in json.loads(reg_p.read_text()).get("workers", {}).items():
            rp = w.get("report_path")
            if (lid, wid) in have or not rp or not Path(rp).exists():
                continue
            report = json.loads(Path(rp).read_text())
            if not isinstance(report.get("cost"), dict):
                continue                                      # v1 report
            cost, source = report["cost"], "backfill:report"
            if str(report.get("runtime", "")).startswith("engine"):
                traj = trajectory_usage(wid)
                if traj:
                    cost, source = traj, "backfill:trajectory"
            row = record_worker(lid, wid, report, w["started"], cost=cost,
                                preset=(w.get("brief") or {}).get("preset"), source=source)
            if row:
                added.append(row)
    return added


# ── the /status line ─────────────────────────────────────────────────────────

def summary_line(now=None) -> str:
    rs = rows()
    if not rs:
        return "cost: no rows yet (ledger empty)"
    now = now or time.time()
    billed = [r for r in rs if r["tier"] != "subscription"]
    today = time.strftime("%Y-%m-%dT00:00:00Z", time.gmtime(now))
    week = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 7 * 86400))

    def part(label, sel):
        return f"{label} ${sum(r['usd'] for r in sel):.4f} ({len(sel)} workers)"
    dreams = [r for r in rs if r["tier"] == "subscription"]
    dream_s = f" · dream {len(dreams)} run(s), {sum(r.get('seconds', 0) for r in dreams) / 60:.0f} min"
    return " · ".join([part("cost: today (UTC)", [r for r in billed if r["ts"] >= today]),
                       part("7d", [r for r in billed if r["ts"] >= week]),
                       part("all", billed)]) + (dream_s if dreams else "")


if __name__ == "__main__":
    if "--backfill" in sys.argv:
        added = backfill()
        for r in added:
            print(f"  + {r['worker']} {r['runtime'].split()[0]:6s} {r['tier']:8s} "
                  f"calls={r['calls']} in={r['input_tokens']} hit={r['cache_read_tokens']} "
                  f"out={r['output_tokens']} ${r['usd']:.6f} [{r['source']}]")
        print(f"backfilled {len(added)} row(s) -> {LEDGER}")
    elif "--rows" in sys.argv:
        for r in rows():
            print(json.dumps(r))
    print(summary_line())
