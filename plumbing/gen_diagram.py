#!/usr/bin/env python3
"""Generate agent-system-diagram.html (v2): one self-contained page, inline
SVG, no scripts, fonts or network. The "Replicate this system" section is
KICKOFF.md's Linux block, read from that file at generation time so the two
never drift (the suite asserts it, and that the committed page equals
render()). Edit THIS file and regenerate; never the HTML by hand.

Usage:  python3 plumbing/gen_diagram.py [out.html]     (default: the repo root page)
"""
import html, sys
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO / "agent-system-diagram.html"
KICKOFF = REPO / "KICKOFF.md"

def kickoff_block(text, host):
    """The fenced block under KICKOFF.md's `## <host>` heading, verbatim: the
    lines between the bare ``` fences, joined by newlines. Raises if absent."""
    head = f"\n## {host}\n"
    i = text.index(head) + len(head)
    start = text.index("\n```\n", i) + len("\n```\n")
    end = text.index("\n```\n", start)
    return text[start:end]

linux_block = kickoff_block(KICKOFF.read_text(encoding="utf-8"), "Linux")
W = 1600
FS, LH, TFS = 10.6, 13.6, 12.2       # body font, line height, title font
PAD = 9
def esc(s): return html.escape(s, quote=False)
def wrap(text, width, size=FS):
    maxc = max(8, int(width / (0.53 * size)))
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if len(t) <= maxc: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines or [""]
class Box:
    def __init__(s, id, x, w, title, lines=(), kind="node", cols=1, title_size=TFS):
        s.id, s.x, s.w, s.title, s.lines, s.kind, s.cols, s.ts = id, x, w, title, list(lines), kind, cols, title_size
        s.y = s.h = None; s.children = []
    def layout(s, y):
        s.y = y
        tl = wrap(s.title, s.w - 2 * PAD, s.ts) if s.title else []
        cy = y + PAD + len(tl) * (LH + 1.5)
        colw = (s.w - 2 * PAD - (s.cols - 1) * 10) / s.cols
        groups = [[]]
        for ln in s.lines:
            if ln == "||": groups.append([])
            else: groups[-1].append(ln)
        s._render = []
        maxh = 0
        for gi, g in enumerate(groups):
            gx = s.x + PAD + gi * (colw + 10); gy = cy
            for ln in g:
                if ln == "": gy += LH * 0.45; continue
                kind = "p"
                if ln.startswith("## "): kind, ln = "h", ln[3:]
                elif ln.startswith("+ "): kind, ln = "ok", ln[2:]
                elif ln.startswith("- "): kind, ln = "no", ln[2:]
                elif ln.startswith("* "): kind, ln = "b", ln[2:]
                indent = 12 if kind in ("ok", "no", "b") else 0
                for i, piece in enumerate(wrap(ln, colw - indent, FS * 1.18 if kind == "h" else FS)):
                    s._render.append((gx, gy, piece, kind if i == 0 else ("p" if kind != "h" else "h"), i == 0, indent))
                    gy += LH
                if kind == "h": pass
            maxh = max(maxh, gy - y)
        s._tl = tl
        s.h = maxh + PAD
        if s.children:
            cy2 = y + PAD + len(tl) * (LH + 1.5) + (maxh - (PAD + len(tl) * (LH + 1.5))) + 4
            for row in s.children:
                rb = cy2
                for c in row:
                    c.layout(cy2); rb = max(rb, c.y + c.h)
                for c in row: c.h = rb - cy2      # equalize the row
                cy2 = rb + 8
            s.h = cy2 - y + 2
        return s.y + s.h
    def svg(s):
        o = [f'<g class="box {s.kind}" id="{s.id}"><rect x="{s.x}" y="{s.y}" width="{s.w}" height="{s.h:.0f}" rx="6"/>']
        ty = s.y + PAD + TFS
        for t in s._tl:
            o.append(f'<text class="title" x="{s.x+PAD}" y="{ty:.1f}" font-size="{s.ts}">{esc(t)}</text>'); ty += LH + 1.5
        for gx, gy, piece, kind, first, ind in s._render:
            yy = gy + FS
            if kind == "h": o.append(f'<text class="h" x="{gx}" y="{yy:.1f}">{esc(piece)}</text>')
            else:
                if first and kind in ("ok", "no", "b"):
                    g = {"ok": "✔", "no": "✘", "b": "•"}[kind]
                    o.append(f'<text class="{kind}" x="{gx}" y="{yy:.1f}">{g}</text>')
                o.append(f'<text x="{gx+ind}" y="{yy:.1f}">{esc(piece)}</text>')
        o.append('</g>')
        for row in s.children:
            for c in row: o.append(c.svg())
        return "\n".join(o)
    def pt(s, side, f=0.5):
        if side == "left": return (s.x, s.y + s.h * f)
        if side == "right": return (s.x + s.w, s.y + s.h * f)
        if side == "top": return (s.x + s.w * f, s.y)
        return (s.x + s.w * f, s.y + s.h)

def col(x, w, items, y0=75, gap=14):
    y = y0; out = []
    for it in items:
        it.x, it.w = x, w
        y = it.layout(y) + gap; out.append(it)
    return out, y - gap

