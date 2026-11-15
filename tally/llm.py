"""Client for any OpenAI-compatible chat completions endpoint, asked for a JSON reply.

Handles what a long batch run on a rate-limited tier needs: it paces itself from the
x-ratelimit headers, retries short 429s, and fails fast when a daily quota is exhausted.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Callable, Protocol

import httpx


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0


class LLM(Protocol):
    def complete(self, system: str, user: str) -> LLMResponse: ...


class LLMError(RuntimeError):
    pass


class QuotaExhausted(LLMError):
    """A long rate-limit wait, typically a daily quota. The run should stop and resume later."""


def parse_duration(text: str) -> float:
    """Seconds from a rate-limit header such as '705ms', '50.8s' or '11m31.2s'. 0.0 if unparseable."""
    parts = re.findall(r"(\d+(?:\.\d+)?)(ms|h|m|s)", text or "")
    if not parts or "".join(n + u for n, u in parts) != text.strip():
        return 0.0
    scale = {"h": 3600.0, "m": 60.0, "s": 1.0, "ms": 0.001}
    return sum(float(n) * scale[u] for n, u in parts)


def redact(text: str) -> str:
    """Strip account identifiers from provider error text, since errors end up in saved runs."""
    return re.sub(r"org_[A-Za-z0-9]{6,}", "org_[redacted]", text)


class OpenAICompatLLM:
    RETRYABLE = {429, 500, 502, 503, 504}
    MAX_WAIT = 90.0

    def __init__(self, base_url: str, api_key: str, model: str, *, temperature: float = 0.0,
                 timeout: float = 60.0, max_retries: int = 5, min_token_budget: int = 2500,
                 extra: dict | None = None, client: httpx.Client | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.min_token_budget = min_token_budget
        self.extra = extra or {}
        self._sleep = sleep
        self._pace = 0.0
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.Client(timeout=timeout, headers=headers)

    def complete(self, system: str, user: str) -> LLMResponse:
        payload = {"model": self.model, "temperature": self.temperature,
                   "response_format": {"type": "json_object"},
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}], **self.extra}
        last_error = "no attempt made"
        for attempt in range(self.max_retries + 1):
            if self._pace:
                self._sleep(self._pace)
                self._pace = 0.0
            started = time.perf_counter()
            try:
                resp = self._client.post(self.url, json=payload)
            except httpx.HTTPError as exc:
                last_error = f"network error: {exc}"
            else:
                if resp.status_code == 200:
                    self._pace = self._pace_from(resp.headers)
                    return self._parse(resp.json(), started)
                last_error = f"HTTP {resp.status_code}: {redact(resp.text[:300])}"
                if resp.status_code not in self.RETRYABLE:
                    break
                retry_after = resp.headers.get("retry-after", "")
                if retry_after.replace(".", "", 1).isdigit():
                    if float(retry_after) > self.MAX_WAIT:
                        raise QuotaExhausted(f"Rate limited for {retry_after}s. {last_error}")
                    self._sleep(float(retry_after) + 0.5)
                    continue
            if attempt < self.max_retries:
                self._sleep(min(2.0 ** attempt, 30.0))
        raise LLMError(last_error)

    def _pace_from(self, headers) -> float:
        remaining = headers.get("x-ratelimit-remaining-tokens", "")
        if not remaining.isdigit() or int(remaining) >= self.min_token_budget:
            return 0.0
        return min(parse_duration(headers.get("x-ratelimit-reset-tokens", "")), self.MAX_WAIT)

    @staticmethod
    def _parse(data: dict, started: float) -> LLMResponse:
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected response shape: {str(data)[:300]}") from exc
        usage = data.get("usage") or {}
        return LLMResponse(content=message.get("content") or "",
                           prompt_tokens=usage.get("prompt_tokens", 0) or 0,
                           completion_tokens=usage.get("completion_tokens", 0) or 0,
                           latency_ms=int((time.perf_counter() - started) * 1000))


class ScriptedLLM:
    """Test double: returns the given replies in order. An Exception item is raised instead."""

    def __init__(self, replies: list):
        self._replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> LLMResponse:
        self.calls.append((system, user))
        if not self._replies:
            raise LLMError("ScriptedLLM ran out of replies.")
        item = self._replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, LLMResponse) else LLMResponse(content=item, prompt_tokens=100,
                                                                      completion_tokens=20)
