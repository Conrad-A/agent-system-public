#!/usr/bin/env python3
"""status — the visibility surface (SPEC §5.2, §10).

Prints the current git build, the runtime path, every lineage with its
workers in flight and any timed-out workers, and the most recent reports.
Reads the shared runtime conventions from lineage.py.

Grows with the build: step 2 adds `waiting` workers, the runtime stamp
(engine / plain, fallback reason) and the permission mode; step 5 adds
`--line`, the one-line form the UserPromptSubmit hook prints (lead context
size, state.md age, one line per running worker); step 7 adds the cost line
(costs.py: today · 7 days · all, from $AGENT_RUNTIME/costs.jsonl).
"""

import json
import subprocess
import sys
from pathlib import Path

import costs  # noqa: E402
import swarm  # noqa: E402
from lineage import LINEAGES, RUNTIME, in_flight, sweep_timeouts, waiting, worker_entry  # noqa: E402


def main() -> None:
    print("=== agent-system status ===")
    repo = Path(__file__).resolve().parents[1]
    head = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%h %s"],
                          capture_output=True, text=True).stdout.strip()
    branch = subprocess.run(["git", "-C", str(repo), "branch", "--show-current"],
                            capture_output=True, text=True).stdout.strip()
    print(f"build: {branch} @ {head}")
    print(f"runtime: {RUNTIME}")

    if LINEAGES.exists():
        # lineages/ also holds index.json (directory -> lineage id); skip files
        for ld in sorted(p for p in LINEAGES.iterdir() if p.is_dir()):
            lid = ld.name
            timed_out = sweep_timeouts(lid)
            flight, asks = in_flight(lid), waiting(lid)
            meta = json.loads((ld / "meta.json").read_text()) if (ld / "meta.json").exists() else {}
            where = meta.get("project_dir") or meta.get("throne_window") or "?"
            print(f"lineage {lid} ({where}): in-flight={len(flight)} waiting={len(asks)}")
            for wid, goal in flight.items():   # [runtime] as stamped at start (run-5 ruling)
                rt = (worker_entry(lid, wid) or {}).get("runtime") or "?"
                print(f"  · {wid} [{rt}]: {goal[:60]}")
            for wid, q in asks.items():
                print(f"  ? {wid} WAITING — {q[:100]}")
            for wid in timed_out:
                print(f"  ! {wid}: TIMED OUT — needs attention")
    else:
        print("lineages: none yet")
    for row in swarm.status_lines():        # step 8: sweeps in flight (SPEC §7)
        print(row)
    recent_reports()
    print(costs.summary_line())            # step 7: today · 7d · all (SPEC §10)


def recent_reports(limit=5):
    rows = []
    if LINEAGES.exists():
        for ld in (p for p in LINEAGES.iterdir() if p.is_dir()):
            for rp in ld.glob("report-*.json"):
                rows.append((rp.stat().st_mtime, ld.name, rp))
    rows.sort(reverse=True)
    if rows:
        print("recent reports:")
        for _, lid, rp in rows[:limit]:
            r = json.loads(rp.read_text())
            did = " ".join(str(r.get("did", "?")).split())[:70]
            stamp = r.get("runtime") or "v1"
            print(f"  · [{lid}] {r.get('based_on', '?')[:50]} -> {did}  [{stamp}]")


ROTATE_ARM = 100_000        # SPEC §3: ROTATE AT NEXT BOUNDARY past this
ROTATE_NOW = 128_000        # ROTATE NOW past this — the lead's hard line
STALE_N = 10                # prompts without a state.md change -> STATE.MD STALE


def context_from_transcript(path) -> int | None:
    """Context size = the last assistant entry's usage (input + cache read +
    cache creation) in the transcript JSONL Claude Code hands the hook —
    never file bytes, which never drop after a compaction."""
    if not path or not Path(path).exists():
        return None
    last = None
    for line_ in open(path, errors="replace"):
        if '"usage"' not in line_:
            continue
        try:
            o = json.loads(line_)
        except ValueError:
            continue
        u = (o.get("message") or {}).get("usage") if o.get("type") == "assistant" else None
        if isinstance(u, dict):
            last = u
    if last is None:
        return None
    return int(last.get("input_tokens") or 0) + int(last.get("cache_read_input_tokens") or 0) \
        + int(last.get("cache_creation_input_tokens") or 0)


def line(hook_input=None) -> str:
    """The one-line form for the UserPromptSubmit hook (SPEC §3, §5.2):
    one lead line — this directory's lineage, context size with the
    rotation nudges, state.md age with the STALE flag — plus one line per
    worker that needs attention. Also records the session's transcript
    path for /rotate and bumps the prompt counter."""
    import time
    from lineage import for_dir, state_path, waiting as _waiting, _lineage_dir, _load, _save
    lid = for_dir()
    d = _lineage_dir(lid)
    hook_input = hook_input or {}
    ctx = context_from_transcript(hook_input.get("transcript_path"))
    if hook_input.get("transcript_path"):
        _save(d / "session.json", {"transcript_path": hook_input["transcript_path"],
                                   "session_id": hook_input.get("session_id"),
                                   "context": ctx, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    sp = state_path(lid)
    mtime = sp.stat().st_mtime if sp.exists() else 0
    c = _load(d / "prompts.json", {"prompts": 0, "state_mtime": mtime, "since_change": 0})
    c["prompts"] += 1
    if c.get("state_mtime") != mtime:
        c["state_mtime"], c["since_change"] = mtime, 0
    else:
        c["since_change"] += 1
    _save(d / "prompts.json", c)
    ctx_s = "context n/a" if ctx is None else f"context {ctx // 1000}k"
    if ctx is not None and ctx > ROTATE_NOW:
        ctx_s += " — ROTATE NOW"
    elif ctx is not None and ctx > ROTATE_ARM:
        ctx_s += " — ROTATE AT NEXT BOUNDARY"
    age = f"changed {int((time.time() - mtime) / 60)}m ago, {c['since_change']} prompts" if mtime else "missing"
    stale = " — STATE.MD STALE" if c["since_change"] >= STALE_N else ""
    rows = [f"lead: lineage {lid} · {ctx_s} · state.md {age}{stale}"]
    for wid, goal in in_flight(lid).items():
        rows.append(f"worker {wid} RUNNING — {goal[:60]}")
    for wid, q in _waiting(lid).items():
        rows.append(f"worker {wid} WAITING (ask-back) — {q[:80]}")
    for wid in sweep_timeouts(lid):
        rows.append(f"worker {wid} TIMED OUT — needs a decision")
    rows += swarm.status_lines()
    return "\n".join(rows)


if __name__ == "__main__":
    if "--line" in sys.argv:
        hook_input = {}
        if not sys.stdin.isatty():
            try:
                hook_input = json.load(sys.stdin)
            except ValueError:
                hook_input = {}
        print(line(hook_input))
    else:
        main()