# ── content ──────────────────────────────────────────────────────────────────
conrad = Box("conrad", 0, 0, "CONRAD — initiates everything (autonomy principle: 24/7 access, not autonomy) and is THE GATE: facts, dream hunks, sweep artifacts, verdicts.", [], "actor")
lead = Box("lead", 0, 0, "THE LEAD — one Claude Code session in this repo (claude-fable-5-1, Max)", [
    "Owns the plan, ambiguity, the review of every report, the gate, the lineage's state.md. Never grinds: briefs and reports only — a worker transcript never enters its context.",
    "## Hooks (.claude/settings.json)",
    "* UserPromptSubmit → status.py --line: context size from the transcript's usage (ROTATE AT NEXT BOUNDARY past 100k, ROTATE NOW past 128k), state.md age (STALE after 10 prompts), one line per running or waiting worker — the safety net under the Monitor.",
    "* SessionStart → session-start.sh: injects lineages/<id>/state.md and the newest handoff, so the next session continues without re-asking.",
    "* PreCompact → pre-compact.sh: copies state.md + the transcript tail to a handoff BEFORE compaction and logs a compaction event (a missed rotation).",
    "* /rotate → rotate.py: state.md rewritten WHOLE (decisions, open threads, focus), the handoff written to handoffs/<ts>.md, the session ends.",
    "## Commands (.claude/commands/ — each one a plumbing/ verb)",
    "/worker · /status · /steer · /stop · /resume · /check · /swarm · /consolidate · /rotate",
    "## Lineage discipline",
    "one project directory = one lineage; ONE writer (the session that opened it); state.md regenerated at every boundary; durable facts go through the gate, never into handoffs.",
], "lead")
plumb = Box("plumb", 0, 0, "plumbing/ — the verbs (stdlib, files, no service; the lead's ONLY way to a worker)", [
    "## do.py — /worker",
    "registers the brief in the lineage registry (state running) and starts worker.py with setsid: detached, it outlives the session. Never ~/Desktop as a whole.",
    "## status.py — /status",
    "registry, waiting ask-backs, recent reports, sweeps, the cost line; --line is the status-line hook",
    "## steer.py — /steer <id> <note>",
    "writes the worker's steer file",
    "## stop.py — /stop <id> [--kill]",
    "the stop file (seen within a second); --kill = SIGTERM; either way a PARTIAL report",
    "## resume.py — /resume <id> <note>",
    "a WAITING worker: the note becomes its answer file, same session; a FINISHED one: a FRESH worker briefed from its report + the note",
    "## check.py — /check <id> [rungs]",
    "runs the ladder over the scope, re-stamps the report",
    "## swarm.py — /swarm <question>",
    "plan → lanes detached, collect, sanitize, scorecard",
    "## consolidate.py · apply_dream.py",
    "the nightly dream and its gate (below)",
], "plumb")
engine = Box("engine", 0, 0, "ENGINE (default) — DeepSeek Harness via deepseek-harness-sdk (no UI)", [
    "one subprocess per worker, JSON-RPC on stdio; three methods only: initialize · session/prompt · shutdown. DSH_HOME = $AGENT_RUNTIME/dsh-home; the trajectory is sessions/<cwd>/<wid>/session.v3.jsonl",
    "## presets: profile + patch (plumbing/compositions/)",
    "* minimal = sdk-minimal + minimal.patch.yml: persistent bash only, sandbox workspace-write (writes fenced; reads fenced by the scope trip)",
    "* standard = sdk + standard.patch.yml: the wide catalog, approval never, compaction / web / ralph / workflow / telemetry OFF, bash 300 s",
    "## per worker",
    "* PKG_NATIVE_CACHE_PATH = dsh-home/cache/<wid> (the harness's native-module cache; removed at worker end) — the same dir holds hooks.json",
    "* HOOKS BRIDGE (both patches): PostToolUse → cat meter-<wid>.txt → one context line after every tool result past 20k; fail-open",
    "* steer = a follow-up prompt queued on the session by the watcher thread; stop = the watcher closes the runtime → PARTIAL",
], "engine")
plain = Box("plain", 0, 0, "PLAIN — the fallback, narrow and loud", [
    "engine → plain ONLY when the engine cannot start (import, missing binary, handshake); never mid-task, never on task failure",
    "direct API through clients.py (stdlib urllib, reasoning_content replayed), the v1 16-tool catalog, one-shot bash, a text step log; the jail is the brief's scope",
    "steer = the steer file read before each model call; stop = the stop file between steps; ask-back in-process like the engine",
    "stamped as runtime: plain (fallback — <reason>) in the report, /status and the ledger — never only in a log",
    "selection: --runtime > WORKER_RUNTIME in .env > engine",
], "plain")
chan = Box("chan", 0, 0, "Into a RUNNING engine turn — what reaches it and what does not", [
    "+ the TOOL RESULT (the model's next input; the meter line rides on it)",
    "+ the HOOK: the PostToolUse context line from the hooks bridge (the meter; the only channel past the harness into a live turn)",
    "- STEER: queued as the NEXT turn's prompt, never seen mid-turn — on the engine it is an event for the lead; the BRIEF is the only channel into a running lane. On plain, steer lands before the next call.",
], "note")
sup = Box("sup", 0, 0, "SUPERVISOR — inside the worker process: mechanical, no model, every tool call and model call (§5.1)", [
    "* repeat: the same tool call (name + args) ×3 → stop",
    "* error loop: the same error on 3 consecutive results (a LANE: the same non-zero exit + last line, never a word in content) → stop",
    "* stall: 8 steps without new ground (a path; for a lane a new search or fetched url too) → stop",
    "* budget: steps > cap · elapsed > timeout · spend > alert → stop",
    "* scope: a path outside the brief's scope → stop; for a LANE an event only — but the lane fence (.., $DSH_HOME, $AGENT_RUNTIME, SEARCH_AUTH_FILE, the repo's .env) → stop; only path-keyed args and command words are scanned, never content",
    "* finish: turn/end max-tokens or error · reasoning heuristics (try again, the plan restated)",
    "||",
    "* context > 26k on projection → STEER 'wrap up, report now' (plain: before the next call; engine: an event only)",
    "* context > 32k → STOP after the call's tool calls ran (a write persists), PARTIAL; a final message over the line is kept as done-at-cap",
    "* meter (not a trip): past 20k every tool result carries 'context Nk of 32k; report by call M' — plain appends it, the engine's hook delivers it",
    "* checkpoint every 10 steps → event. An ask-back is NOT a trip: the worker writes its question, state waiting, and blocks on the answer file",
    "ON TRIP: stop on both runtimes (the SDK has no cancel, no pause) → PARTIAL report with the evidence, registry failed, event trip:<rule> → the lead resumes with a fresh worker or takes over",
], "sup", cols=2)
worker = Box("worker", 0, 0, "WORKER PROCESS — worker.py, the adapter: brief → runtime → report · model deepseek-flash (V4.1 Flash) · cwd = the brief's scope · one process = one session (an ask-back blocks it; it outlives the lead)", [], "worker")
worker.children = [[engine, plain], [chan], [sup]]
genome = Box("genome", 0, 0, "GENOME — the repo (git, main; remote backup after every meaningful commit)", [
    "* SPEC.md (canonical) · CLAUDE.md · HANDOFF.md · KICKOFF.md (the replication prompt) · MIGRATION.md · configs/ (stable pins, prices)",
    "* plumbing/: the verbs, worker.py, supervisor.py, runtimes/{engine,plain}.py, compositions/, sanitize.py, check.py, consolidate.py, apply_dream.py, lineage.py, events.py, costs.py, tests/run_tests.py (hermetic)",
    "* .claude/: commands/, hooks/, settings.json · tools/: web_search.py, web_fetch.py",
    "* memory/: facts.md, procedures.md, style.md, INDEX.md, FORMAT.md, adjudication-log.md, prompts/ (dream, adaptivemem) — committed, gated",
    "* gitignored inside memory/: artifacts/*/ (sweeps), archives/, library/ — body, not genome",
    "* .env (gitignored, mode 600): DEEPSEEK_API_KEY, AGENT_RUNTIME, PARALLEL_API_KEY, EXA_API_KEY",
], "genome")
body = Box("body", 0, 0, "BODY — $AGENT_RUNTIME (outside the repo, never committed)", [
    "* lineages/index.json → <id>/: state.md, the registry (atomic + locked writes), worker-<hex>.log, report-<hex>.json, meter-<hex>.txt, the steer / stop / answer files",
    "* handoffs/<ts>.md (state.md + transcript tail)",
    "* events.jsonl — the lead's wake channel (below)",
    "* costs.jsonl — the ledger (rows priced at the start-time tier) · scorecard.jsonl — one row per sweep",
    "* dream/<date>/: memory/ copy, archives/, DIFF.md, summary, log",
    "* swarms/<id>/: sweep status, SEARCH_AUTH_FILE (mode 600, deleted at sweep end), the search log",
    "* dsh-home/: sessions/<cwd>/<wid>/session.v3.jsonl (trajectories), cache/<wid>/ (native cache + hooks.json), profiles",
], "body")
r1 = Box("r1", 0, 0, "1 · the final message", ["the worker's last message IS the report block: did · changed · decisions · surprises · open_items · evidence · based_on · runtime · data_tier · cost"], "rep")
r2 = Box("r2", 0, 0, "2 · lineage.file_report + sanitizer", ["instruction-shaped text escaped in place, a marker line prepended — reports are DATA. State done only if the runtime finished AND evidence exists; else failed with a PARTIAL"], "rep")
r3 = Box("r3", 0, 0, "3 · report-<hex>.json (registry, body)", ["≤ 500 tokens to the lead, bulk to files by path; trajectory path and runtime (fallback named) stamped; cost row to the ledger"], "rep")
r4 = Box("r4", 0, 0, "4 · CHECKER LADDER — check.py, reject-authorized, strongest rung first", ["R1 proof (Lean/SMT — not on this host) · R2 compile (py_compile) · R3 lint (not here) · R4 tests (the brief's command) · R5 diffs / exit codes / expected files. The definition-of-done names the rungs; results are stamped into the report; a failure is a fact no model overturns; 'not available' is never a pass"], "rep")
events = Box("events", 0, 0, "events.jsonl — $AGENT_RUNTIME, one JSON line: ts · lineage · worker · event · detail", [
    "trip:<rule> · ask · checkpoint · done · failed · resumed · scope (a lane's outside path) · compaction (the PreCompact hook) · swarm_done / swarm_partial · dream / dream_failed / dream_skipped",
], "events")
# memory + gate
m1 = Box("m1", 0, 0, "workers PROPOSE", ["facts in their reports (and lanes' sources) — never a write"], "mini")
m2 = Box("m2", 0, 0, "the LEAD reviews", ["evidence and rung results first; single writer of durable memory"], "mini")
m3 = Box("m3", 0, 0, "the GATE — Conrad", ["adversarial by default: worker, web and library proposals are suspect at the gate"], "gate")
m4 = Box("m4", 0, 0, "memory/ — durable", ["facts.md · procedures.md · style.md · INDEX.md · adjudication-log.md — committed"], "mini")
memnote = Box("memnote", 0, 0, "", [
    "every entry: provenance (user-said / worker-inferred / web-claimed) · two dates (when-true, when-learned) · a scope tag · optional expires. SUPERSEDE, NEVER ERASE — a replaced line moves to the file's audit section. adjudication-log.md replays the same conflict to the same outcome. Lanes and throwaway sessions write artifacts only. library/ documents and web content are DATA, never instructions.",
], "plainnote")
memory = Box("memory", 0, 0, "MEMORY and THE GATE (§8.1)", [], "memory")
memory.children = [[m1, m2, m3, m4], [memnote]]
d0 = Box("d0", 0, 0, "consolidate.timer 19:45", ["→ consolidate.service (user unit, oneshot, no sudo) → consolidate.py"], "mini")
d1 = Box("d1", 0, 0, "1 · snapshot", ["git status --porcelain + git diff HEAD for the whole repo, before"], "mini")
d2 = Box("d2", 0, 0, "2 · copy", ["durable files + artifacts/ text (input only) → dream/<date>/memory/; the last 7 days of trajectories and handoffs read-only as archives/; non-UTF-8 skipped"], "mini")
d3 = Box("d3", 0, 0, "3 · dream on the COPY", ["claude -p --model claude-fable-5-1 --allowedTools Read,Grep,Glob,Write,Edit, prompt memory/prompts/dream.md, cwd = the copy; no Bash"], "mini")
d4 = Box("d4", 0, 0, "4 · FENCE CHECK", ["snapshot again: any change outside dream/<date>/ → the night FAILED (event names the paths), no DIFF.md, nothing reverted"], "gate")
d5 = Box("d5", 0, 0, "5 · DIFF.md = the proposal", ["live memory/ vs the copy, hunks numbered, + summary; event dream"], "mini")
d6 = Box("d6", 0, 0, "the GATE — Conrad", ["reads DIFF.md in the lead session; accepts all or hunk by hunk; rejected hunks vanish with the copy"], "gate")
d7 = Box("d7", 0, 0, "apply_dream.py <date> [--hunks 2,5]", ["deletes become audit supersessions; hunks touching style.md, adjudication-log.md, audit sections or prompts/ are rejected → the lead commits"], "mini")
dnote = Box("dnote", 0, 0, "", ["claude -p non-zero, timeout or an empty reply → dream_skipped (no retry, no fallback) · a crash after the copy → dream_failed, exit 3 · the one thing that runs without Conrad, and it only proposes."], "plainnote")
dream = Box("dream", 0, 0, "THE DREAM — nightly, on a copy, never the live store (§8.2)", [], "dream")
dream.children = [[d0, d1, d2, d3], [d4, d5, d6, d7], [dnote]]
s0 = Box("s0", 0, 0, "/swarm <question>", ["the lead; a sweep never launches before Conrad supplies the question"], "mini")
s1 = Box("s1", 0, 0, "decomposability gate", ["independent subtasks? low merge cost? divergence acceptable? 3/3 fan out · 2/3 the lead merges · ≤1/3 no swarm"], "gate")
s2 = Box("s2", 0, 0, "plan → state.md", ["sub-questions, lane assignments, what each lane must NOT cover — written before spawning"], "mini")
s3 = Box("s3", 0, 0, "swarm.py DETACHED", ["setsid: lanes keep running through a lead rotation; caps enforced here, not by any model"], "mini")
lanes = Box("lanes", 0, 0, "≤ 5 LANES — minimal workers, depth 1 (no sub-workers), ONE successor per lane at 32k (briefed from the notebook + the partial), the second stop ends it PARTIAL", [
    "## confinement — the lethal trifecta broken",
    "* workspaceRoot = memory/artifacts/swarm-<id>/<lane>/ (gitignored) and nothing else",
    "* the lane's SHELL: env -i + PATH (tools/ first) + HOME = the lane dir (the worker PROCESS keeps the real HOME) + locale + SEARCH_AUTH_FILE + SEARCH_LOG",
    "* no repo, no .env, no DeepSeek key (the harness drops KEY|SECRET|TOKEN and DSH_* names from every shell); reads fenced by the scope rule; network only here",
    "## caps and sweep rules",
    "$1.00 per sweep · 12 calls · 1200 s per lane · wall clock 2× · concurrency ≤ 5. serial collapse (one lane > 60% of calls, once every lane has ≥ 3 and one reached 10) · fake parallelism (refused at the plan) · dead lane (no notebook write or search in 10 steps)",
    "||",
    "## tools (stdlib, first on PATH)",
    "* web_search.py — Parallel PRIMARY, Exa FALLBACK, one retry, the answering backend stamped, one JSON line per call to SEARCH_LOG",
    "* web_fetch.py — GET-only, http(s), loopback and private hosts refused, 2 MB cap; saves page-NN.md capped at 12k chars, prints the path + a 6k excerpt",
    "## notebook notes.md",
    "append after EVERY fetch in the very next call; the lane's state file; a tripped lane with no final message files its notebook as the PARTIAL",
    "## the lane brief (context starts empty)",
    "sub-question · what the other lanes cover · tool-call budget · start wide, then narrow · REPORT CALL: the message after the 5th tool call is the report (a successor's after the 3rd) · grep saved pages, never cat them whole",
], "lanes", cols=2)
c1 = Box("c1", 0, 0, "collect", ["sanitizer on every report → reports.md: N short reports, sources = url · title · the claim (unsourced claims do not count); errors are not findings"], "mini")
c2 = Box("c2", 0, 0, "the LEAD synthesizes", ["synthesis.md with a mandatory CONTRADICTIONS section; only the lead reads all N — lanes never see each other"], "mini")
c3 = Box("c3", 0, 0, "scorecard.jsonl + verdict", ["calls per lane, max share, completion, sourced lanes, searches, usd, partial, fallback_lanes; swarm.py --verdict <sweep> 1-5 (refused without the CONTRADICTIONS heading)"], "mini")
c4 = Box("c4", 0, 0, "the GATE", ["any sweep artifact enters the genome per item, through the gate — never by git add"], "gate")
swarm = Box("swarm", 0, 0, "SWARM MODE — research fan-out, opt-in (§7)", [], "swarm")
swarm.children = [[s0, s1, s2, s3], [lanes], [c1, c2, c3, c4]]

