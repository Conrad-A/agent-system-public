"""clients — one OpenAI-compatible chat client per provider, stdlib only.

DeepSeek now; GLM reserved (SPEC §2: a possible factual-check lane, no
key configured). No `openai` package: a chat completion is one HTTPS POST.

DeepSeek V4.1 quirks honored here (SPEC §2, configs/stable.md):
- thinking = `thinking: {type: enabled}` + `reasoning_effort` low/high/max;
- thinking tokens count against `max_tokens` (default 16384);
- with `tools` present, the caller replays `reasoning_content` on every
  later request — `replay()` builds that assistant entry.
No retries here (adjudication log 2026-09-04: declined until the ledger
shows recurrence); the caller decides.
"""

import json
import os
import urllib.error
import urllib.request

from envfile import load_env  # noqa: E402

load_env()

WORKER_MODEL = "deepseek-flash"          # the only worker model; configs/stable.md
DEFAULT_MAX_TOKENS = 16384               # thinking counts against it


class Chat:
    """Minimal chat-completions client for an OpenAI-compatible endpoint."""

    def __init__(self, base_url: str, api_key_env: str):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.api_key_env = api_key_env

    def complete(self, messages, *, model, tools=None,
                 max_tokens=DEFAULT_MAX_TOKENS, thinking=True, effort="max",
                 timeout=600, **extra) -> dict:
        """One request; returns the parsed JSON response (choices, usage)."""
        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(f"{self.api_key_env} is not set (.env)")
        body = {"model": model, "messages": messages, "max_tokens": max_tokens,
                "thinking": {"type": "enabled" if thinking else "disabled"}}
        if thinking and effort:
            body["reasoning_effort"] = effort
        if tools:
            body["tools"] = tools
        body.update(extra)
        req = urllib.request.Request(
            self.url, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            raise RuntimeError(f"{self.url} -> HTTP {e.code}: {detail}") from None


DEEPSEEK = Chat("https://api.deepseek.com", "DEEPSEEK_API_KEY")
GLM = Chat("https://api.z.ai/api/paas/v4", "GLM_API_KEY")       # reserved; no key


def message(response: dict) -> dict:
    """The assistant message of a chat-completions response."""
    return response["choices"][0]["message"]


def replay(msg: dict) -> dict:
    """The assistant history entry for `msg`, carrying reasoning_content."""
    entry = {"role": "assistant", "content": msg.get("content") or ""}
    if msg.get("reasoning_content"):
        entry["reasoning_content"] = msg["reasoning_content"]
    if msg.get("tool_calls"):
        entry["tool_calls"] = msg["tool_calls"]
    return entry


def usage(response: dict) -> dict:
    """`usage` of a response: prompt_tokens, completion_tokens, cache fields."""
    return response.get("usage") or {}
