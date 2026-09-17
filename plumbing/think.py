#!/usr/bin/env python3
"""think — the `think` preset (SPEC §4.4): one hard question, one
tool-free call at the deepest reasoning setting, a distilled answer.

Usage:  python3 plumbing/think.py "<question>"
The call's whole life is this one request — throwaway by design.
"""

import sys

from clients import DEEPSEEK, WORKER_MODEL, message  # noqa: E402

PROMPT = """You are a deep-reasoning subagent. Think the problem through
fully, then answer with a DISTILLED conclusion: the answer, the key reasoning
in a few lines, and any decisive caveat. No tools exist; no filler."""


def think(question: str) -> str:
    r = DEEPSEEK.complete(
        [{"role": "system", "content": PROMPT},
         {"role": "user", "content": question}],
        model=WORKER_MODEL, effort="max")
    return (message(r).get("content") or "(no answer)").strip()


if __name__ == "__main__":
    print(think(" ".join(sys.argv[1:])))