# ── layout ──────────────────────────────────────────────────────────────────
def size_children(box):
    for row in box.children:
        n = len(row); gap = 8; cw = (box.w - 2 * PAD - gap * (n - 1)) / n
        for i, c in enumerate(row):
            c.x = box.x + PAD + i * (cw + gap); c.w = cw
            size_children(c)
Y0 = 74
lead.x, lead.w = 20, 340; conrad.x, conrad.w = 20, 340
plumb.x, plumb.w = 388, 250
worker.x, worker.w = 666, 566; size_children(worker)
genome.x, genome.w = 1260, 320; body.x, body.w = 1260, 320
yc = conrad.layout(Y0); lead.layout(yc + 14)
plumb.layout(Y0); worker.layout(Y0)
yg = genome.layout(Y0); body.layout(yg + 34)
row1_bottom = max(lead.y + lead.h, plumb.y + plumb.h, worker.y + worker.h, body.y + body.h)
# report chain under plumbing + worker
ry = row1_bottom + 56
rx = 388; rw = [190, 205, 205, 216]; gapr = 12
for b, w in zip((r1, r2, r3, r4), rw):
    b.x, b.w = rx, w; b.layout(ry); rx += w + gapr
rh = max(b.h for b in (r1, r2, r3, r4))
for b in (r1, r2, r3, r4): b.h = rh
ey = ry + rh + 44
events.x, events.w = 388, 844; events.layout(ey)
row2_y = max(ey + events.h, body.y + body.h) + 40
memory.x, memory.w = 20, 760; size_children(memory); ym = memory.layout(row2_y)
dream.x, dream.w = 20, 760; size_children(dream); yd = dream.layout(ym + 16)
swarm.x, swarm.w = 800, 780; size_children(swarm); ys = swarm.layout(row2_y)
H = int(max(yd, ys) + 20)

