#!/usr/bin/env python3
"""apply_dream — the gate applies a dream's DIFF.md to live memory/ (SPEC §8.2).

usage: python3 plumbing/apply_dream.py <date> [--hunks 2,5]

- Every hunk (default) or the numbered ones. Rejected hunks vanish with
  the copy; the lead commits after.
- PRESERVE UNCHANGED, enforced here: hunks touching style.md,
  adjudication-log.md, anything under prompts/, or a file's `## Audit`
  section are REJECTED. So is a whole-file deletion and a hunk whose
  context no longer matches live memory/ (it changed since the copy).
- DELETES become SUPERSESSIONS: every removed line of facts.md or
  procedures.md is appended to that file's audit section with the date
  and the reason the dream gave in its closing block
  (`file · old · new · reason`). Nothing is erased from live memory.
- CONTRADICTIONS: a closing-block line with a real `new` whose hunk was
  accepted becomes a row in adjudication-log.md.
"""

import re
import sys
import time
from pathlib import Path

import events  # noqa: E402
import lineage  # noqa: E402
from verify_paths import REPO  # noqa: E402

MEM = REPO / "memory"
DREAMS = lineage.RUNTIME / "dream"
PROTECTED = ("style.md", "adjudication-log.md")
PROTECTED_DIRS = ("prompts/",)
AUDIT_FILES = ("facts.md", "procedures.md")
AUDIT_HEADING = "## Audit — superseded entries (write contract §3d: supersede, never erase)"
HUNK_RE = re.compile(r"^## hunk (\d+) · (.+?)\n```diff\n(.*?)^```\n", re.S | re.M)
RANGE_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
REASON_RE = re.compile(r"^`?([\w./-]+\.md) · (.+?) · (.+?) · (.+?)`?$")


# ── parsing ──────────────────────────────────────────────────────────────────

def parse(diff_md: str):
    """[(n, rel, old_start, old_len, lines, whole_file_deleted)] + closing-block reasons."""
    out = []
    for m in HUNK_RE.finditer(diff_md):
        n, rel, body = int(m.group(1)), m.group(2).strip(), m.group(3)
        lines = body.splitlines(keepends=True)
        header, rest = lines[:2], lines[2:]
        r = RANGE_RE.match(rest[0]) if rest else None
        if not r:
            continue
        old_start = int(r.group(1))
        old_len = int(r.group(2)) if r.group(2) is not None else 1
        new_len = int(r.group(4)) if r.group(4) is not None else 1
        deleted = new_len == 0 and old_start == 1 and all(
            l.startswith("-") for l in rest[1:] if l.strip())
        out.append((n, rel, old_start, old_len, rest[1:], deleted))
    reasons = []
    tail = diff_md.split("## dream summary", 1)[-1]
    for line in tail.splitlines():
        m = REASON_RE.match(line.strip())
        if m:
            reasons.append(tuple(s.strip() for s in m.groups()))
    return out, reasons


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def reason_for(rel: str, removed: str, reasons) -> tuple[str, str]:
    """(reason, new) for a removed block; matched on the dream's `old` text."""
    name = Path(rel).name
    for file, old, new, why in reasons:
        if Path(file).name == name and (_norm(old)[:40] in _norm(removed)
                                        or _norm(removed)[:40] in _norm(old)):
            return why, new
    return "(no reason given by the dream)", "-"


# ── applying ─────────────────────────────────────────────────────────────────

def audit_index(lines: list[str]):
    for i, l in enumerate(lines):
        if l.startswith("## Audit"):
            return i
    return None


def check(rel: str, old_start: int, deleted: bool, hunk: list[str], live: list[str]):
    """The rejection reason, or None. Only changed lines count — context
    lines may overlap the audit heading without touching the section."""
    if Path(rel).name in PROTECTED or any(rel.startswith(d) for d in PROTECTED_DIRS):
        return "protected file (style / adjudication / prompts)"
    if deleted:
        return "whole-file deletion"
    ai = audit_index(live)
    if ai is not None:
        cur = old_start                       # 1-based old line of the next old line
        for l in hunk:
            if l[:1] == "-" and cur > ai:
                return "touches the audit section"
            if l[:1] == "+" and cur > ai + 1:
                return "touches the audit section"
            if l[:1] in (" ", "-"):
                cur += 1
    return None


