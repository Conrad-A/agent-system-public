"""envfile — load the repo's `.env` into the process environment.

Nothing else exports `.env` (the shell does not source it), so every
plumbing entry point calls `load_env()` before reading AGENT_RUNTIME or an
API key. Existing environment values win over the file, which is what lets
the test suite point AGENT_RUNTIME at a temp dir before any import.
"""

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_env(path: Path = REPO / ".env") -> dict:
    """KEY=VALUE lines (comments and blanks skipped) -> os.environ, env wins.
    Returns what the file held; never prints anything."""
    found = {}
    if not path.exists():
        return found
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        found[key] = value
        os.environ.setdefault(key, value)
    return found
