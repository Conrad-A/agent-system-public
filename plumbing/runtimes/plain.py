"""plain — the fallback worker loop (SPEC §4.2): direct API through
clients.py, the v1 16-tool catalog, one-shot bash, a text step log.

Moved from v1 worker.py with two forced changes: no `openai` package on the
host (clients.py is stdlib) and the jail is the brief's scope, never
~/Desktop. Steer = the steer file read before each model call; stop = the
stop file checked between steps; ask-back continues in-process like the
engine. The file tools are jailed to WORKSPACE component-wise; the bash
tool runs in WORKSPACE but is not jailed (the §5.1 scope trip is the fence).

DeepSeek quirk honored: with tools in play, reasoning_content is replayed on
every later request (clients.replay).
"""

import json
import subprocess
from pathlib import Path

from clients import DEEPSEEK, WORKER_MODEL, message, replay, usage  # noqa: E402
from runtimes import (DEFAULT_STEPS, EMPTY_COST, build_report, is_lane,  # noqa: E402
                      lane_env, note_at_cap, stop_requested, take_steer)
from supervisor import Supervisor  # noqa: E402

WORKSPACE = Path.cwd()               # set per run from the brief's scope
SHELL_ENV = None                     # lanes: the confined env for bash (§7)
MAX_TOOL_OUT = 12000
SHELL_TIMEOUT_S = 300                # SPEC §4.3


def _tool(name, desc, props, req):
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props, "required": req}}}


_P = {"path": {"type": "string"}}
_PP = {"src": {"type": "string"}, "dest": {"type": "string"}}
TOOLS = [
    _tool("bash", "Run a shell command in the workspace; output capped 12k.",
          {"command": {"type": "string"}}, ["command"]),
    _tool("read_file", "Read a file (workspace only).", _P, ["path"]),
    _tool("write_file", "Write/overwrite a file (workspace only).",
          {**_P, "content": {"type": "string"}}, ["path", "content"]),
    _tool("append_file", "Append to a file (workspace only).",
          {**_P, "content": {"type": "string"}}, ["path", "content"]),
    _tool("list_dir", "List a directory's entries.", _P, ["path"]),
    _tool("glob", "Find files matching a glob pattern under a directory.",
          {**_P, "pattern": {"type": "string"}}, ["path", "pattern"]),
    _tool("grep", "Search file contents for a regex under a directory.",
          {**_P, "pattern": {"type": "string"}}, ["path", "pattern"]),
    _tool("mkdir", "Create a directory (parents included).", _P, ["path"]),
    _tool("move", "Move/rename a file or directory.", _PP, ["src", "dest"]),
    _tool("copy", "Copy a file or directory.", _PP, ["src", "dest"]),
    _tool("delete", "Delete a file or empty directory (workspace only).", _P, ["path"]),
    _tool("head", "First 40 lines of a file.", _P, ["path"]),
    _tool("tail", "Last 40 lines of a file.", _P, ["path"]),
    _tool("diff", "Unified diff between two files.", _PP, ["src", "dest"]),
    _tool("file_info", "Size, mtime, and type of a path.", _P, ["path"]),
    _tool("todo_note", "Record a working note in the worker log.",
          {"note": {"type": "string"}}, ["note"]),
]

SYSTEM = """You are an execution worker in a personal agent system. Complete
the task using the tools, then STOP and report. Rules: stay inside the SCOPE
directory; be surgical — smallest change that completes the task; collect
EVIDENCE (command output, file paths) as you go; if the task is impossible
or unsafe, stop and say why. End with the REPORT block the brief asks for."""


def _safe_path(p: str) -> Path:
    full = (WORKSPACE / p).resolve() if not p.startswith("/") else Path(p).resolve()
    if not (full == WORKSPACE or WORKSPACE in full.parents):
        raise ValueError(f"outside workspace: {p}")   # component-wise jail
    return full


