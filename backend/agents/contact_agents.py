"""Agent del contatto: richiesta dei dati ed estrazione strutturata."""
from __future__ import annotations
from typing import AsyncIterator
from agents import prompts
from services import llm

_LANG_NAME = {"en": "english", "it": "italian"}


def _lang(default_language: str) -> str:
    return _LANG_NAME.get(default_language, default_language)


async def ask_contact(default_language: str = "en") -> AsyncIterator[str]:
    system = prompts.load("ask_contact", default_language=_lang(default_language))
    async for token in llm.stream(system, "Ask for the contact details."):
        yield token


async def extract_contact(message: str, default_language: str = "en") -> dict:
    """{"name", "company", "email", "valid"}. Nessuna normalizzazione qui: la
    validazione è una sola, la presenza dell'e-mail, e la decide il prompt."""
    system = prompts.load("extract_contact", default_language=_lang(default_language))
    return await llm.complete_structured(system, message)