def apply_hunk(live: list[str], old_start: int, old_len: int, hunk: list[str], delta: int):
    """Returns (new live lines, new delta, removed blocks) or None on mismatch."""
    old = [l[1:] for l in hunk if l[:1] in (" ", "-")]
    new = [l[1:] for l in hunk if l[:1] in (" ", "+")]
    pos = (old_start - 1 if old_len else old_start) + delta
    if live[pos:pos + len(old)] != old:
        found = None
        for cand in range(max(0, pos - 50), min(len(live), pos + 50) + 1):
            if live[cand:cand + len(old)] == old:
                found = cand
                break
        if found is None:
            return None
        pos = found
    blocks, cur = [], []
    for l in hunk:
        if l[:1] == "-":
            cur.append(l[1:])
        elif cur:
            blocks.append("".join(cur))
            cur = []
    if cur:
        blocks.append("".join(cur))
    return live[:pos] + new + live[pos + len(old):], delta + len(new) - len(old), blocks


def append_audit(lines: list[str], removed: str, reason: str, date: str) -> list[str]:
    if audit_index(lines) is None:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines += ["\n", AUDIT_HEADING + "\n", "\n"]
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    body = "".join("  " + l for l in removed.splitlines(keepends=True))
    if not body.endswith("\n"):
        body += "\n"
    return lines + [f"\n- SUPERSEDED {date} (dream: {reason}):\n", body]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__.strip().splitlines()[2])
        return 2
    date, wanted = argv[0], None
    if "--hunks" in argv:
        wanted = {int(x) for x in argv[argv.index("--hunks") + 1].split(",") if x.strip()}
    diff_p = DREAMS / date / "DIFF.md"
    if not diff_p.exists():
        print(f"no DIFF.md for dream {date} ({diff_p})")
        return 2
    hs, reasons = parse(diff_p.read_text())
    today = time.strftime("%Y-%m-%d")
    files, deltas, applied, rejected, adj_rows = {}, {}, [], [], []
    for n, rel, old_start, old_len, hunk, deleted in hs:
        if wanted is not None and n not in wanted:
            continue
        live = files.get(rel)
        if live is None:
            p = MEM / rel
            live = p.read_text().splitlines(keepends=True) if p.exists() else []
            files[rel], deltas[rel] = live, 0
        why = check(rel, old_start, deleted, hunk, live)
        if why is None:
            res = apply_hunk(live, old_start, old_len, hunk, deltas[rel])
            why = None if res else "context mismatch (live memory changed since the copy)"
        if why:
            rejected.append((n, rel, why))
            print(f"hunk {n} · {rel} · REJECTED — {why}")
            continue
        files[rel], deltas[rel], blocks = res
        for block in blocks:
            reason, new = reason_for(rel, block, reasons)
            if Path(rel).name in AUDIT_FILES:
                files[rel] = append_audit(files[rel], block, reason, today)
            if new != "-":
                adj_rows.append(f"- {today} · {Path(rel).name}: {_norm(block)[:70]} · "
                                f"{new[:70]} · {reason} (dream, applied by the gate)\n")
        applied.append((n, rel))
        print(f"hunk {n} · {rel} · APPLIED")
    for rel, lines in files.items():
        if any(a[1] == rel for a in applied):
            p = MEM / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("".join(lines))
    if adj_rows:
        with open(MEM / "adjudication-log.md", "a") as f:
            f.writelines(adj_rows)
    lid = lineage.for_dir(REPO)
    events.emit(lid, "lead", "dream_applied",
                f"{date}: applied {[a[0] for a in applied]}, rejected {[r[0] for r in rejected]}")
    print(f"applied {len(applied)}, rejected {len(rejected)}, adjudication rows {len(adj_rows)}"
          + (" — live memory/ changed: review `git diff memory/` and commit." if applied
             else " — live memory/ unchanged."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