# ── arrows ──────────────────────────────────────────────────────────────────
arrows = []
def arrow(p, q, kind, label="", via=(), lx=None, ly=None, anchor="middle"):
    pts = [p, *via, q]
    d = "M " + " L ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    if lx is None: lx = (pts[0][0] + pts[-1][0]) / 2 + 4
    if ly is None: ly = (pts[0][1] + pts[-1][1]) / 2 - 5
    arrows.append((d, kind, label, lx, ly, anchor))
# conrad -> lead
arrow(conrad.pt("bottom", 0.5), lead.pt("top", 0.5), "ctl", "prompts · /verbs · rulings", lx=205, ly=lead.y - 4)
# lead -> plumbing
arrow(lead.pt("right", 0.30), plumb.pt("left", 0.30), "ctl")
# plumbing -> worker
arrow(plumb.pt("right", 0.12), worker.pt("left", 0.12), "ctl")
arrow(plumb.pt("right", 0.42), worker.pt("left", 0.42), "ctl")
# worker -> body (registry, logs)
arrow(worker.pt("right", 0.5), body.pt("left", 0.30), "data", "", via=((1246, worker.y + worker.h * 0.5), (1246, body.y + body.h * 0.30)), lx=1246, ly=body.y + body.h * 0.30 - 8)
# supervisor -> events: from the worker's bottom-right, down the corridor to the
# right of the report chain, into the events box's right edge — never through a report box
ev_x = r4.x + r4.w + 10; ev_y = worker.y + worker.h + 26
arrow((worker.x + worker.w - 24, worker.y + worker.h), events.pt("right", 0.5), "evt", "events with evidence: trips, ask, checkpoint, done, failed",
      via=((worker.x + worker.w - 24, ev_y), (ev_x, ev_y), (ev_x, events.y + events.h * 0.5)), lx=worker.x + worker.w - 32, ly=ev_y - 6, anchor="end")
