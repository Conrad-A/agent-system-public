"""supervisor — Layer 1: mechanical, no model, every step (SPEC §5.1).

Runs INSIDE the worker process, fed by the runtime (tool calls, results,
model calls). A trip writes `trip:<rule>` to events.jsonl and STOPS the
worker through the same stop file the lead uses (the runtime files a
PARTIAL). `context` steers instead ("wrap up, report now") — once, when the
projection prompt + last growth passes CONTEXT_STEER; past CONTEXT_STOP
the check runs AFTER the call's tool
calls (context_check; ruling on run 5, 2026-09-15): a notebook write
persists, a call with tool calls trips once they ran (no further model
call), a final message is kept and filed done-at-cap. Values are
tripwires to tune from logs (§4.3); scope exempts system paths so a
`/usr/bin/python3` never trips, while a home directory or /tmp path
outside the scope does.

GENERAL RULE for a LANE (ruling on run 6, 2026-09-15): no lane trip ever
matches inside a tool result's content — a lane's results are untrusted web
text. Error loop for a lane = the same non-zero exit and error line on
three consecutive results (plain hands over the exit and stderr; the
engine's tool/result is text only, so the exit comes from the harness's
trailing marker and the line is the last output line before it); stall for
a lane = a relative OR absolute file word naming a file in the lane dir is
new ground. Run 6: the gsa successor was killed on the word "exception" in
three page slices (exit 0 each); the sbir-sttr successor cd'd to its lane
once and read page-01..09.md by relative name into a stall at step 9.
"""

import ast
import json
import os
import re
import time

import events  # noqa: E402
import lineage  # noqa: E402
from runtimes import TOOLS_DIR, is_lane, verb_path  # noqa: E402

REPEAT_N = 3            # same tool call (name + args) this many times
ERROR_LOOP_N = 3        # same error substring on consecutive results
STALL_STEPS = 8         # tool calls without new ground: a path, or for a lane a search/fetch
CONTEXT_STEER = 26_000  # prompt tokens: steer "wrap up"
CONTEXT_STOP = 32_000   # prompt tokens: stop, PARTIAL
METER_FROM = 20_000     # prompt tokens: the context meter rides every tool result past this (change 12)
CHECKPOINT_EVERY = 10   # steps between checkpoint events
SYSTEM_PREFIXES = ("/usr", "/bin", "/sbin", "/lib", "/lib64", "/etc", "/dev",
                   "/proc", "/sys", "/opt", "/var", "/run", "/snap")
WRAP_UP = ("wrap up now: you are near the context limit — stop exploring, "
           "write the REPORT block with the evidence so far, and finish")
# The scope scan reads only what can name a path (§5.1, Conrad 2026-09-15): a
# path-keyed argument whole, and a command as bare words — a quoted path first
# (spaces and all; never regex or shell syntax, so an awk program in quotes is
# not a path), then the words that are a path from their first character (a
# name character after the slash, so `/^#+[` in an awk or sed program is a
# regex literal). File contents, search queries and notebook text are never
# scanned: the step-8 flight test's scan tripped seven times on such text and
# never on a real path, so for a LANE an outside path is a `scope` EVENT the
# lead reads, never a stop — the sandbox is a lane's write fence (§4.2).
_QPATH = re.compile(r"[\"'](~?/[\w.~-][^\"'\n|{}=;&<>*?\[\]^$`\\]*|~)[\"']")   # a quoted path, spaces and all
_BARE = re.compile(r"~?/[\w.~-][^\s\"'`;|&<>()\\]*")               # a bare command word that is a path
_SEP = re.compile(r"[\s;|&<>()=]+")                                 # shell word separators
_WEB_CALL = re.compile(r"web_(?:search|fetch)\.py[^\n;&|]*")    # a lane's search or fetch, query/url included
_PATH_KEY = re.compile(r"(?i).*(path|file|dir|directory|cwd)s?$")  # a path-valued tool argument
_CMD_KEY = re.compile(r"(?i)(command|cmd)$")                        # a command-valued tool argument
_ERROR = re.compile(r"(?i)(error|exception|traceback|no such file|permission denied|"
                    r"command not found|exit code [1-9]\d*)")    # non-lane workers only (run 6)
