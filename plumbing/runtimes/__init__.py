"""runtimes — the worker runtimes behind worker.py (SPEC §4.2, §5).

select(): `--runtime` flag > WORKER_RUNTIME in .env > `engine`.
run():    open the selected runtime, send the brief, and drive the ASK-BACK
          loop: a report whose open_items starts with `ASK:` files as
          `waiting`, the worker process BLOCKS on the answer file, then the
          answer goes into the SAME session as the next turn (the SDK server
          cannot reopen a session from another process, so the process stays
          alive — SPEC §4.1 literally). Steer and stop arrive the same way:
          files beside the worker, read by the runtime between calls.
AUTO-FALLBACK is narrow and loud: engine -> plain only when the engine
CANNOT START (import, binary, handshake = engine.CannotStart); never
mid-task, never on task failure; the stamp says `plain (fallback — <why>)`.

Both runtimes share the brief rendering, the report parsing and the
ask-back loop, so a brief reads the same on either and a report has the
same shape from either.
"""

import os
import re
import time
from pathlib import Path

import events  # noqa: E402
import lineage  # noqa: E402

REPORT_KEYS = ("did", "changed", "decisions", "surprises", "open_items", "evidence")
RUNTIMES = ("engine", "plain")
DEFAULT_STEPS = 25                       # SPEC §4.3; 64 for coding goals
ASK_ROUNDS = 3                           # ask-backs per worker before PARTIAL
EMPTY_COST = {"calls": 0, "input_tokens": 0, "cache_read_tokens": 0,
              "output_tokens": 0, "reasoning_tokens": 0}
# input_tokens = the whole prompt (cache misses + cache reads) — the number
# the 26k/32k context rule watches; cache_read_tokens is the cached part.
RESUME_PREFIX = "ANSWER from the lead (continue the task; end with the REPORT block): "
# A swarm lane's shell (SPEC §7 lane confinement): `env -i` plus PATH,
# HOME (= the lane's own directory, so `~` and $HOME stay inside the scope),
# locale, and the two swarm handles — SEARCH_AUTH_FILE (the mode-600 file
# swarm.py writes the search keys to; the engine scrubs credential-shaped
# names out of every shell, so keys never travel as variables) and
# SEARCH_LOG (one line per search call, priced into the ledger). Never the
# DeepSeek key, never AGENT_RUNTIME.
LANE_KEEP = ("PATH", "LANG", "LC_ALL", "LC_CTYPE")
LANE_HANDLES = {"search_auth_file": "SEARCH_AUTH_FILE", "search_log": "SEARCH_LOG"}
TOOLS_DIR = str(Path(__file__).resolve().parents[2] / "tools")   # first on a lane's PATH


def is_lane(brief: dict) -> bool:
    return bool(brief.get("lane"))


def lane_env(brief: dict) -> dict:
    """The environment a lane's shell may see (plain: the bash tool's env;
    engine: layered over the harness process, which scrubs the rest)."""
    env = {k: os.environ[k] for k in LANE_KEEP if k in os.environ}
    env["PATH"] = TOOLS_DIR + ":" + env.get("PATH", "/usr/bin:/bin")   # web_search.py, web_fetch.py
    env["HOME"] = str(brief["scope"])
    for field, name in LANE_HANDLES.items():
        if brief.get(field):
            env[name] = str(brief[field])
    return env


def select(flag=None) -> str:
    choice = flag or os.environ.get("WORKER_RUNTIME") or "engine"
    if choice not in RUNTIMES:
        raise ValueError(f"unknown runtime {choice!r}; expected one of {RUNTIMES}")
    return choice


def render_brief(brief: dict) -> str:
    """The brief as the worker's prompt. Paths only, never file bodies."""
    caps = brief.get("caps") or {}
    steps = caps.get("steps", DEFAULT_STEPS)
    return "\n".join([
        f"GOAL: {brief['goal']}",
        f"CONSTRAINTS: {brief.get('constraints') or '-'}",
        f"DEFINITION OF DONE: {brief['definition_of_done']}",
        f"RELEVANT FACTS: {brief.get('facts') or '-'}",
        f"SCOPE: {brief['scope']} — work only inside this directory; never read "
        "or write anything outside it.",
        f"CAPS: at most {steps} tool steps; wrap up and report before the cap.",
        "REPORT: when done, or when you must stop, make your final message "
        "exactly this block and nothing after it:",
        "DID: <what you did, 1-3 lines>",
        "CHANGED: <paths you changed, or ->",
        "DECISIONS: <decisions you took, or ->",
        "SURPRISES: <anything unexpected, or ->",
        "OPEN_ITEMS: <what remains, or -; if you cannot proceed without a "
        "decision only the lead can make, stop and write `ASK: <your question>` "
        "here — never guess>",
        "EVIDENCE: <commands you ran and what they showed, test output, paths "
        "— claims without evidence do not count as done>",
    ] + ([
        "SOURCES: <one per line: url · title · the claim it supports — the url "
        "field of a web_search result or the url line of a web_fetch, never an "
        "excerpt; a claim without a source does not count>",
    ] if brief.get("sources_required") else []))


_KEY = re.compile(r"^(DID|CHANGED|DECISIONS|SURPRISES|OPEN_ITEMS|EVIDENCE|SOURCES):[ \t]*",
                  re.M)


