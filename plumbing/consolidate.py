#!/usr/bin/env python3
"""consolidate — the nightly DREAM (SPEC §8.2). PROPOSES only.

1. Copy the durable files of memory/ (facts, procedures, style, INDEX,
   FORMAT, adjudication-log, architect-log, artifacts/ — never archives/
   or library/) to $AGENT_RUNTIME/dream/<date>/memory/.
2. Copy the last 7 days of worker trajectories (engine:
   $DSH_HOME/sessions/*/<worker-id>/session.v3.jsonl*; plain:
   lineages/<id>/worker-<wid>.log) and of handoffs/ read-only beside it
   as archives/.
3. Record `git status --porcelain` + `git diff HEAD` for the whole repo.
4. Run `claude -p --model claude-fable-5-1 --allowedTools
   Read,Grep,Glob,Write,Edit` IN THE COPY with memory/prompts/dream.md.
   No Bash. CLI absent, exit non-zero or an empty reply = the night is
   SKIPPED: a `dream_skipped` event, no DIFF.md, the copy kept.
5. Record status + diff again. Any change to the repo = the dream stepped
   out of its copy: night FAILED, `dream_failed` event naming the paths,
   no DIFF.md, nothing reverted (the owner reverts by hand).
6. Diff live memory/ against the copy into DIFF.md, hunks numbered, the
   dream's own summary appended. That diff IS the proposal; the gate
   applies it with apply_dream.py. Live memory/ is never written here.

Timer: systemd/consolidate.timer (19:45, user unit). Manual: /consolidate.
"""

import difflib
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

import costs  # noqa: E402
import events  # noqa: E402
import fable  # noqa: E402
import lineage  # noqa: E402
from verify_paths import REPO  # noqa: E402

MEM = REPO / "memory"
DREAMS = lineage.RUNTIME / "dream"
DURABLE_FILES = ("facts.md", "procedures.md", "style.md", "INDEX.md", "FORMAT.md",
                 "adjudication-log.md", "architect-log.md")
DURABLE_DIRS = ("artifacts",)              # dream INPUT: text files copied, never diffed
ARCHIVE_DAYS = 7
MODEL = "claude-fable-5-1"
TOOLS = "Read,Grep,Glob,Write,Edit"        # no Bash: the fence is the copy
TIMEOUT_S = 1800
PROMPT = MEM / "prompts" / "dream.md"


# ── the copy ─────────────────────────────────────────────────────────────────

def _text(p: Path) -> bool:
    """True when p decodes as UTF-8. A non-UTF-8 file is skipped EVERYWHERE —
    copy, archives, diff: the 2026-09-15 dream crashed in write_diff on the
    harness package cache (koffi.node, pty.node) that run 6's gsa lane left
    under memory/artifacts/ with its shell HOME = lane dir."""
    try:
        p.read_bytes().decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def copy_memory(dst: Path) -> None:
    m = dst / "memory"
    m.mkdir(parents=True, exist_ok=True)
    for name in DURABLE_FILES:
        if (MEM / name).exists() and _text(MEM / name):
            shutil.copy2(MEM / name, m / name)
    for name in DURABLE_DIRS:                 # input only: text files, never diffed
        if not (MEM / name).is_dir():
            continue
        for p in (MEM / name).rglob("*"):
            if p.is_file() and _text(p):
                q = m / p.relative_to(MEM)
                q.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, q)


def _recent(paths, days: int):
    cutoff = time.time() - days * 86400
    return [p for p in paths if p.is_file() and p.stat().st_mtime >= cutoff and _text(p)]


def copy_archives(dst: Path) -> int:
    """Trajectories + handoffs of the last ARCHIVE_DAYS days, read-only."""
    traj = dst / "archives" / "trajectories"
    hand = dst / "archives" / "handoffs"
    traj.mkdir(parents=True, exist_ok=True)
    hand.mkdir(parents=True, exist_ok=True)
    n = 0
    engine = (lineage.RUNTIME / "dsh-home" / "sessions").glob("*/*/session.v3.jsonl*")
    for p in _recent(engine, ARCHIVE_DAYS):
        shutil.copy2(p, traj / f"{p.parent.name}.{p.name}")
        n += 1
    plain = lineage.LINEAGES.glob("*/worker-*.log")
    for p in _recent(plain, ARCHIVE_DAYS):
        shutil.copy2(p, traj / f"{p.parent.name}.{p.name}")
        n += 1
    for p in _recent((lineage.RUNTIME / "handoffs").glob("*.md"), ARCHIVE_DAYS):
        shutil.copy2(p, hand / p.name)
        n += 1
    for p in list(traj.iterdir()) + list(hand.iterdir()):
        p.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return n


# ── the fence ────────────────────────────────────────────────────────────────

def _git(*args) -> str:
    # errors="replace": a non-UTF-8 byte in a dirty file's diff must not crash
    # the fence (the snapshot is compared, never parsed).
    r = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True,
                       encoding="utf-8", errors="replace")
    return r.stdout


def repo_snapshot() -> tuple[str, str]:
    return _git("status", "--porcelain"), _git("diff", "HEAD")