# report path
arrow((worker.x + 40, worker.y + worker.h), (r1.x + r1.w * 0.5, r1.y), "rep", "report path", via=((worker.x + 40, r1.y - 28), (r1.x + r1.w * 0.5, r1.y - 28)), lx=r1.x + r1.w * 0.5 + 8, ly=r1.y - 32, anchor="start")
arrow(r1.pt("right"), r2.pt("left"), "rep"); arrow(r2.pt("right"), r3.pt("left"), "rep"); arrow(r3.pt("right"), r4.pt("left"), "rep", "/check", lx=r3.x + r3.w + 6, ly=r3.y - 6, anchor="start")
# ladder -> lead
arrow(r4.pt("bottom", 0.5), lead.pt("bottom", 0.35), "rep", "the lead reads the report: ≤ 500 tokens, bulk by path — then resumes, re-briefs, or promotes facts through the gate", via=((r4.x + r4.w * 0.5, r4.y + r4.h + 24), (lead.x + lead.w * 0.35, r4.y + r4.h + 24)), lx=400, ly=r4.y + r4.h + 20, anchor="start")
# events -> lead (Monitor)
arrow(events.pt("left", 0.5), lead.pt("bottom", 0.75), "evt", "Monitor on events.jsonl wakes the lead\n(Claude Code re-invokes the session)\n→ one verb: steer · stop · resume · take over", via=((lead.x + lead.w * 0.75, events.y + events.h * 0.5),), lx=events.x - 8, ly=events.y + events.h * 0.5 - 16, anchor="end")
# memory chain, dream chain, swarm chain
for a, b in ((m1, m2), (m2, m3), (m3, m4)): arrow(a.pt("right"), b.pt("left"), "ctl")
for a, b in ((d0, d1), (d1, d2), (d2, d3)): arrow(a.pt("right"), b.pt("left"), "ctl")
arrow(d3.pt("bottom", 0.5), d4.pt("top", 0.5), "ctl", via=((d3.x + d3.w * 0.5, d3.y + d3.h + 4), (d4.x + d4.w * 0.5, d3.y + d3.h + 4)))
for a, b in ((d4, d5), (d5, d6), (d6, d7)): arrow(a.pt("right"), b.pt("left"), "prop" if a is d5 else "ctl")
for a, b in ((s0, s1), (s1, s2), (s2, s3)): arrow(a.pt("right"), b.pt("left"), "ctl")
arrow(s3.pt("bottom", 0.5), lanes.pt("top", 0.9), "ctl")
arrow(lanes.pt("bottom", 0.1), c1.pt("top", 0.5), "rep")
for a, b in ((c1, c2), (c2, c3), (c3, c4)): arrow(a.pt("right"), b.pt("left"), "rep" if a is c1 else "ctl")

