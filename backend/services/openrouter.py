# backend/services/openrouter.py
from __future__ import annotations
import json
import asyncio
from typing import AsyncIterator
import httpx
from config import settings
from services import usage as _usage

BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "google/gemma-4-26b-a4b-it:nitro"
TIMEOUT = 60.0

# HTTP statuses that mean "this API key is out of credits / unauthorized" —
# worth retrying the request with the fallback key.
_FALLBACK_STATUSES = {402, 401, 429}


def _headers(fallback: bool = False) -> dict:
    key = settings.openrouter_api_key_fallback if fallback else settings.openrouter_api_key
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://13protein.com",
    }


def _api_keys() -> list[bool]:
    """Key selectors to try, in order: primary then fallback (if set)."""
    keys = [False]
    if settings.openrouter_api_key_fallback:
        keys.append(True)
    return keys


async def stream(
    system: str,
    user: str,
    history: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
) -> AsyncIterator[str]:
    """Stream text tokens from OpenRouter."""
    messages = list(history or [])
    messages.append({"role": "user", "content": user})
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": True,
        "usage": {"include": True},
    }

    keys = _api_keys()
    async with httpx.AsyncClient() as client:
        for i, fallback in enumerate(keys):
            try:
                async with client.stream(
                    "POST",
                    f"{BASE_URL}/chat/completions",
                    headers=_headers(fallback),
                    json=payload,
                    timeout=TIMEOUT,
                ) as response:
                    if response.status_code in _FALLBACK_STATUSES and i < len(keys) - 1:
                        await response.aread()
                        continue
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: ") or line == "data: [DONE]":
                            continue
                        chunk = json.loads(line[6:])
                        if chunk.get("usage"):
                            _usage.record(chunk["usage"], model=model)
                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    return
            except httpx.HTTPStatusError:
                if i < len(keys) - 1:
                    continue
                raise


async def _post_json(payload: dict) -> dict:
    """POST to chat/completions, retrying with the fallback key on credit/auth
    errors, and retrying once on transient failures (5xx / network errors) so a
    single OpenRouter hiccup doesn't kill the whole turn. Returns the parsed
    JSON response."""
    keys = _api_keys()
    for attempt in range(2):
        try:
            async with httpx.AsyncClient() as client:
                for i, fallback in enumerate(keys):
                    response = await client.post(
                        f"{BASE_URL}/chat/completions",
                        headers=_headers(fallback),
                        json=payload,
                        timeout=TIMEOUT,
                    )
                    if getattr(response, "status_code", 200) in _FALLBACK_STATUSES and i < len(keys) - 1:
                        continue
                    response.raise_for_status()
                    data = response.json()
                    _usage.record(data.get("usage"), model=payload.get("model"))
                    return data
        except httpx.HTTPStatusError as exc:
            # Client errors (4xx) are not transient — don't retry them.
            if exc.response.status_code < 500 or attempt == 1:
                raise
        except httpx.TransportError:
            if attempt == 1:
                raise
        await asyncio.sleep(0.5)


async def complete(
    system: str,
    user: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """Single non-streaming call returning the raw assistant message text."""
    data = await _post_json(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "usage": {"include": True},
        }
    )
    return data["choices"][0]["message"]["content"]


WEB_SEARCH_MODEL = settings.web_search_model


async def web_complete(
    system: str,
    user: str,
    model: str = "",
) -> str:
    """Single non-streaming call to a web-search-capable model (replaces the
    Voiceflow Exa API). Returns the raw assistant message text."""
    data = await _post_json(
        {
            "model": model or WEB_SEARCH_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "usage": {"include": True},
        }
    )
    return data["choices"][0]["message"]["content"]


def _strip_json_fences(content: str) -> str:
    """Some models wrap the JSON in markdown fences despite response_format;
    strip a leading ```/```json and trailing ``` so json.loads can parse it."""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text


async def complete_structured(
    system: str,
    user: str,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Single non-streaming call expecting a JSON response."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "usage": {"include": True},
    }
    for attempt in range(2):
        data = await _post_json(payload)
        content = data["choices"][0]["message"]["content"]
        try:
            return json.loads(_strip_json_fences(content))
        except json.JSONDecodeError:
            if attempt == 1:
                raise
            await asyncio.sleep(0)  # retry once
