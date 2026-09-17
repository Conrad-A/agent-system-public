"""engine — DeepSeek Harness, one subprocess per worker (SPEC §4.2).

Composition = the shipped profile for the preset (minimal -> sdk-minimal,
standard -> sdk) plus our patch file in compositions/. The runtime's cwd is
the brief's scope, so workspaceRoot follows it. DSH_HOME is one shared home
under $AGENT_RUNTIME; sessions are keyed by worker id, so the trajectory is
$DSH_HOME/sessions/<cwd-mangled>/<worker id>/session.v3.jsonl.

The SDK server speaks three methods only: initialize, session/prompt,
shutdown. So: a session lives as long as this process (turns = prompts on
the same session id); STEER = a follow-up prompt queued while a turn runs
(a watcher thread sends it when the lead's steer file appears); STOP = the
watcher closes the runtime (the run raises, the report is PARTIAL). There
is no cancel and no cross-process resume.

CannotStart is raised only for import / binary / handshake failures — the
one case runtimes.run() may fall back to plain.
"""

import glob
import json
import os
import shutil
import threading
from pathlib import Path

import lineage  # noqa: E402
from clients import WORKER_MODEL  # noqa: E402
from runtimes import (EMPTY_COST, LANE_KEEP, build_report, is_lane, lane_env,  # noqa: E402
                      note_at_cap, stop_requested, take_steer, verb_path)
from supervisor import Supervisor  # noqa: E402

COMPOSITIONS = Path(__file__).resolve().parents[1] / "compositions"
PROFILES = {"minimal": "sdk-minimal", "standard": "sdk"}
DSH_HOME = lineage.RUNTIME / "dsh-home"
ENV = {"DSH_TELEMETRY_DISABLED": "1",          # no session telemetry
       "DSH_MAX_TOKENS_AS_SUCCESS": "false",   # a max-tokens turn is not success
       "DSH_PERMISSION_MODE": "workspace-write"}  # belt; the patch is the braces
WATCH_POLL_S = 1.0


class CannotStart(Exception):
    """The engine could not start: import, missing binary, or handshake."""


def trajectory_path(wid: str):
    hits = glob.glob(str(DSH_HOME / "sessions" / "*" / wid / "session.v3.jsonl*"))
    return hits[0] if hits else None


def _result_text(d: dict) -> str:
    parts = []
    for block in (d.get("message") or {}).get("content") or []:
        for inner in block.get("content") or []:
            if inner.get("type") == "text":
                parts.append(inner.get("text") or "")
    return "\n".join(parts)


