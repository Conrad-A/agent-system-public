#!/usr/bin/env python3
"""web_search — CLI-first web search for swarm lanes (SPEC §7). stdlib only.

Usage:  web_search.py "<query>" [--n 10] [--mode lookup|research] [--backend parallel|exa]

One function per backend. Parallel Search (mode `basic`) is the PRIMARY,
Exa the FALLBACK: on an error OR an empty result from the primary the script
retries ONCE on the fallback and stamps which backend answered. Selection is
by which keys are present — PARALLEL_API_KEY / EXA_API_KEY in the environment,
else KEY=VALUE lines in the file named by SEARCH_AUTH_FILE (the runtime
scrubs credential-shaped names out of a lane's shell, so swarm.py hands the
keys over in that file) — so a kit with one key still works.
`--mode` is RESERVED: logged, never routed on (routing waits on scorecard
evidence, SPEC §15). Output: one header line, then one JSON object per
result. Cite the `url` field as a source — never an excerpt. If SEARCH_LOG is
set, one JSON line per backend CALL is appended there: the sweep spend cap
counts requests as well as tokens, and an errored call is still a request.
Exit 0 = results; 1 = every backend failed or came back empty; 2 = usage.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

TIMEOUT_S = 30
MAX_N = 10                                  # ten results are in the price
BACKENDS = ("parallel", "exa")              # primary first
KEY_NAMES = {"parallel": "PARALLEL_API_KEY", "exa": "EXA_API_KEY"}
BACKEND_MODE = {"parallel": "basic", "exa": "auto"}   # the row in configs/prices.md


class SearchError(Exception):
    pass


def credentials(env=None) -> dict:
    """{backend: key} from the environment, then from SEARCH_AUTH_FILE."""
    env = os.environ if env is None else env
    creds = {b: env.get(n) for b, n in KEY_NAMES.items() if env.get(n)}
    path = env.get("SEARCH_AUTH_FILE")
    if path and os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    for b, n in KEY_NAMES.items():
                        if k.strip() == n and v.strip() and b not in creds:
                            creds[b] = v.strip()
    return creds


def _post(url: str, headers: dict, body: dict):
    """(status, text) — an HTTP error returns its status and body, never raises."""
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:500]
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, str(e)


def search_parallel(query: str, n: int, key: str) -> list:
    status, text = _post("https://api.parallel.ai/v1/search", {"x-api-key": key},
                         {"objective": query, "search_queries": [query],
                          "mode": BACKEND_MODE["parallel"]})
    if status != 200:
        raise SearchError(f"HTTP {status}: {text[:160]}")
    out = []
    for r in (json.loads(text).get("results") or [])[:n]:
        out.append({"url": r.get("url"), "title": r.get("title"),
                    "date": r.get("publish_date"),
                    "excerpt": " ".join((r.get("excerpts") or [""])[0].split())[:300]})
    return out


def search_exa(query: str, n: int, key: str) -> list:
    status, text = _post("https://api.exa.ai/search", {"x-api-key": key},
                         {"query": query, "type": BACKEND_MODE["exa"], "numResults": n})
    if status != 200:
        raise SearchError(f"HTTP {status}: {text[:160]}")
    return [{"url": r.get("url"), "title": r.get("title"),
             "date": r.get("publishedDate"), "excerpt": ""}
            for r in (json.loads(text).get("results") or [])[:n]]


SEARCH = {"parallel": search_parallel, "exa": search_exa}


def _log(log_path, row: dict) -> None:
    if not log_path:
        return
    with open(log_path, "a") as f:
        f.write(json.dumps(row) + "\n")


def run(query: str, n: int, intent: str, creds: dict, backend=None, log_path=None):
    """(results, stamp). Primary first; one retry on the fallback on error or
    empty. Raises SearchError when nothing answered."""
    order = [backend] if backend else [b for b in BACKENDS if b in creds]
    if not order:
        raise SearchError("no search key: set PARALLEL_API_KEY and/or EXA_API_KEY "
                          "(or point SEARCH_AUTH_FILE at a file with those lines)")
    if backend and backend not in creds:
        raise SearchError(f"no key for {backend}")
    reasons = []
    for b in order[:2]:
        t0 = time.monotonic()
        row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "backend": b,
               "backend_mode": BACKEND_MODE[b], "intent": intent, "query": query[:300]}
        try:
            results = SEARCH[b](query, n, creds[b])
            status = "ok" if results else "empty"
        except (SearchError, ValueError) as e:
            results, status = [], "error"
            row["detail"] = str(e)[:200]
        row.update(status=status, results=len(results), ms=int((time.monotonic() - t0) * 1000))
        _log(log_path, row)
        if results:
            stamp = b if not reasons else f"{b} (fallback — {'; '.join(reasons)})"
            return results, stamp
        reasons.append(f"{b}: {row.get('detail', 'empty result')}")
    raise SearchError("; ".join(reasons))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="web_search.py", description=__doc__.splitlines()[0])
    ap.add_argument("query")
    ap.add_argument("--n", type=int, default=MAX_N, help=f"results, at most {MAX_N}")
    ap.add_argument("--mode", default="research", choices=("lookup", "research"),
                    help="reserved: recorded, not routed on")
    ap.add_argument("--backend", default=None, choices=BACKENDS, help="force one backend")
    a = ap.parse_args(argv)
    if not a.query.strip():
        ap.error("empty query")
    try:
        results, stamp = run(a.query, max(1, min(a.n, MAX_N)), a.mode, credentials(),
                             a.backend, os.environ.get("SEARCH_LOG"))
    except SearchError as e:
        print(f"error: {e}")
        return 2 if str(e).startswith("no search key") or str(e).startswith("no key for") else 1
    print(f"backend: {stamp} · results: {len(results)} · intent: {a.mode} "
          "· cite the url field, never an excerpt")
    for r in results:
        print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