# The harness's exit marker, the last line of every engine tool result (read
# from run 6's trajectories and the runtime binary, 2026-09-15): sdk-minimal's
# persistent bash ends every result with `[Command finished with exit code N]`;
# sdk's one-shot bash appends `[exit code: N]` on a non-zero exit only, or
# `[killed by signal: X]` / `[timed out after Nms]`. The SDK result carries no
# exit or stderr field (isError false on every run-6 result), so this is the
# engine's only exit channel; stderr is merged into the text before it.
_EXIT_MARKER = re.compile(r"\n?\[(?:Command finished with exit code (\d+)|exit code: (\d+)|"
                          r"(killed by signal: [^\]]*|timed out after [^\]]*))\]\s*$")
# A relative file word in a command (a lane's new ground once resolved against
# the lane dir and found there): `page-01.md`, `./notes.md`, `sub/x.txt` — not
# a word after a slash (an absolute path's segment or a url's host).
_REL_FILE = re.compile(r"(?<![\w/.~-])(?:\./)?[\w-][\w.-]*(?:/[\w.-]+)*\.\w+(?![\w/])")
_REASONING_LOOP = re.compile(r"(?i)(try again|let's try (that )?again|same approach|"
                             r"not sure what the user wants|unclear what (is|was) asked)")
# The lane fence (§7): the sandbox confines writes, not reads, so a lane that
# holds untrusted web content must not walk out of its directory by relative
# traversal, through the harness's DSH_HOME overlay, by the body's literal path
# or $PKG_NATIVE_CACHE_PATH (the worker's pkg cache under it — the harness
# forwards that variable to the shell; ruling 3), or by printing the file
# that holds its search keys — or the repo's `.env`. A match is a `scope` trip;
# it reads path-keyed arguments and commands only, never content.
_LANE_FENCE = re.compile(r"(?<![\w.])\.\.(?=/|$|[\s\"'`;|&)])|\$\{?DSH_HOME\b|"
                         r"\$\{?AGENT_RUNTIME\b|\$\{?PKG_NATIVE_CACHE_PATH\b|SEARCH_AUTH_FILE|"
                         r"(?<![\w-])\.env\b", re.M)