class Engine:
    def __init__(self, brief: dict, lid: str, wid: str, log):
        preset = brief.get("preset", "minimal")
        if preset not in PROFILES:
            raise ValueError(f"engine has no preset {preset!r}; use one of {list(PROFILES)}")
        self.brief, self.lid, self.wid, self.log = brief, lid, wid, log
        self.scope = Path(brief["scope"]).expanduser().resolve()
        caps = brief.get("caps") or {}
        try:
            from deepseek_harness import DeepSeekHarness
        except ImportError as e:
            raise CannotStart(f"import: {e}") from None
        DSH_HOME.mkdir(parents=True, exist_ok=True)
        env = dict(ENV)
        # Ruling 3 (2026-09-16): the harness runtime is a pkg-packaged executable
        # whose dlopen hook copies every native module's package under
        # PKG_NATIVE_CACHE_PATH, else $HOME/.cache/pkg/<hash> — run 6 left 38 MB
        # in every lane dir (HOME = lane dir) and crashed the dream. Per WORKER,
        # never shared: pkg re-copies on every launch with plain overwrites, so a
        # sweep's simultaneous lanes would race on one dir. Removed at close.
        self.cache = DSH_HOME / "cache" / wid
        env["PKG_NATIVE_CACHE_PATH"] = str(self.cache)
        # Change 12 (ruling on run 6): the context meter reaches a RUNNING engine
        # turn only through a tool result — the harness's Claude Code hooks
        # bridge (§14 item 1a) runs a PostToolUse command hook, `cat` of the
        # supervisor's meter file, whose JSON the bridge adds as one context
        # line after the tool result. One config per process, read at startup:
        # per worker, in the cache dir that goes at close; the env name is
        # DSH_*, so the lane's shell never sees it. Fail-open by the bridge.
        self.hooks = self.cache / "hooks.json"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.hooks.write_text(json.dumps({"hooks": {"PostToolUse": [{"matcher": ".*", "hooks": [
            {"type": "command", "command": f"cat {verb_path(lid, wid, 'meter')}"}]}]}}) + "\n")
        env["DSH_HOOKS_CONFIG"] = str(self.hooks)
        if is_lane(brief):
            # §7 lane confinement: the harness inherits this process's env and
            # forwards it to the shell minus credential-shaped and DSH_* names
            # (dsh-subprocess scrubbedParentEnv, read 2026-09-15); prune the
            # rest here so the shell sees only PATH, HOME, locale, the two
            # swarm handles — never AGENT_RUNTIME or the lead's session.
            keep = set(LANE_KEEP) | {"DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"}
            for k in list(os.environ):
                if k not in keep and not k.startswith("DSH_"):
                    del os.environ[k]
            env.update(lane_env(brief))
        try:
            self.h = DeepSeekHarness(
                dsh_home=str(DSH_HOME), cwd=str(self.scope), profile=PROFILES[preset],
                patches=(str(COMPOSITIONS / f"{preset}.patch.yml"),),
                model=WORKER_MODEL, provider="deepseek-official",
                reasoning_effort=caps.get("effort", "max"),
                max_tokens=int(caps.get("max_tokens", 16384)), env=env,
                request_timeout_seconds=caps.get("timeout_s", 7200))
            self.h.start()
        except Exception as e:  # noqa: BLE001 — start / handshake only
            shutil.rmtree(self.cache, ignore_errors=True)
            raise CannotStart(f"{type(e).__name__}: {str(e)[:300]}") from None
        self.evidence, self.cost, self.steps = [], dict(EMPTY_COST), 0
        self.stopped = False
        self.at_cap = None          # a final message over the context line: the overage (ruling on run 5)
        self._pending = None        # (prompt, tool results still due) — the 32k check waits for them
        self.sup = Supervisor(brief, lid, wid, log)
        self._closed = threading.Event()
        self._watcher = threading.Thread(target=self._watch, name="verbs", daemon=True)
        self._watcher.start()

    # ── the lead's verbs: steer (follow-up prompt) and stop (close) ──────────
    def _watch(self):
        while not self._closed.wait(WATCH_POLL_S):
            if stop_requested(self.lid, self.wid):
                self.stopped = True
                self.log("STOP requested — closing the runtime")
                self.h.close()
                return
            note = take_steer(self.lid, self.wid)
            if note is not None:
                self.log(f"STEER queued as a follow-up: {note[:200]}")
                try:
                    self.h.client.session_prompt(
                        self.wid, [{"type": "text", "text": f"STEER from the lead: {note}"}])
                except Exception as e:  # noqa: BLE001
                    self.log(f"STEER failed: {e}")

    def _on_event(self, n):
        ev = n.payload.get("event") if n.method == "session.event" else None
        if not isinstance(ev, dict):
            return
        t, d = ev.get("type"), ev.get("data") or {}
        if t == "tool/call":
            self.steps += 1
            self.log(f"STEP {self.steps}: {d.get('name')} {str(d.get('arguments'))[:200]}")
            self.evidence.append(f"[{d.get('name')}] {str(d.get('arguments'))[:80]}")
            args = d.get("arguments")       # a dict from the SDK: the supervisor reads JSON, not a repr
            self.sup.tool_call(str(d.get("name")), args if isinstance(args, str) else json.dumps(args or {}))
        elif t == "tool/result":
            txt = _result_text(d)
            self.log(f"RESULT: {txt[:200]}")
            if self.evidence:
                self.evidence[-1] += f" -> {txt[:120]}"
            # the SDK result is text only (run 6's trajectories: no exit or stderr field, isError
            # false on every result): the supervisor reads the exit from the harness's trailing
            # marker; an isError result, never seen yet, counts as exit 1
            is_error = any(b.get("isError") for b in (d.get("message") or {}).get("content") or [])
            self.sup.tool_result(txt, exit_code=1 if is_error else None)
            if self._pending:               # the message's last result: now the 32k check (the write landed)
                prompt, due = self._pending
                self._pending = (prompt, due - 1) if due > 1 else None
                if due <= 1:
                    self.sup.context_check(prompt)
        elif t == "assistant/message":
            u = d.get("usage") or {}
            cached = int(u.get("cacheReadTokens") or 0)
            prompt = int(u.get("inputTokens") or 0) + cached   # miss + cached = whole prompt
            self.cost["calls"] += 1
            self.cost["input_tokens"] += prompt
            self.cost["cache_read_tokens"] += cached
            self.cost["output_tokens"] += int(u.get("outputTokens") or 0)
            self.cost["reasoning_tokens"] += int(u.get("reasoningTokens") or 0)
            self.log(f"CONTEXT call {self.cost['calls']}: prompt_tokens={prompt} (cached {cached})")
            blocks = (d.get("message") or {}).get("content") or []
            reasoning = " ".join(b.get("text") or "" for b in blocks if b.get("type") == "reasoning")
            if self._pending:               # a result never came: the previous call's check, now
                self.sup.context_check(self._pending[0])
                self._pending = None
            self.sup.model_call(prompt, reasoning)
            # ruling on run 5: the stream is message, its tool calls, their results, next message
            # (read from a real trajectory 2026-09-15) — so the 32k check runs at this message's
            # last tool/result, after the write landed; a trip there closes the runtime (the
            # watcher, within a second) before the next call can complete. A final message
            # (no tool-call block) is checked now and KEPT: done at cap, the overage on the report.
            tools = sum(1 for b in blocks if b.get("type") == "tool-call")
            if tools:
                self._pending = (prompt, tools)
            else:
                self.at_cap = self.sup.context_check(prompt, final=True)
        elif t == "turn/end":
            self.log(f"TURN END: {json.dumps(d.get('reason'))}")
            kind = (d.get("reason") or {}).get("kind")
            self.sup.finish(str(kind))

    def turn(self, prompt: str) -> dict:
        """One prompt on this worker's session -> a report (cumulative cost)."""
        try:
            result = self.h.run(prompt, session_id=self.wid, on_notification=self._on_event)
            finish, final = result.finish_reason, result.final_response
        except Exception as e:  # noqa: BLE001
            if not self.stopped:
                raise
            finish, final = "stopped", ""
            self.log(f"TURN ended by stop: {type(e).__name__}")
        complete = finish == "completed" and not self.sup.tripped
        self.log(f"FINISH: {finish}")
        report = build_report(self.brief, final, self.evidence, runtime="engine",
                              complete=complete, cost=dict(self.cost),
                              extra={"trajectory": trajectory_path(self.wid),
                                     "finish_reason": finish, "steps": self.steps})
        if self.sup.tripped:
            report["open_items"] = f"PARTIAL: {self.sup.tripped}"
        elif complete and self.at_cap:
            note_at_cap(report, self.at_cap)
        return report

    def close(self):
        self._closed.set()
        self.h.close()
        shutil.rmtree(self.cache, ignore_errors=True)   # the worker's pkg cache (ruling 3)