def _sh(cmd, cwd=None):
    """(text, exit code, stderr) of one shell command."""
    r = subprocess.run(cmd, cwd=cwd or WORKSPACE, capture_output=True,
                       text=True, timeout=SHELL_TIMEOUT_S, env=SHELL_ENV)
    text = (r.stdout + r.stderr)[:MAX_TOOL_OUT] or f"(exit {r.returncode}, no output)"
    return text, r.returncode, r.stderr


def run_tool(name: str, args: dict) -> str:
    return run_tool_exit(name, args)[0]


def run_tool_exit(name: str, args: dict) -> tuple:
    """(text, exit code, stderr): a shell tool's real exit and stderr ride
    beside its text so a lane's supervisor signs an error by them, never by
    a word in the output (ruling on run 6, 2026-09-15); a file tool exits 0."""
    out = _run_tool(name, args)
    return out if isinstance(out, tuple) else (out, 0, "")


def _run_tool(name: str, args: dict):  # noqa: PLR0911, PLR0912
    if name == "bash":
        return _sh(["bash", "-c", args["command"]])
    if name == "read_file":
        return _safe_path(args["path"]).read_text()[:MAX_TOOL_OUT]
    if name in ("write_file", "append_file"):
        p = _safe_path(args["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if name == "append_file" else "w"
        with open(p, mode) as f:
            f.write(args["content"])
        return f"{name} {p} ({len(args['content'])} chars)"
    if name == "list_dir":
        return "\n".join(sorted(x.name + ("/" if x.is_dir() else "")
                                for x in _safe_path(args["path"]).iterdir()))[:MAX_TOOL_OUT]
    if name == "glob":
        return "\n".join(str(x) for x in
                         _safe_path(args["path"]).rglob(args["pattern"]))[:MAX_TOOL_OUT] or "(no matches)"
    if name == "grep":
        return _sh(["grep", "-rn", "-m", "50", "-E", args["pattern"],
                    str(_safe_path(args["path"]))])
    if name == "mkdir":
        _safe_path(args["path"]).mkdir(parents=True, exist_ok=True)
        return "created"
    if name in ("move", "copy"):
        s, d = _safe_path(args["src"]), _safe_path(args["dest"])
        cmd = ["mv", str(s), str(d)] if name == "move" \
            else ["cp", "-r", str(s), str(d)]          # mv takes no -r
        return _sh(cmd)
    if name == "delete":
        p = _safe_path(args["path"])
        p.rmdir() if p.is_dir() else p.unlink()
        return f"deleted {p}"
    if name in ("head", "tail"):
        return _sh([name, "-n", "40", str(_safe_path(args["path"]))])
    if name == "diff":
        return _sh(["diff", "-u", str(_safe_path(args["src"])),
                    str(_safe_path(args["dest"]))])
    if name == "file_info":
        p = _safe_path(args["path"])
        st = p.stat()
        return f"{p}: {'dir' if p.is_dir() else 'file'}, {st.st_size} bytes, mtime {st.st_mtime}"
    if name == "todo_note":
        return f"noted: {args['note'][:200]}"
    return f"unknown tool {name}"


class Plain:
    """The loop as a runtime object: turn() runs one prompt to a final
    message (or a cap / stop); messages persist across turns, so an
    ask-back answer continues the same conversation in-process."""

    def __init__(self, brief: dict, lid: str, wid: str, log):
        global WORKSPACE, SHELL_ENV
        WORKSPACE = Path(brief["scope"]).expanduser().resolve()
        WORKSPACE.mkdir(parents=True, exist_ok=True)
        SHELL_ENV = lane_env(brief) if is_lane(brief) else None
        self.brief, self.lid, self.wid, self.log = brief, lid, wid, log
        self.caps = brief.get("caps") or {}
        self.max_steps = int(self.caps.get("steps", DEFAULT_STEPS))
        self.messages = [{"role": "system", "content": SYSTEM}]
        self.evidence, self.cost, self.steps = [], dict(EMPTY_COST), 0
        self.stopped = False
        self.sup = Supervisor(brief, lid, wid, log)

    def turn(self, prompt: str) -> dict:
        self.messages.append({"role": "user", "content": prompt})
        final, complete, finish, at_cap = "", False, "step-cap", None
        for _ in range(self.max_steps):
            if stop_requested(self.lid, self.wid):
                self.log("STOP requested — stopping between steps")
                self.stopped, finish = True, "stopped"
                break
            note = take_steer(self.lid, self.wid)
            if note is not None:
                self.messages.append({"role": "user", "content": f"STEER from the lead: {note}"})
                self.log(f"STEER applied: {note[:200]}")
            r = DEEPSEEK.complete(self.messages, model=WORKER_MODEL, tools=TOOLS,
                                  max_tokens=int(self.caps.get("max_tokens", 16384)),
                                  effort=self.caps.get("effort", "max"))
            u = usage(r)
            self.cost["calls"] += 1
            self.cost["input_tokens"] += int(u.get("prompt_tokens") or 0)
            self.cost["cache_read_tokens"] += int(u.get("prompt_cache_hit_tokens") or 0)
            self.cost["output_tokens"] += int(u.get("completion_tokens") or 0)
            self.cost["reasoning_tokens"] += int((u.get("completion_tokens_details") or {})
                                                 .get("reasoning_tokens") or 0)
            self.log(f"CONTEXT call {self.cost['calls']}: prompt_tokens={u.get('prompt_tokens')} "
                     f"(cached {u.get('prompt_cache_hit_tokens', 0)})")
            msg = message(r)
            self.messages.append(replay(msg))            # reasoning_content replayed
            prompt = int(u.get("prompt_tokens") or 0)
            self.sup.model_call(prompt, msg.get("reasoning_content") or "")
            if not msg.get("tool_calls"):
                final, complete, finish = msg.get("content") or "", True, "completed"
                at_cap = self.sup.context_check(prompt, final=True)   # ruling on run 5: the answer is kept
                self.log(f"STEP {self.steps}: final message" + (f" — done at cap: {at_cap}" if at_cap else ""))
                break
            for tc in msg["tool_calls"]:
                fn = tc["function"]
                args = json.loads(fn.get("arguments") or "{}")
                self.steps += 1
                self.log(f"STEP {self.steps}: {fn['name']} {str(args)[:200]}")
                self.sup.tool_call(fn["name"], json.dumps(args))
                if self.sup.tripped:
                    out = "stopped by the supervisor"
                else:
                    try:
                        out, code, err = run_tool_exit(fn["name"], args)
                    except Exception as e:  # noqa: BLE001
                        out, code, err = f"tool error: {e}", 1, str(e)
                    self.sup.tool_result(out, code, err)      # the exit and stderr, not the text, sign a lane's errors
                    if self.sup.meter:                        # change 12: the context meter rides the result
                        out = (out or "(no output)") + "\n" + self.sup.meter
                self.evidence.append(f"[{fn['name']}] {str(args)[:80]} -> {out[:120]}")
                self.messages.append({"role": "tool", "tool_call_id": tc["id"],
                                      "content": out or "(no output)"})
            # ruling on run 5: the 32k check AFTER the call's tool calls ran — a notebook
            # write persists; over the line it trips here, so there is no further model call
            self.sup.context_check(prompt)
        else:
            self.log(f"STEP CAP {self.max_steps} hit — stop + report (never silent)")
        if self.sup.tripped:
            complete, finish = False, "stopped"
        report = build_report(self.brief, final, self.evidence, runtime="plain",
                              complete=complete, cost=dict(self.cost),
                              extra={"trajectory": None, "finish_reason": finish,
                                     "steps": self.steps})
        if self.sup.tripped:
            report["open_items"] = f"PARTIAL: {self.sup.tripped}"
        elif at_cap:
            note_at_cap(report, at_cap)
        return report

    def close(self):
        pass
