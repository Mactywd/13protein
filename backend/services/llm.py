"""Unico punto d'ingresso LLM per gli agent. Sceglie il provider da
settings.llm_provider a ogni chiamata (così i test possono cambiarlo)."""
from __future__ import annotations
from typing import AsyncIterator
from config import settings
from services import openrouter, llm_mock

DEFAULT_MODEL = openrouter.DEFAULT_MODEL


def _backend():
    return llm_mock if settings.llm_provider == "mock" else openrouter


def model_name() -> str:
    """Il modello effettivamente usato: serve a chi lo persiste (evaluation)."""
    return llm_mock.MODEL if settings.llm_provider == "mock" else DEFAULT_MODEL


async def stream(system: str, user: str, history: list[dict] | None = None,
                 model: str | None = None) -> AsyncIterator[str]:
    async for token in _backend().stream(system, user, history=history, model=model or DEFAULT_MODEL):
        yield token


async def complete(system: str, user: str, model: str | None = None) -> str:
    return await _backend().complete(system, user, model=model or DEFAULT_MODEL)


async def complete_structured(system: str, user: str, model: str | None = None) -> dict:
    return await _backend().complete_structured(system, user, model=model or DEFAULT_MODEL)


async def web_complete(system: str, user: str, model: str = "") -> str:
    return await _backend().web_complete(system, user, model=model)