class Supervisor:
    def __init__(self, brief: dict, lid: str, wid: str, log):
        self.lid, self.wid, self.log = lid, wid, log
        self.scope = str(brief["scope"]).rstrip("/") + "/"
        self.lane = is_lane(brief)
        caps = brief.get("caps") or {}
        self.max_steps = int(caps.get("steps", 25))
        self.timeout_s = float(caps.get("timeout_s", 7200))
        self.started = time.monotonic()
        self.calls: list = []               # (name, args) history
        self.seen_paths: set = set()
        self.stale_steps = 0
        self._unborn: set = set()           # a lane's file words the last call may create (born at its result)
        self.errors: list = []              # consecutive error signatures
        self.steps = 0
        self.steered = False
        self.last_prompt = None             # the previous call's prompt: growth = prompt − last (ruling on run 5)
        self.tripped = None
        self.report_call = brief.get("report_call")   # the brief's REPORT CALL (a lane's 5th, a successor's 3rd), else None
        self.meter = ""                     # the context meter line, "" under METER_FROM (change 12)
        self._write_meter()                 # the file exists from the start: the engine's hook cats it

    # ── feeds ────────────────────────────────────────────────────────────────
    def tool_call(self, name: str, args: str) -> None:
        if self.tripped:
            return
        self.steps += 1
        key = (name, args)
        self.calls.append(key)
        if self.steps % CHECKPOINT_EVERY == 0:
            events.emit(self.lid, self.wid, "checkpoint", f"step {self.steps}")
        if self.calls.count(key) >= REPEAT_N:
            return self.trip("repeat", f"{name} {args[:120]} x{self.calls.count(key)}")
        outside = [p for p in self.paths(args) if self.is_outside(p)]
        if outside and not self.lane:
            return self.trip("scope", f"{name} touches {outside[0][:120]}")
        if outside:                         # §5.1: for a lane an event, never a stop (demoted 2026-09-15)
            events.emit(self.lid, self.wid, "scope", f"{name} touches {outside[0][:120]}")
            self.log(f"SUPERVISOR scope: {name} touches {outside[0][:120]}")
        if self.lane:
            joined = "\n".join(t for part in self.surfaces(args) for t in part)
            fence = _LANE_FENCE.search(joined)
            if fence:
                return self.trip("scope", f"{name} crosses the lane fence: {fence.group(0)!r}")
            if str(lineage.RUNTIME) in joined:       # the body by its literal path (ruling 3)
                return self.trip("scope", f"{name} crosses the lane fence: the runtime's path")
        new = set(self.paths(args)) - self.seen_paths
        if self.lane:                       # §5.1: a lane's new query or url is new ground,
            new |= set(_WEB_CALL.findall(args or "")) - self.seen_paths
            words, self._unborn = self.file_words(args)    # and so is a file word, relative or absolute (run 6)
            new |= words - self.seen_paths
        if new:
            self.seen_paths |= new
            self.stale_steps = 0
        else:
            self.stale_steps += 1
            if self.stale_steps >= STALL_STEPS:
                return self.trip("stall", f"{STALL_STEPS} steps without a new path")
        if self.steps > self.max_steps:
            return self.trip("budget", f"steps {self.steps} > cap {self.max_steps}")
        if time.monotonic() - self.started > self.timeout_s:
            return self.trip("budget", f"elapsed > timeout {self.timeout_s:.0f}s")

    def tool_result(self, text: str, exit_code=None, err=None) -> None:
        """A result's error signature, ERROR_LOOP_N alike in a row = error
        loop. A LANE's signature comes from the exit and the error line
        (plain passes the shell's exit_code and stderr; the engine passes
        text only and the harness's marker gives the exit) — never from a
        word in the content (ruling on run 6, 2026-09-15). Any other worker
        keeps the substring rule."""
        if self.tripped:
            return
        if self.lane:
            born = {f for f in self._unborn if os.path.exists(f)} - self.seen_paths
            if born:                        # the call created the file it named: new ground at its result
                self.seen_paths |= born
                self.stale_steps = 0
            self._unborn = set()
            sig = error_signature(text, exit_code, err)
        else:
            m = _ERROR.search(text or "")
            sig = m.group(0).lower() if m else None
        if sig is None:
            self.errors.clear()
            return
        self.errors.append(sig)
        if len(self.errors) >= ERROR_LOOP_N and len(set(self.errors[-ERROR_LOOP_N:])) == 1:
            self.trip("error loop", f"'{sig}' on {ERROR_LOOP_N} consecutive results")

    def model_call(self, prompt_tokens: int, reasoning: str = "") -> None:
        """Per call, as the response arrives: the 26k steer (once; never past
        the stop line, where that call ends in context_check) and the
        reasoning loop. The 32k rule is context_check, after the tool calls.
        The steer fires on PROJECTION (ruling on run 5, 2026-09-15): projected
        = this prompt + its growth over the previous call (0 on the first), so
        a worker growing 3-7k a call is told to wrap up one call before it
        crosses 26k — in run 5 the steer at 26k landed, but the answer call
        replayed 5-9k of reasoning and tripped 32k in 5 of 8 workers. The
        direct rule (prompt > 26k) is the floor: projected >= prompt."""
        if self.tripped:
            return
        growth = max(prompt_tokens - self.last_prompt, 0) if self.last_prompt is not None else 0
        self.last_prompt = prompt_tokens
        projected = prompt_tokens + growth
        self.meter = self.meter_line(prompt_tokens, growth)
        self._write_meter()
        if projected > CONTEXT_STEER and prompt_tokens <= CONTEXT_STOP and not self.steered:
            self.steered = True
            verb_path(self.lid, self.wid, "steer").write_text(WRAP_UP + "\n")
            events.emit(self.lid, self.wid, "steer",
                        f"context {prompt_tokens} (+{growth} -> {projected} projected): wrap up")
            self.log(f"SUPERVISOR steer: context {prompt_tokens} +{growth} -> {projected} projected "
                     f"> {CONTEXT_STEER}")
        if reasoning and _REASONING_LOOP.search(reasoning):
            self.trip("reasoning", _REASONING_LOOP.search(reasoning).group(0))

    def meter_line(self, prompt: int, growth: int) -> str:
        """The context meter (ruling on run 6, 2026-09-15; change 12): past
        METER_FROM, `context Nk of 32k; report by call M`. M is the number of
        the LAST tool call — the brief's unit: the message after it is the
        report, as the brief's REPORT CALL says of its 5th (a successor's
        3rd) — the smaller of the brief's report_call and the projection:
        this call makes tool call steps+1; each further call is one more
        tool call and +growth of prompt; the last call whose prompt stays
        under CONTEXT_STOP is the report, so the call before it makes the
        last tool call (diag_run6's STOP CALL — every run-6 lane spent exactly
        one call past it). Never before this call's own tool call: it is
        already made. Growth 0 (a first call) projects no limit."""
        if prompt <= METER_FROM:
            return ""
        this = self.steps + 1
        limit = None                                   # the projection; None = unbounded (growth 0)
        if growth > 0:
            # further calls k >= 0 with prompt + (k+1)*growth < CONTEXT_STOP
            further = -(-(CONTEXT_STOP - prompt) // growth) - 2
            limit = this + max(further, 0)
        bounds = [b for b in (self.report_call, limit) if b is not None]
        m = max(min(bounds), this) if bounds else this
        return f"context {prompt // 1000}k of {CONTEXT_STOP // 1000}k; report by call {m}"

    def _write_meter(self) -> None:
        """The meter file the engine's PostToolUse hook cats (change 12): the
        hooks bridge's additionalContext JSON past METER_FROM, `{}` (= nothing)
        under it. Atomic — tmp + replace — the hook may read mid-write."""
        p = verb_path(self.lid, self.wid, "meter")
        body = json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                   "additionalContext": self.meter}}) if self.meter else "{}"
        tmp = p.with_suffix(".tmp")
        tmp.write_text(body + "\n")
        os.replace(tmp, p)

    def context_check(self, prompt_tokens: int, final: bool = False):
        """The 32k rule, run AFTER the call's tool calls (ruling on run 5,
        2026-09-15: the tripping call's output is never discarded — run 5
        lost three notebook writes and filed three answers as PARTIAL). Over
        CONTEXT_STOP a call with tool calls trips `context` (no further model
        call); a final message is kept — a `done-at-cap` event, and the
        overage is returned for the report. None under the line."""
        if self.tripped or prompt_tokens <= CONTEXT_STOP:
            return None
        over = f"prompt {prompt_tokens} > {CONTEXT_STOP} (+{prompt_tokens - CONTEXT_STOP})"
        if not final:
            self.trip("context", over)
            return over
        events.emit(self.lid, self.wid, "done-at-cap", over)
        self.log(f"SUPERVISOR done at cap: {over}")
        return over

    def finish(self, reason: str) -> None:
        if reason in ("max-tokens", "error") and not self.tripped:
            self.trip("finish", f"turn/end {reason}")

    # ── helpers ──────────────────────────────────────────────────────────────
    def surfaces(self, args: str) -> tuple:
        """(absolute path-keyed values, command strings, relative path-keyed
        values): the only arguments the scope scan, the lane fence and a
        lane's file words read; every other value is content. The args are
        JSON (or the repr of a dict, which is what the engine's
        notifications carried in run 3); anything else is one command."""
        try:
            obj = json.loads(args or "")
        except (ValueError, TypeError):
            try:
                obj = ast.literal_eval(args or "")
            except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
                obj = args or ""
        if isinstance(obj, str):
            return [], [obj], []
        paths, commands, rel, stack = [], [], [], [(None, obj)]
        while stack:
            k, x = stack.pop()
            if isinstance(x, str) and k:
                if _PATH_KEY.fullmatch(k):        # one path, spaces and all
                    (paths if x.startswith(("/", "~")) else rel).append(x)
                elif _CMD_KEY.fullmatch(k):
                    commands.append(x)
            elif isinstance(x, dict):
                stack.extend(x.items())
            elif isinstance(x, list):
                stack.extend((k, v) for v in x)
        return paths, commands, rel

    def paths(self, args: str) -> list:
        """Paths a tool call can touch: path-keyed arguments whole, and a
        command's bare words — quoted paths first, then the words that are a
        path from their first character; a search or fetch call's query and
        url are content and skipped. Never file contents (§5.1)."""
        paths, commands, _ = self.surfaces(args)
        for c in commands:
            c = _WEB_CALL.sub(" ", c)
            paths += _QPATH.findall(c)
            paths += [w for w in _SEP.split(_QPATH.sub(" ", c)) if _BARE.fullmatch(w)]
        return [p.rstrip(".,:") for p in paths]

    def file_words(self, args: str) -> tuple:
        """A lane's file words (ruling on run 6, 2026-09-15): relative
        path-keyed values and a command's file-shaped words, resolved
        against the lane dir — (those naming a file there now, those that
        do not yet: the call may create them, so tool_result looks again).
        Run 6's successor reading page-01..09.md by relative name after one
        `cd` is on new ground; `t.split` in a python heredoc names no file."""
        _, commands, rel = self.surfaces(args)
        words = set(rel)
        for c in commands:
            words |= set(_REL_FILE.findall(_WEB_CALL.sub(" ", c)))
        full = {os.path.normpath(self.scope + w) for w in words}
        full = {f for f in full if f.startswith(self.scope)}
        return {f for f in full if os.path.exists(f)}, {f for f in full if not os.path.exists(f)}

    def is_outside(self, p: str) -> bool:
        if p.startswith("~"):
            return True
        if p.startswith(self.scope) or p + "/" == self.scope:
            return False
        if p == TOOLS_DIR or p.startswith(TOOLS_DIR + "/"):
            return False        # §7: tools/ is exempt (quote the path — the repo path has a space)
        return not any(p == s or p.startswith(s + "/") for s in SYSTEM_PREFIXES)

    def trip(self, rule: str, detail: str) -> None:
        self.tripped = f"trip:{rule} — {detail}"
        events.emit(self.lid, self.wid, f"trip:{rule}", detail)
        self.log(f"SUPERVISOR {self.tripped}")
        verb_path(self.lid, self.wid, "stop").write_text(self.tripped + "\n")


def exit_marker(text: str) -> tuple:
    """(exit code, the output before the marker) from the harness's trailing
    exit marker — the engine's only exit channel. No marker: (None, text).
    A signal or timeout marker is exit -1 with the marker as the output."""
    m = _EXIT_MARKER.search(text or "")
    if not m:
        return None, text or ""
    code = m.group(1) or m.group(2)
    if code is None:
        return -1, m.group(3)
    return int(code), text[:m.start()]


def error_signature(text: str, exit_code=None, err=None):
    """A lane's error signature (ruling on run 6, 2026-09-15): `exit N: <line>`
    where the line is the last line of a non-zero exit's error output —
    plain's stderr, or on the engine the output before the exit marker
    (stderr is merged into it) — never a word matched in content. None for
    exit 0, for a result with no exit at all, and for a non-zero exit that
    printed nothing: grep, diff and test say "no match" that way (run 6's
    sbir-sttr result 5), and that is not an error."""
    if exit_code is None:
        exit_code, text = exit_marker(text)
    if not exit_code:
        return None
    lines = [ln.strip() for ln in (text if err is None else err).splitlines() if ln.strip()]
    return f"exit {exit_code}: {lines[-1][:120].lower()}" if lines else None