# trace markers
marks = [(1, lead.x + lead.w - 14, lead.y + lead.h * 0.30 - 14), (2, plumb.x + plumb.w - 14, plumb.y + 26), (3, worker.x + worker.w - 14, worker.y + 14),
         (4, sup.x + sup.w - 14, sup.y + 14), (5, events.x + events.w - 14, events.y + 14), (6, r1.x + r1.w - 14, r1.y + 14), (7, r4.x + r4.w - 14, r4.y + r4.h - 14)]

svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="dtitle">',
       '<title id="dtitle">agent-system v2 architecture</title>', '<defs>']
for k in ("ctl", "evt", "rep", "prop", "data"):
    svg.append(f'<marker id="m-{k}" class="mk {k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z"/></marker>')
svg.append('</defs>')
# body/genome divider label
svg.append(f'<text class="divider" x="{genome.x + genome.w/2}" y="{genome.y + genome.h + 21}" text-anchor="middle">— committed above · never committed below —</text>')
for b in (conrad, lead, plumb, worker, genome, body, r1, r2, r3, r4, events, memory, dream, swarm):
    svg.append(b.svg())
for d, k, label, lx, ly, anchor in arrows:
    svg.append(f'<path class="arrow {k}" d="{d}" marker-end="url(#m-{k})"/>')
    if label:
        for i, part in enumerate(label.split("\n")):
            svg.append(f'<text class="alabel {k}" x="{lx:.0f}" y="{ly + i * 12:.0f}" text-anchor="{anchor}">{esc(part)}</text>')
for n, x, y in marks:
    svg.append(f'<g class="mark"><circle cx="{x:.0f}" cy="{y:.0f}" r="9"/><text x="{x:.0f}" y="{y+3.6:.0f}" text-anchor="middle">{n}</text></g>')
svg.append('</svg>')