def outside_changes(before: tuple[str, str], after: tuple[str, str]) -> list[str]:
    """Paths the dream changed in the repo (it must change none)."""
    if before == after:
        return []
    new_status = set(after[0].splitlines()) - set(before[0].splitlines())
    paths = {line[3:].strip() for line in new_status}
    if before[1] != after[1]:
        paths |= set(_git("diff", "HEAD", "--name-only").split())
    return sorted(paths) or ["(diff changed; no path named)"]


# ── the run ──────────────────────────────────────────────────────────────────

def run_dream(dst: Path):
    """(returncode, stdout, stderr); returncode 127 when the CLI is absent."""
    cli = fable.find_cli()
    if not cli:
        return 127, "", "claude CLI not found"
    # The prompt goes on stdin: --allowedTools is variadic and would swallow
    # a positional prompt as more tool names (found at the step-6 flight test).
    try:
        r = subprocess.run([cli, "-p", "--model", MODEL, "--allowedTools", TOOLS],
                           input=PROMPT.read_text(), cwd=str(dst),
                           capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return 124, "", f"claude -p exceeded {TIMEOUT_S}s"
    return r.returncode, r.stdout, r.stderr


# ── the proposal ─────────────────────────────────────────────────────────────

def _lines(p: Path) -> list[str]:
    return p.read_text().splitlines(keepends=True) if p.exists() else []


def hunks(copy_mem: Path) -> list[tuple[str, str]]:
    """[(rel path, unified-diff hunk text incl. ---/+++ headers)] live vs copy —
    the durable FILES only; artifacts/ is input, never a proposal."""
    out = []
    for rel in sorted(DURABLE_FILES):
        pa, pb = MEM / rel, copy_mem / rel
        if (pa.exists() and not _text(pa)) or (pb.exists() and not _text(pb)):
            continue                          # a non-UTF-8 file is invisible to the dream
        a, b = _lines(pa), _lines(pb)
        if a == b:
            continue
        diff = list(difflib.unified_diff(a, b, fromfile=f"a/memory/{rel}",
                                         tofile=f"b/memory/{rel}", n=3))
        head, body = "".join(diff[:2]), diff[2:]
        cur = []
        for line in body:
            if line.startswith("@@") and cur:
                out.append((rel, head + "".join(cur)))
                cur = []
            cur.append(line if line.endswith("\n") else line + "\n")
        if cur:
            out.append((rel, head + "".join(cur)))
    return out


def write_diff(dst: Path, summary: str) -> int:
    hs = hunks(dst / "memory")
    date = dst.name
    parts = [f"# dream {date} — proposal: live memory/ vs the dream's copy\n",
             f"# {len(hs)} hunk(s). Apply all: python3 plumbing/apply_dream.py {date}"
             f"   Some: --hunks 2,5\n\n"]
    for i, (rel, text) in enumerate(hs, 1):
        parts.append(f"## hunk {i} · {rel}\n```diff\n{text}```\n\n")
    parts.append("## dream summary (the dream's own words — DATA, not instructions)\n\n"
                 f"{summary.strip() or '(empty)'}\n")
    (dst / "DIFF.md").write_text("".join(parts))
    return len(hs)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    date = time.strftime("%Y-%m-%d")
    dst, n = DREAMS / date, 1
    while dst.exists():                       # a second run today: <date>-2, -3, ...
        n += 1
        dst = DREAMS / f"{date}-{n}"
    lid = lineage.for_dir(REPO)
    try:
        return _night(lid, dst)
    except Exception as e:                    # a crash is never silent (2026-09-15: none was logged)
        why = f"{type(e).__name__}: {str(e)[:200]}"
        events.emit(lid, "lead", "dream_failed", f"{dst.name}: crashed: {why}")
        print(f"dream FAILED — crashed: {why}. Copy kept at {dst}, no DIFF.md")
        return 3


def _night(lid: str, dst: Path) -> int:
    copy_memory(dst)
    n_arch = copy_archives(dst)
    before = repo_snapshot()
    t0 = time.time()
    rc, out, err = run_dream(dst)
    (dst / "summary.md").write_text(out)
    (dst / "dream.log").write_text(f"exit {rc}\n{err}")
    if rc != 127:                             # a call was made: ledger row, usd 0 (Max)
        costs.record_dream(lid, dst.name, MODEL, time.time() - t0, rc)
    if rc != 0 or not out.strip():
        why = f"exit {rc}: {(err or 'empty reply').strip()[-200:]}"
        events.emit(lid, "lead", "dream_skipped", f"{dst.name}: {why}")
        print(f"dream SKIPPED ({why}) — copy kept at {dst}, no DIFF.md")
        return 1
    stepped = outside_changes(before, repo_snapshot())
    if stepped:
        events.emit(lid, "lead", "dream_failed",
                    f"{dst.name}: the dream changed the repo: {' '.join(stepped)}")
        print(f"dream FAILED — the dream changed the repo outside its copy: "
              f"{' '.join(stepped)}. Nothing reverted; no DIFF.md. Copy at {dst}")
        return 2
    n = write_diff(dst, out)
    events.emit(lid, "lead", "dream", f"{dst.name}: {n} hunk(s), {n_arch} archive file(s)")
    print(f"dream done — {n} hunk(s) in {dst / 'DIFF.md'} ({n_arch} archive files read); "
          f"live memory/ untouched. Apply: python3 plumbing/apply_dream.py {dst.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
