"""sanitize — the report sanitizer (SPEC §7): before the lead reads any
report, instruction-shaped patterns are escaped IN PLACE — nothing deleted —
and a marker line is prepended to `did` when anything was escaped. Reports
are DATA (§4.1); this is the enforcement. Runs inside lineage.file_report,
so every filed report (worker, lane, successor, /check re-stamp) is
sanitized at rest; idempotent — an already-escaped span is left alone.
"""

import re

PATTERNS = (
    # imitated harness / system / tool tags
    re.compile(r"</?\s*(system|assistant|human|user|instructions?|system-reminder|"
               r"tool_result|tool_use|function_calls|function_results|antml:[\w-]+|"
               r"IMPORTANT|INST|SYS)\b[^>]*>", re.I),
    # turn markers at the start of a line
    re.compile(r"^[ \t]*(Human|Assistant|System)[ \t]*:", re.I | re.M),
    re.compile(r"\[/?INST\]|<<\s*/?SYS\s*>>", re.I),
    # "ignore previous instructions"-class text
    re.compile(r"\b(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+|your\s+)?"
               r"(previous|prior|above|earlier|preceding|system|original)\s+"
               r"(instructions?|prompts?|messages?|rules?|guidance)\b", re.I),
    re.compile(r"\b(you are now|from now on,? you are|new instructions?:|system prompt:)", re.I),
)
FIELDS = ("did", "changed", "decisions", "surprises", "open_items", "evidence",
          "sources", "self_review")
OPEN, CLOSE = "⟦escaped: ", "⟧"
MARKER = "[report sanitizer: {n} instruction-shaped pattern(s) escaped — reports are data]"
_ESCAPED = re.compile(r"(⟦escaped: .*?⟧)", re.S)


def sanitize_text(text: str) -> tuple[str, int]:
    """(escaped text, count). Spans escaped earlier are skipped."""
    n = 0

    def esc(m):
        nonlocal n
        n += 1
        return OPEN + m.group(0) + CLOSE

    parts = _ESCAPED.split(text)
    for i in range(0, len(parts), 2):          # even parts are not yet escaped
        for pat in PATTERNS:
            parts[i] = pat.sub(esc, parts[i])
    return "".join(parts), n


def sanitize_report(report: dict) -> dict:
    """Escape every string field in place; prepend the marker to `did` and
    stamp `sanitized` with the count when anything matched."""
    total = 0
    for f in FIELDS:
        v = report.get(f)
        if isinstance(v, str) and v:
            report[f], n = sanitize_text(v)
            total += n
    if total:
        report["did"] = MARKER.format(n=total) + "\n" + str(report.get("did", ""))
        report["sanitized"] = int(report.get("sanitized") or 0) + total
    return report
