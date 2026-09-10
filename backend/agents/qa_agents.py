"""Agent delle domande libere: apertura dello step e risposta con il contesto
recuperato dal knowledgebase. Il modello vede solo i chunk passati qui."""
from __future__ import annotations
from typing import AsyncIterator
from agents import prompts
from services import llm, retrieval

_LANG_NAME = {"en": "english", "it": "italian"}


def _lang(default_language: str) -> str:
    return _LANG_NAME.get(default_language, default_language)


async def qa_intro(project_description: str,
                   default_language: str = "en") -> AsyncIterator[str]:
    system = prompts.load("qa_intro", default_language=_lang(default_language),
                          project_description=project_description)
    async for token in llm.stream(system, project_description or "Open the questions step."):
        yield token


def build_question_message(question: str, chunks: list[dict]) -> str:
    """Il messaggio utente che l'agent invia: domanda e contesto numerato.

    Il formato `[n] Title (url)` è letto anche dal provider mock, che cita i
    titoli trovati: cambiarlo qui vuol dire cambiarlo in services/llm_mock.py."""
    return f"Question: {question}\n\nContext:\n{retrieval.format_context(chunks)}"


async def qa_answer(question: str, chunks: list[dict],
                    default_language: str = "en") -> AsyncIterator[str]:
    system = prompts.load("qa_answer", default_language=_lang(default_language))
    async for token in llm.stream(system, build_question_message(question, chunks)):
        yield token