def parse_report(text: str) -> dict:
    """The worker's final REPORT block -> the six contract fields ('-' if
    absent) plus `sources` when the block has one (research reports, §7)."""
    out = {k: "-" for k in REPORT_KEYS}
    text = text or ""
    matches = list(_KEY.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        value = text[m.end():end].strip()
        out[m.group(1).lower()] = value or "-"
    return out


def build_report(brief, final_text, evidence, *, runtime, complete, cost,
                 extra=None) -> dict:
    """Shared report assembly: parsed block + mechanical evidence + stamps."""
    r = parse_report(final_text)
    parts = [p for p in (r["evidence"] if r["evidence"] != "-" else "",
                         "\n".join(evidence[-15:])) if p]
    r["evidence"] = "\n--- mechanical ---\n".join(parts) if parts else "-"
    if r["did"] == "-":
        r["did"] = (final_text or "(no final message)")[:1500]
    if not complete and r["open_items"] == "-":
        r["open_items"] = "PARTIAL: the worker did not finish (see evidence)"
    r.update({"based_on": brief.get("based_on") or brief["goal"][:300],
              "runtime": runtime,
              "data_tier": brief.get("data_tier", "private"),
              "cost": cost, "complete": bool(complete), "at_cap": None})
    r.update(extra or {})
    return r


def note_at_cap(report: dict, over: str) -> None:
    """Ruling on run 5 (2026-09-15): a final message over the context line is
    a result, never a PARTIAL — finish_reason `done-at-cap`, the overage
    first in open_items (a worker at the line cannot take an ask-back, so a
    question there is for the lead to read), `at_cap` for the sweep's row
    and lane headers."""
    report["finish_reason"], report["at_cap"] = "done-at-cap", over
    rest = str(report.get("open_items", "-"))
    report["open_items"] = f"done at cap: {over}" + ("" if rest in ("", "-") else f"; {rest}")


# ── the lead's verbs arrive as files beside the worker ───────────────────────

def verb_path(lid: str, wid: str, verb: str):
    return lineage.LINEAGES / lid / f"{verb}-{wid.split('.')[-1]}{'.txt' if verb != 'stop' else ''}"


def take_steer(lid: str, wid: str):
    """The steer note if one is waiting (consumed), else None."""
    p = verb_path(lid, wid, "steer")
    if not p.exists():
        return None
    note = p.read_text().strip()
    p.unlink()
    return note


def stop_requested(lid: str, wid: str) -> bool:
    return verb_path(lid, wid, "stop").exists()


def wait_for_answer(lid: str, wid: str, timeout_s: float, poll_s: float = 2.0):
    """Block on the answer file; None on stop or timeout."""
    p = verb_path(lid, wid, "answer")
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if p.exists():
            text = p.read_text().strip()
            p.unlink()
            return text
        if stop_requested(lid, wid):
            return None
        time.sleep(poll_s)
    return None


def _open(name: str, brief, lid, wid, log):
    """Open a runtime; the engine's start failure falls back to plain, loudly."""
    if name == "engine":
        from runtimes import engine
        try:
            return engine.Engine(brief, lid, wid, log), "engine"
        except engine.CannotStart as e:
            log(f"ENGINE CANNOT START — falling back to plain: {e}")
            from runtimes import plain
            return plain.Plain(brief, lid, wid, log), f"plain (fallback — {e})"
    from runtimes import plain
    return plain.Plain(brief, lid, wid, log), "plain"


def run(brief: dict, lid: str, wid: str, log, runtime=None) -> dict:
    """Brief -> report, with the ask-back loop in between. The runtime stays
    open (same session) across ask-backs; it is closed on return."""
    rt, stamp = _open(select(runtime), brief, lid, wid, log)
    lineage.stamp_runtime(lid, wid, stamp)      # visible in /status while running (run-5 ruling)
    timeout_s = (brief.get("caps") or {}).get("timeout_s", 7200)
    try:
        report = rt.turn(render_brief(brief))
        for _ in range(ASK_ROUNDS):
            asking = report["complete"] and str(report["open_items"]).startswith(lineage.ASK_PREFIX)
            if rt.stopped or not asking:
                break
            question = str(report["open_items"])[len(lineage.ASK_PREFIX):].strip()
            report["runtime"] = stamp
            lineage.file_report(lid, wid, report, state="waiting")
            events.emit(lid, wid, "ask", question)
            log(f"ASK-BACK (blocking on the answer file): {question[:200]}")
            answer = wait_for_answer(lid, wid, timeout_s)
            if answer is None:
                report["complete"] = False
                report["open_items"] = f"PARTIAL: ask-back unanswered (stop or timeout) — {question}"
                break
            lineage.set_state(lid, wid, "running")
            events.emit(lid, wid, "resumed", answer[:200])
            log(f"RESUME with the lead's answer: {answer[:200]}")
            report = rt.turn(RESUME_PREFIX + answer)
        report["runtime"] = stamp
        if report["complete"]:
            import check
            rungs = check.parse_rungs(brief.get("definition_of_done", ""))
            if rungs:
                results = check.ladder(brief["scope"], rungs)
                check.stamp(report, results)
                log("LADDER: " + "; ".join(f"{r['rung']} {r['status']}" for r in results))
                if not report["complete"]:
                    events.emit(lid, wid, "trip:ladder", report["open_items"])
        return report
    finally:
        rt.close()
