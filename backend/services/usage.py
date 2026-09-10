# backend/services/usage.py
"""Per-request OpenRouter cost accumulator.

main.py calls start() at the beginning of a turn and reset(token) at the end,
reading current() to persist the total. OpenRouter call sites call record()
with the `usage` block from each response. When no accumulator is active
(record() outside a started context), record() is a no-op so unit tests and
non-request callers are unaffected.
"""
from __future__ import annotations
import contextvars
from dataclasses import dataclass, field


@dataclass
class Usage:
    cost: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    models: set[str] = field(default_factory=set)


_current: contextvars.ContextVar[Usage | None] = contextvars.ContextVar(
    "openrouter_usage", default=None
)


def start() -> contextvars.Token:
    """Begin accumulating in the current context. Returns a token for reset()."""
    return _current.set(Usage())


def reset(token: contextvars.Token) -> None:
    _current.reset(token)


def current() -> Usage:
    """The active accumulator, or a zeroed Usage if none is active."""
    return _current.get() or Usage()


def record(usage: dict | None, model: str | None = None) -> None:
    """Add one OpenRouter `usage` block to the active accumulator (no-op if none)."""
    acc = _current.get()
    if acc is None:
        return
    if model:
        acc.models.add(model)
    if not usage:
        return
    acc.cost += float(usage.get("cost", 0) or 0)
    acc.prompt_tokens += int(usage.get("prompt_tokens", 0) or 0)
    acc.completion_tokens += int(usage.get("completion_tokens", 0) or 0)