page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent System v2 — architecture</title>
<meta name="description" content="One page: the lead, plumbing/ verbs, workers on two runtimes with the in-process supervisor, the report path and checker ladder, events and the Monitor wake, body vs genome, memory and the gate, the nightly dream, swarm mode.">
<style>
  :root {{ --bg:#f6f7fa; --panel:#ffffff; --line:#c9cfdb; --text:#1c2130; --dim:#5b6478; --muted:#eef1f6;
    --lead:#2f6fd6; --lead-soft:#e8f0fd; --plumb:#6b5cc7; --plumb-soft:#eeebfa; --worker:#c77d16; --worker-soft:#fdf3e3;
    --sup:#b04a2b; --sup-soft:#fbeae4; --genome:#3e8c5a; --genome-soft:#e6f4ea; --body:#616a7d; --body-soft:#eceff4;
    --rep:#1f8f5f; --evt:#2f6fd6; --prop:#8a4fc9; --dream:#8a4fc9; --dream-soft:#f1e9fb; --swarm:#0f8a9a; --swarm-soft:#e3f4f6;
    --gate:#c93a3a; --gate-soft:#fbe7e7; --ok:#1f8f5f; --no:#c93a3a; }}
  @media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#0f1218; --panel:#171b24; --line:#333b4d; --text:#e7eaf0; --dim:#a0a8ba; --muted:#1f2531;
    --lead:#6ea3ff; --lead-soft:#182740; --plumb:#a99bf0; --plumb-soft:#241f3d; --worker:#f0b350; --worker-soft:#2f2617;
    --sup:#f08a68; --sup-soft:#3a2119; --genome:#6fcf94; --genome-soft:#16301f; --body:#a3acc0; --body-soft:#1c2230;
    --rep:#4fd39a; --evt:#6ea3ff; --prop:#c39bf5; --dream:#c39bf5; --dream-soft:#261b38; --swarm:#4fc9d8; --swarm-soft:#10303a;
    --gate:#ff7a7a; --gate-soft:#3a1c1c; --ok:#4fd39a; --no:#ff7a7a; }} }}
  :root[data-theme="dark"] {{ --bg:#0f1218; --panel:#171b24; --line:#333b4d; --text:#e7eaf0; --dim:#a0a8ba; --muted:#1f2531;
    --lead:#6ea3ff; --lead-soft:#182740; --plumb:#a99bf0; --plumb-soft:#241f3d; --worker:#f0b350; --worker-soft:#2f2617;
    --sup:#f08a68; --sup-soft:#3a2119; --genome:#6fcf94; --genome-soft:#16301f; --body:#a3acc0; --body-soft:#1c2230;
    --rep:#4fd39a; --evt:#6ea3ff; --prop:#c39bf5; --dream:#c39bf5; --dream-soft:#261b38; --swarm:#4fc9d8; --swarm-soft:#10303a;
    --gate:#ff7a7a; --gate-soft:#3a1c1c; --ok:#4fd39a; --no:#ff7a7a; }}
  html, body {{ margin:0; background:var(--bg); color:var(--text); font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }}
  .wrap {{ max-width:1640px; margin:0 auto; padding:18px 16px 40px; }}
  h1 {{ font-size:1.35rem; margin:0 0 4px; }}
  .sub {{ color:var(--dim); font-size:.9rem; margin:0 0 10px; line-height:1.45; }}
  .legend {{ display:flex; flex-wrap:wrap; gap:8px 18px; font-size:.8rem; color:var(--dim); margin:0 0 12px; align-items:center; }}
  .legend span.k {{ display:inline-block; width:34px; height:0; border-top:2.5px solid; vertical-align:middle; margin-right:6px; }}
  .legend .ctl {{ border-color:var(--text); }} .legend .evt {{ border-color:var(--evt); border-top-style:dashed; }}
  .legend .rep {{ border-color:var(--rep); }} .legend .prop {{ border-color:var(--prop); border-top-style:dotted; }} .legend .data {{ border-color:var(--body); }}
  .legend .pill {{ padding:1px 8px; border-radius:10px; border:1px solid var(--line); background:var(--panel); }}
  svg {{ width:100%; height:auto; display:block; background:var(--panel); border:1px solid var(--line); border-radius:10px; }}
  svg text {{ font-family: inherit; font-size:{FS}px; fill:var(--text); }}
  svg .title {{ font-weight:700; }}
  svg .h {{ font-weight:700; fill:var(--dim); font-size:{FS}px; letter-spacing:.2px; text-transform:uppercase; }}
  svg .b {{ fill:var(--dim); }} svg .ok {{ fill:var(--ok); font-weight:700; }} svg .no {{ fill:var(--no); font-weight:700; }}
  svg .box rect {{ fill:var(--panel); stroke:var(--line); stroke-width:1.2; }}
  svg .actor rect {{ fill:var(--gate-soft); stroke:var(--gate); }} svg .actor .title {{ fill:var(--gate); }}
  svg .lead rect {{ fill:var(--lead-soft); stroke:var(--lead); stroke-width:1.6; }} svg .lead .title {{ fill:var(--lead); }}
  svg .plumb rect {{ fill:var(--plumb-soft); stroke:var(--plumb); }} svg .plumb .title {{ fill:var(--plumb); }}
  svg .worker rect {{ fill:var(--worker-soft); stroke:var(--worker); stroke-width:1.6; }} svg .worker .title {{ fill:var(--worker); }}
  svg .engine rect, svg .plain rect {{ fill:var(--panel); stroke:var(--worker); }} svg .engine .title, svg .plain .title {{ fill:var(--worker); }}
  svg .note rect {{ fill:var(--muted); stroke:var(--line); stroke-dasharray:4 3; }}
  svg .sup rect {{ fill:var(--sup-soft); stroke:var(--sup); }} svg .sup .title {{ fill:var(--sup); }}
  svg .genome rect {{ fill:var(--genome-soft); stroke:var(--genome); }} svg .genome .title {{ fill:var(--genome); }}
  svg .body rect {{ fill:var(--body-soft); stroke:var(--body); stroke-dasharray:6 3; }} svg .body .title {{ fill:var(--body); }}
  svg .rep rect {{ fill:var(--panel); stroke:var(--rep); }} svg .rep .title {{ fill:var(--rep); }}
  svg .events rect {{ fill:var(--lead-soft); stroke:var(--evt); stroke-dasharray:6 3; }} svg .events .title {{ fill:var(--evt); }}
  svg .memory rect {{ fill:var(--genome-soft); stroke:var(--genome); }} svg .memory .title {{ fill:var(--genome); }}
  svg .dream rect {{ fill:var(--dream-soft); stroke:var(--dream); }} svg .dream .title {{ fill:var(--dream); }}
  svg .swarm rect {{ fill:var(--swarm-soft); stroke:var(--swarm); }} svg .swarm .title {{ fill:var(--swarm); }}
  svg .lanes rect {{ fill:var(--panel); stroke:var(--swarm); }} svg .lanes .title {{ fill:var(--swarm); }}
  svg .mini rect {{ fill:var(--panel); stroke:var(--line); }} svg .mini .title {{ fill:var(--text); }}
  svg .gate rect {{ fill:var(--gate-soft); stroke:var(--gate); }} svg .gate .title {{ fill:var(--gate); }}
  svg .plainnote rect {{ fill:none; stroke:none; }} svg .plainnote text {{ fill:var(--dim); }}
  svg .divider {{ fill:var(--dim); font-size:10px; }}
  svg .arrow {{ fill:none; stroke-width:1.6; }}
  svg .arrow.ctl {{ stroke:var(--text); }} svg .arrow.evt {{ stroke:var(--evt); stroke-dasharray:6 4; }}
  svg .arrow.rep {{ stroke:var(--rep); stroke-width:2; }} svg .arrow.prop {{ stroke:var(--prop); stroke-dasharray:2 3; stroke-width:2; }}
  svg .arrow.data {{ stroke:var(--body); }}
  svg .mk.ctl path {{ fill:var(--text); }} svg .mk.evt path {{ fill:var(--evt); }} svg .mk.rep path {{ fill:var(--rep); }} svg .mk.prop path {{ fill:var(--prop); }} svg .mk.data path {{ fill:var(--body); }}
  svg .alabel {{ font-size:10px; fill:var(--dim); paint-order:stroke; stroke:var(--panel); stroke-width:4px; stroke-linejoin:round; }}
  svg .alabel.rep {{ fill:var(--rep); }} svg .alabel.evt {{ fill:var(--evt); }}
  svg .mark circle {{ fill:var(--text); }} svg .mark text {{ fill:var(--panel); font-weight:700; font-size:11px; }}
  ol.trace {{ font-size:.86rem; line-height:1.5; color:var(--text); margin:14px 0 0; padding-left:1.4em; max-width:1100px; }}
  ol.trace li {{ margin:2px 0; }}
  h2 {{ font-size:1.05rem; margin:24px 0 2px; }}
  pre.kickoff {{ font-size:.8rem; line-height:1.45; color:var(--text); background:var(--muted); border:1px solid var(--line); border-radius:8px; padding:12px 14px; margin:8px 0 0; white-space:pre-wrap; overflow-wrap:anywhere; max-width:1100px; }}
  .foot {{ color:var(--dim); font-size:.78rem; margin-top:14px; line-height:1.5; }}
</style>
</head>
<body>
<div class="wrap">
<h1>agent-system v2 — one lead directs, cheap workers grind, a human gate decides</h1>
<p class="sub">Redrawn 2026-09-16 from SPEC.md §1–§8 and §11 as built. A frontier Claude Code session is the LEAD; DeepSeek V4.1 Flash workers run detached inside DeepSeek's engine (plain loop as the fallback) with a mechanical supervisor in the same process; every report passes the sanitizer and the checker ladder; the lead is woken by events; durable memory changes only through Conrad's gate; the nightly dream proposes on a copy. The v1 (v3.1) picture is <code>docs/history/agent-system-diagram.html</code>.</p>
<div class="legend">
  <span><span class="k ctl"></span>brief · verb · control</span>
  <span><span class="k evt"></span>event · wake</span>
  <span><span class="k rep"></span>report path</span>
  <span><span class="k prop"></span>proposal (the dream's DIFF.md)</span>
  <span><span class="k data"></span>state written to the body</span>
  <span class="pill">✔ reaches a running engine turn &nbsp;·&nbsp; ✘ does not</span>
  <span class="pill">① – ⑦ one brief, from /worker to a filed report (list below)</span>
</div>
{chr(10).join(svg)}
<ol class="trace">
  <li><b>/worker "goal" --scope DIR</b> — Conrad prompts; the lead writes a brief (goal, constraints, definition-of-done with the rungs, facts, scope, preset, caps) and calls the verb.</li>
  <li><b>do.py</b> registers the brief in the lineage registry (state <i>running</i>) and starts <code>worker.py</code> with setsid — detached, it outlives the session.</li>
  <li><b>worker.py</b> reads the brief and opens the runtime: the engine (profile + patch, per-worker cache, hooks.json) — or plain, only if the engine cannot start, stamped as a fallback everywhere.</li>
  <li>The model works inside the scope. Every tool call and result passes the <b>supervisor</b>; past 20k of context the meter line rides every tool result (the hook on the engine); at 26k it steers, at 32k it stops — a trip files a PARTIAL.</li>
  <li>Trips, checkpoints and ask-backs land in <b>events.jsonl</b>; the Monitor wakes the lead, which steers, stops, resumes (an ask-back gets its answer on the same session) or takes over. The status line is the safety net.</li>
  <li>The worker's final message is the <b>report</b>: <code>lineage.file_report</code> sanitizes it and files <code>report-&lt;hex&gt;.json</code> — <i>done</i> only with evidence, else <i>failed</i> + PARTIAL.</li>
  <li><b>/check</b> runs the ladder rungs the definition-of-done named and stamps the results; the lead reads ≤ 500 tokens (bulk by path), decides, and promotes any fact only through the gate.</li>
</ol>
<h2 id="replicate">Replicate this system</h2>
<p class="sub">Clone <code>backup</code> (the private remote), open Claude Code in the repo and paste the block for your host as the first message: the session reads the kit and brings it up layer by layer, flight test by flight test. Below is the Linux block of <code>KICKOFF.md</code>, verbatim — the generator copies it from that file, so the two never drift; the macOS block is in <code>KICKOFF.md</code>.</p>
<!-- replication:begin -->
<pre class="kickoff">{esc(linux_block)}</pre>
<!-- replication:end -->
<p class="foot">Self-contained: no scripts, no fonts, no network. Generated by <code>plumbing/gen_diagram.py</code> — regenerate when a SPEC.md section or KICKOFF.md changes (the suite checks the page against both the generator and KICKOFF.md); the drawing is documentation, not a source of truth — SPEC.md wins every conflict.</p>
</div>
</body>
</html>
'''
def render():
    return page

def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}: {len(page)} bytes, {H}px tall; row1 bottom {row1_bottom:.0f}, worker bottom {worker.y+worker.h:.0f}, body 30% {body.y+body.h*0.30:.0f}, r4 right {r4.x+r4.w:.0f}, events right {events.x+events.w:.0f}, dream bottom {yd:.0f}, swarm bottom {ys:.0f}")

if __name__ == "__main__":
    main()
