#!/usr/bin/env python3
"""Lineage machinery (SPEC §3, §4.1): one lineage per project directory,
the worker registry, the report contract, ask-back.

Runtime state lives OUTSIDE the repo (body, not genome) at $AGENT_RUNTIME
(from .env; v1 default ~/Desktop/agent-system-runtime).

State layout:
  runtime/lineages/index.json            {"<abs project dir>": "<lineage id>"}
  runtime/lineages/<lineage_id>/
    meta.json        {project_dir, created}
    registry.json    {workers: {id: {state, brief, started, timeout_s,
                                     report_path, trajectory, runtime, question}}}
                     (every writer: <file>.lock held, <file>.tmp + os.replace)
    state.md         the lead's continuous state file (holistic rewrites only)
    events.jsonl     append-only lineage event log
    worker-<hex>.log / report-<hex>.json / steer-<hex>.txt / stop-<hex> /
    answer-<hex>.txt — per-worker files (log, report, the lead's verbs)
"""

import calendar
import contextlib
import fcntl
import json
import os
import time
import uuid
from pathlib import Path

import sanitize  # noqa: E402
from envfile import load_env  # noqa: E402

load_env()                      # .env -> environment; existing values win
RUNTIME = Path(os.environ.get(
    "AGENT_RUNTIME", Path.home() / "Desktop" / "agent-system-runtime"))
LINEAGES = RUNTIME / "lineages"

WORKER_STATES = ("running", "waiting", "done", "failed", "timed_out")
REPORT_FIELDS = ("did", "changed", "decisions", "surprises", "open_items",
                 "evidence", "based_on",            # SPEC §4.1 contract
                 "runtime", "data_tier", "cost")    # v2 stamps
REPORT_CHAT_BUDGET = 500                            # ~tokens to chat; rest via files
ASK_PREFIX = "ASK:"                                 # open_items marker for ask-back


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _lineage_dir(lineage_id: str) -> Path:
    d = LINEAGES / lineage_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def _save(path: Path, obj):
    """Atomic: write <file>.tmp beside it, then os.replace it into place, so
    a reader never sees a truncated file. Run 6 (2026-09-15): a lane worker's
    start-time stamp_runtime read registry.json mid-write (empty) and died."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


@contextlib.contextmanager
def _locked(path: Path):
    """Exclusive lock for a load-modify-save on `path`: flock on <file>.lock
    beside it, released when the handle closes. Every registry / index writer
    holds it, so concurrent writers never lose an update; readers need no
    lock because _save replaces atomically."""
    with open(path.with_name(path.name + ".lock"), "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def _event(lineage_id: str, kind: str, **data):
    with open(_lineage_dir(lineage_id) / "events.jsonl", "a") as f:
        f.write(json.dumps({"ts": _now(), "kind": kind, **data}) + "\n")


def _hex(worker_id: str) -> str:
    return worker_id.split(".")[-1]


# ── lineages: one per project directory ──────────────────────────────────────

def create_lineage(project_dir) -> str:
    project_dir = str(Path(project_dir).resolve())
    lid = time.strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6]
    d = _lineage_dir(lid)
    _save(d / "meta.json", {"project_dir": project_dir, "created": _now()})
    _save(d / "registry.json", {"workers": {}})
    (d / "state.md").write_text("# state — decisions · open threads · focus\n")
    index_p = LINEAGES / "index.json"
    with _locked(index_p):
        index = _load(index_p, {})
        index[project_dir] = lid
        _save(index_p, index)
    _event(lid, "lineage_created", project_dir=project_dir)
    return lid


def for_dir(project_dir=None) -> str:
    """The lineage id of a project directory (default: cwd); created if new."""
    project_dir = str(Path(project_dir or Path.cwd()).resolve())
    index = _load(LINEAGES / "index.json", {})
    return index.get(project_dir) or create_lineage(project_dir)


def state_path(lineage_id: str) -> Path:
    return _lineage_dir(lineage_id) / "state.md"


# ── workers (SPEC §4.1 contract) ──────────────────────────────────────────

def spawn_worker(lineage_id: str, brief: dict, timeout_s: int = 7200) -> str:
    """Brief must carry: goal, definition_of_done, scope (enforced);
    constraints, facts, preset, runtime, caps are optional.
    Returns the worker id <lineage_id>.<hex> (no collisions across lineages)."""
    for k in ("goal", "definition_of_done", "scope"):
        if k not in brief:
            raise ValueError(f"brief missing required field: {k}")
    wid = f"{lineage_id}.{uuid.uuid4().hex[:6]}"
    reg_p = _lineage_dir(lineage_id) / "registry.json"
    with _locked(reg_p):
        reg = _load(reg_p, {"workers": {}})
        reg["workers"][wid] = {"state": "running", "brief": brief, "started": _now(),
                               "timeout_s": timeout_s, "report_path": None,
                               "trajectory": None, "runtime": brief.get("runtime"),
                               "question": None}
        _save(reg_p, reg)
    _event(lineage_id, "worker_spawned", worker=wid, goal=brief["goal"],
           preset=brief.get("preset"), runtime=brief.get("runtime"))
    return wid


def worker_brief(lineage_id: str, worker_id: str) -> dict:
    """The brief spawn_worker stored for this worker (the adapter reads it)."""
    reg = _load(_lineage_dir(lineage_id) / "registry.json", {"workers": {}})
    return reg["workers"][worker_id]["brief"]


def file_report(lineage_id: str, worker_id: str, report: dict,
                state: str = "done") -> str:
    """Reports are contracts: required fields, evidence required for 'done'.
    state 'waiting' = ask-back: open_items carries `ASK: <question>` and the
    question is recorded in the registry for /status and the resume verb."""
    if state not in WORKER_STATES:
        raise ValueError(f"unknown worker state {state!r}")
    missing = [f for f in REPORT_FIELDS if f not in report]
    if missing:
        raise ValueError(f"report missing fields: {missing}")
    if state == "done" and not report["evidence"]:
        raise ValueError("claims without evidence don't count as done (SPEC §4.1)")
    sanitize.sanitize_report(report)          # SPEC §7: reports are data, enforced
    d = _lineage_dir(lineage_id)
    rp = d / f"report-{_hex(worker_id)}.json"
    _save(rp, report)
    reg_p = d / "registry.json"
    with _locked(reg_p):
        reg = _load(reg_p, {"workers": {}})
        if worker_id in reg["workers"]:
            w = reg["workers"][worker_id]
            w.update(state=state, report_path=str(rp),
                     trajectory=report.get("trajectory"), runtime=report.get("runtime"))
            if state == "waiting":
                w["question"] = str(report.get("open_items", "")).removeprefix(ASK_PREFIX).strip()
        _save(reg_p, reg)
    _event(lineage_id, "worker_report", worker=worker_id, state=state)
    return str(rp)


def lineage_of(worker_id: str) -> str:
    return worker_id.rsplit(".", 1)[0]


def set_state(lineage_id: str, worker_id: str, state: str) -> None:
    """Flip a worker's registry state (resume -> running, stop -> failed)."""
    if state not in WORKER_STATES:
        raise ValueError(f"unknown worker state {state!r}")
    reg_p = _lineage_dir(lineage_id) / "registry.json"
    with _locked(reg_p):
        reg = _load(reg_p, {"workers": {}})
        reg["workers"][worker_id]["state"] = state
        _save(reg_p, reg)
    _event(lineage_id, "worker_state", worker=worker_id, state=state)


