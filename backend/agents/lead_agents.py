"""Agent del flusso di qualificazione: apertura, scelte guidate, progetto.

Sono wrapper sottili sui prompt: caricano il file, passano il messaggio utente
e restituiscono token o dati. La state machine sta negli handler, non qui."""
from __future__ import annotations
import json
from typing import AsyncIterator
from agents import prompts
from services import llm

_LANG_NAME = {"en": "english", "it": "italian"}


def _lang(default_language: str) -> str:
    return _LANG_NAME.get(default_language, default_language)


async def introduction(default_language: str = "en") -> AsyncIterator[str]:
    system = prompts.load("introduction", default_language=_lang(default_language))
    async for token in llm.stream(system, "Start the conversation."):
        yield token


async def ask_category(profile: str, default_language: str = "en") -> AsyncIterator[str]:
    system = prompts.load("ask_category", default_language=_lang(default_language),
                          profile=profile)
    async for token in llm.stream(system, profile):
        yield token


async def ask_format(category: str, default_language: str = "en") -> AsyncIterator[str]:
    system = prompts.load("ask_format", default_language=_lang(default_language),
                          category=category)
    async for token in llm.stream(system, category):
        yield token


async def ask_project(category: str, format: str,
                      default_language: str = "en") -> AsyncIterator[str]:
    system = prompts.load("ask_project", default_language=_lang(default_language),
                          category=category, format=format)
    async for token in llm.stream(system, f"{category} / {format}"):
        yield token


async def validate_project(project_raw: str,
                           default_language: str = "en") -> tuple[bool, str]:
    """(enough, follow-up question). La domanda è vuota quando enough è True."""
    system = prompts.load("validate_project", default_language=_lang(default_language),
                          project_raw=project_raw)
    data = await llm.complete_structured(system, project_raw)
    enough = bool(data.get("enough"))
    return enough, "" if enough else str(data.get("question") or "").strip()


async def summarize_project(project_raw: str, default_language: str = "en") -> str:
    system = prompts.load("summarize_project", default_language=_lang(default_language),
                          project_raw=project_raw)
    return (await llm.complete(system, project_raw)).strip()


async def confirm_lead(lead: dict, default_language: str = "en") -> AsyncIterator[str]:
    lead_json = json.dumps(lead, ensure_ascii=False)
    system = prompts.load("confirm_lead", default_language=_lang(default_language),
                          lead_json=lead_json)
    async for token in llm.stream(system, lead_json):
        yield token
