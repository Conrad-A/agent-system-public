#!/usr/bin/env python3
"""Fable module — shared transport + rate cap (SPEC-v3.1 §2d, phase 1).

Transport: Claude Code CLI (`claude -p`) billed to the owner's Max
subscription (decision 2026-09-03). Raw Anthropic API kept as a fallback
flag only: FABLE_TRANSPORT=api + ANTHROPIC_API_KEY in .env.

Caps are RATE caps, not dollar caps (flat-rate transport): default 10
calls/day, override FABLE_RATE_CAP. Per-question friction is deliberate —
escalation must never become a mode (§2d).

Observability: every call appends a JSONL row (ts, model, latency, chars)
to <runtime>/fable/log.jsonl. Langfuse can't wrap a CLI subprocess (its
drop-in wrapper is OpenAI-client-only) — a dsh→Langfuse-style exporter for
this log is future work; the log is the ground truth meanwhile.

Module disabled = CLI absent (and no API fallback configured): every
feature answers with a one-line "disabled" message and nothing else
changes — the load-bearing invariant (§2d).
"""

import json
import os
import shutil
import subprocess
import time
import urllib.request
from datetime import date
from pathlib import Path

RUNTIME = Path(os.environ.get("AGENT_RUNTIME",
                              Path.home() / "Desktop" / "agent-system-runtime"))
FABLE_DIR = RUNTIME / "fable"
MODELS = [os.environ.get("FABLE_MODEL", "claude-fable-5-1"), "claude-fable-5"]
RATE_CAP = int(os.environ.get("FABLE_RATE_CAP", "10"))
ARM_CAP = int(os.environ.get("FABLE_VERIFY_CAP", "20"))
DISABLED = ("fable module disabled — claude CLI not found and no API "
            "fallback configured. Core system unaffected (SPEC-v3.1 §2d).")


def find_cli():
    """CLI path: CLAUDE_BIN override first, then PATH. None = not installed."""
    env = os.environ.get("CLAUDE_BIN")
    if env:
        return env if Path(env).exists() else None
    return shutil.which("claude")


def api_fallback_ready() -> bool:
    return (os.environ.get("FABLE_TRANSPORT") == "api"
            and bool(os.environ.get("ANTHROPIC_API_KEY")))


def enabled() -> bool:
    return find_cli() is not None or api_fallback_ready()


# ── rate cap ─────────────────────────────────────────────────────────────────

def _counter_file() -> Path:
    return FABLE_DIR / f"calls-{date.today().isoformat()}.json"


def calls_today() -> int:
    f = _counter_file()
    try:
        return int(json.loads(f.read_text())["n"])
    except Exception:  # noqa: BLE001
        return 0


def check_cap() -> int:
    """Remaining calls today; 0 = refuse."""
    return max(0, RATE_CAP - calls_today())


def record_call(model: str, latency: float, chars: int,
                count: bool = True, kind: str = "escalate") -> None:
    """count=False for the sanctioned scheduled classes (calibration):
    they log but never consume the owner's daily escalate budget."""
    FABLE_DIR.mkdir(parents=True, exist_ok=True)
    if count:
        _counter_file().write_text(json.dumps({"n": calls_today() + 1}))
    with (FABLE_DIR / "log.jsonl").open("a") as fh:
        fh.write(json.dumps({"ts": time.time(), "model": model, "kind": kind,
                             "latency_s": round(latency, 1),
                             "chars": chars}) + "\n")


# ── verify arm (SPEC-v3.1 §2d phase 3) ────────────────────────────────────────────
# One Fable candidate joins the verify pool for FAMILY decorrelation —
# flag-gated (FABLE_VERIFY_ARM), its own daily cap (FABLE_VERIFY_CAP,
# separate from the escalate budget), and it may only ever ADD a candidate:
# any failure or cap hit degrades to the plain ×5 pool, never blocks verify.

def verify_arm_enabled() -> bool:
    return (os.environ.get("FABLE_VERIFY_ARM", "").lower()
            in ("1", "on", "true", "yes")) and enabled()


def _arm_counter_file() -> Path:
    return FABLE_DIR / f"calls-arm-{date.today().isoformat()}.json"


def arm_calls_today() -> int:
    try:
        return int(json.loads(_arm_counter_file().read_text())["n"])
    except Exception:  # noqa: BLE001
        return 0


def check_arm_cap() -> int:
    return max(0, ARM_CAP - arm_calls_today())


def record_arm_call() -> None:
    FABLE_DIR.mkdir(parents=True, exist_ok=True)
    _arm_counter_file().write_text(json.dumps({"n": arm_calls_today() + 1}))


# ── transport ────────────────────────────────────────────────────────────────

def _ask_cli(cli: str, prompt: str, timeout: int):
    last_err = "no model accepted the call"
    for model in MODELS:
        t0 = time.time()
        r = subprocess.run([cli, "-p", "--model", model, prompt],
                           capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip(), model, time.time() - t0
        last_err = (r.stderr or r.stdout or "empty reply").strip()[:300]
    raise RuntimeError(f"claude CLI failed: {last_err}")


def _ask_api(prompt: str, timeout: int):
    body = json.dumps({"model": MODELS[0], "max_tokens": 8192,
                       "messages": [{"role": "user", "content": prompt}]})
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body.encode(),
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        j = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in j.get("content", []))
    return text.strip(), j.get("model", MODELS[0]), time.time() - t0


def ask(prompt: str, timeout: int = 540):
    """One Fable call. Returns (text, model, latency_s). Caller checks the
    cap FIRST (check_cap) and records AFTER (record_call)."""
    cli = find_cli()
    if cli:
        return _ask_cli(cli, prompt, timeout)
    if api_fallback_ready():
        return _ask_api(prompt, timeout)
    raise RuntimeError(DISABLED)


def status_line() -> str:
    """One line for !status (SPEC-v3.1 §2d: caps visible)."""
    if not enabled():
        return "fable: disabled (no CLI, no API fallback)"
    via = "claude -p" if find_cli() else "api fallback"
    arm = (f"verify-arm ON {arm_calls_today()}/{ARM_CAP}"
           if verify_arm_enabled() else "verify-arm off")
    return (f"fable: enabled via {via} · escalate {calls_today()}/{RATE_CAP} "
            f"today · {arm}")