def set_pid(lineage_id: str, worker_id: str, pid: int) -> None:
    reg_p = _lineage_dir(lineage_id) / "registry.json"
    with _locked(reg_p):
        reg = _load(reg_p, {"workers": {}})
        reg["workers"][worker_id]["pid"] = pid
        _save(reg_p, reg)


def stamp_runtime(lineage_id: str, worker_id: str, runtime: str) -> None:
    """Record the runtime a worker ACTUALLY opened (`engine`, `plain`, or
    `plain (fallback — <why>)`) in its registry row at start, so /status and
    a sweep's status.json show it while the worker runs — the filed report
    re-stamps it at the end. Ruling on run 5 (2026-09-15): the fallback was
    only ever visible in the worker log and the ledger, and nobody read them."""
    reg_p = _lineage_dir(lineage_id) / "registry.json"
    with _locked(reg_p):
        reg = _load(reg_p, {"workers": {}})
        if worker_id in reg["workers"]:
            reg["workers"][worker_id]["runtime"] = runtime
            _save(reg_p, reg)


def worker_entry(lineage_id: str, worker_id: str):
    """The registry row of a worker, or None when the id is unknown (the
    verbs print one clean line instead of a traceback)."""
    if not (LINEAGES / lineage_id).is_dir():
        return None
    reg = _load(_lineage_dir(lineage_id) / "registry.json", {"workers": {}})
    return reg["workers"].get(worker_id)


def answer(lineage_id: str, worker_id: str, text: str) -> Path:
    """The lead's answer to an ask-back: written beside the worker for the
    resume verb (step 3) to deliver; state stays waiting until then."""
    p = _lineage_dir(lineage_id) / f"answer-{_hex(worker_id)}.txt"
    p.write_text(text.strip() + "\n")
    _event(lineage_id, "answered", worker=worker_id)
    return p


def sweep_timeouts(lineage_id: str) -> list[str]:
    """Mark overdue running workers timed_out; return their ids (notify!)."""
    reg_p = _lineage_dir(lineage_id) / "registry.json"
    flipped = []
    with _locked(reg_p):
        reg = _load(reg_p, {"workers": {}})
        for wid, w in reg["workers"].items():
            if w["state"] == "running":
                started = calendar.timegm(
                    time.strptime(w["started"], "%Y-%m-%dT%H:%M:%SZ"))  # UTC in, UTC out
                if time.time() - started > w["timeout_s"]:
                    w["state"] = "timed_out"
                    flipped.append(wid)
        if flipped:
            _save(reg_p, reg)
    for wid in flipped:
        _event(lineage_id, "worker_timeout", worker=wid)
    return flipped


def in_flight(lineage_id: str) -> dict:
    """Running workers: {id: goal}."""
    reg = _load(_lineage_dir(lineage_id) / "registry.json", {"workers": {}})
    return {w: v["brief"]["goal"] for w, v in reg["workers"].items()
            if v["state"] == "running"}


def waiting(lineage_id: str) -> dict:
    """Workers blocked on an ask-back: {id: question}."""
    reg = _load(_lineage_dir(lineage_id) / "registry.json", {"workers": {}})
    return {w: v.get("question") or "?" for w, v in reg["workers"].items()
            if v["state"] == "waiting"}
