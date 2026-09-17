#!/usr/bin/env python3
"""web_fetch — GET one URL, save its text, print an excerpt (SPEC §7).

Usage:  web_fetch.py <url> [--max-chars 6000] [--dir DIR]

GET only — no request bodies, no other methods. http(s) only; loopback and
private-network hosts are refused (a lane reads untrusted pages and must not
be steered at local services). Body capped at 2 MB. HTML becomes text
through html2text (a tag-strip fallback if the module is missing); JSON and
plain text pass through; any other type is reported, not saved.
The text is written to page-NN.md (NN = the next free number) in DIR,
default the current directory — a lane's own directory — CAPPED at
PAGE_CAP (12,000) chars with a marker line at the end when the page was
longer (ruling 2026-09-15 on run 6: lanes cat whole 44k-char pages); the
output holds only `url:`, `status:`, `type:`, `title:` and `saved:` lines,
a `---` line and the first --max-chars characters. Grep or head the saved
file for the rest instead of fetching again (ruling 2026-09-15 after run
4: lanes were passing whole pages through context and tripped 32k within
minutes).
"""

import argparse
import html
import ipaddress
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TIMEOUT_S = 30
DEFAULT_MAX_CHARS = 6000
PAGE_CAP = 12000  # chars kept in page-NN.md; a longer page ends in a marker line (run 6 ruling)
MAX_BYTES = 2 * 1024 * 1024
USER_AGENT = "agent-system web_fetch/1 (+stdlib urllib; GET only)"
PRIVATE_NAMES = ("localhost", "localhost.localdomain", "ip6-localhost")


def private_host(host: str) -> bool:
    """True for loopback, link-local, private or unspecified addresses/names."""
    h = (host or "").strip("[]").lower()
    if not h or h in PRIVATE_NAMES or h.endswith(".localhost") or h.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_unspecified \
        or ip.is_reserved or ip.is_multicast


def check_url(url: str) -> str:
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ("http", "https"):
        raise ValueError(f"refused: only http(s) URLs (got {u.scheme or 'no'} scheme)")
    if private_host(u.hostname or ""):
        raise ValueError(f"refused: private or local host {u.hostname!r}")
    return url


def _get(url: str):
    """(status, final_url, content_type, bytes); GET, no body. An HTTP error
    returns its status and body; a transport error raises OSError."""
    req = urllib.request.Request(url, method="GET",
                                 headers={"User-Agent": USER_AGENT,
                                          "Accept": "text/html,text/plain,application/json;q=0.9,*/*;q=0.5"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            return r.status, r.geturl(), r.headers.get("Content-Type", ""), r.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        return e.code, e.geturl() or url, e.headers.get("Content-Type", ""), e.read(MAX_BYTES + 1)


def _strip_tags(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", markup)
    text = re.sub(r"(?s)<[^>]+>", " ", markup)
    return re.sub(r"[ \t]+", " ", html.unescape(text)).strip()


def to_text(content_type: str, data: bytes):
    """(title, text, kind) — kind is html | text | json | other."""
    ctype = (content_type or "").split(";")[0].strip().lower()
    charset = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    body = data.decode(charset.group(1) if charset else "utf-8", errors="replace")
    if ctype in ("text/html", "application/xhtml+xml") or (not ctype and "<html" in body[:2000].lower()):
        m = re.search(r"(?is)<title[^>]*>(.*?)</title>", body)
        title = html.unescape(" ".join(m.group(1).split())) if m else ""
        try:
            import html2text
            h = html2text.HTML2Text()
            h.ignore_images, h.body_width = True, 0
            text = h.handle(body)
        except ImportError:
            text = _strip_tags(body)
        return title, text.strip(), "html"
    if ctype in ("application/json", "text/plain", "text/markdown", "text/csv") \
            or ctype.startswith("text/"):
        return "", body.strip(), "json" if ctype == "application/json" else "text"
    return "", "", "other"


def next_page_path(d: Path) -> Path:
    """page-NN.md with NN = the next free number in d (01, 02, ...)."""
    nums = [int(m.group(1)) for f in d.glob("page-*.md") if (m := re.fullmatch(r"page-(\d+)\.md", f.name))]
    return d / f"page-{max(nums, default=0) + 1:02d}.md"


def save_page(d: Path, url: str, status: int, title: str, text: str) -> Path:
    """Write the whole text to the next page-NN.md in d; never overwrites."""
    for _ in range(3):
        path = next_page_path(d)
        try:
            with open(path, "x", encoding="utf-8") as f:
                f.write(f"# {title or url}\nurl: {url}\nstatus: {status}\n\n{text}\n")
            return path
        except FileExistsError:
            continue
    raise OSError(f"no free page-NN.md name in {d}")


def fetch(url: str, max_chars: int, save_dir=None) -> str:
    check_url(url)
    status, final, ctype, data = _get(url)
    truncated_bytes = len(data) > MAX_BYTES
    title, text, kind = to_text(ctype, data[:MAX_BYTES])
    head = [f"url: {final}", f"status: {status}", f"type: {ctype or 'unknown'}",
            f"title: {title or '-'}"]
    if kind == "other":
        return "\n".join(head + ["---", f"(not rendered: {ctype or 'unknown type'}, {len(data)} bytes)"])
    if truncated_bytes:
        text += f"\n[body capped at {MAX_BYTES} bytes]"
    total = len(text)
    if total > PAGE_CAP:
        text = text[:PAGE_CAP] + f"\n[page capped at {PAGE_CAP} of {total} chars — the rest was not saved]"
    try:
        path = save_page(Path(save_dir) if save_dir else Path.cwd(), final, status, title, text)
        saved = (f"saved: {path if save_dir else './' + path.name} "
                 + (f"({PAGE_CAP} of {total} chars — capped)" if total > PAGE_CAP else f"({total} chars)"))
    except OSError as e:
        saved = f"saved: - (could not write the page file: {e})"
    excerpt = text
    if len(text) > max_chars:
        excerpt = text[:max_chars] + (f"\n[excerpt: {max_chars} of {min(total, PAGE_CAP)} chars — "
                                      "grep the saved file for the rest]")
    return "\n".join(head + [saved, "---", excerpt])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="web_fetch.py", description=__doc__.splitlines()[0])
    ap.add_argument("url")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                    help="characters of the page printed; the whole page is in the saved file")
    ap.add_argument("--dir", default=None, help="where page-NN.md goes (default: the current directory)")
    a = ap.parse_args(argv)
    try:
        print(fetch(a.url, max(200, a.max_chars), a.dir))
    except ValueError as e:
        print(f"error: {e}")
        return 2
    except OSError as e:
        print(f"error: fetch failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
