from __future__ import annotations
from typing import AsyncIterator
from models import SessionState, Step, Event, TextEvent, ButtonsEvent, CarouselEvent, DoneEvent
from agents import lead_agents
from services import retrieval
from lib import labels


async def _reask(state: SessionState, group: str, step: Step) -> AsyncIterator[Event]:
    """Valore non riconosciuto: rimanda gli stessi bottoni senza costo LLM."""
    yield ButtonsEvent(buttons=labels.buttons(group, state.default_language))
    state.current_step = step
    yield DoneEvent(step=step.value, input_enabled=False)


async def handle(state: SessionState, message: str) -> AsyncIterator[Event]:
    lang = state.default_language
    async for token in lead_agents.introduction(lang):
        yield TextEvent(token)
    yield ButtonsEvent(buttons=labels.buttons("profile", lang))
    state.current_step = Step.PROFILE_SELECT
    yield DoneEvent(step=state.current_step.value, input_enabled=False)


async def handle_profile(state: SessionState, message: str) -> AsyncIterator[Event]:
    if message not in labels.values("profile"):
        async for e in _reask(state, "profile", Step.PROFILE_SELECT):
            yield e
        return
    lang = state.default_language
    state.profile = message
    async for token in lead_agents.ask_category(labels.label_for("profile", message, "en"), lang):
        yield TextEvent(token)
    yield ButtonsEvent(buttons=labels.buttons("category", lang))
    state.current_step = Step.CATEGORY_SELECT
    yield DoneEvent(step=state.current_step.value, input_enabled=False)


async def handle_category(state: SessionState, message: str) -> AsyncIterator[Event]:
    if message not in labels.values("category"):
        async for e in _reask(state, "category", Step.CATEGORY_SELECT):
            yield e
        return
    lang = state.default_language
    state.category = message
    # "Non lo so ancora" non ha una pagina del knowledgebase: nessuna card.
    doc = retrieval.CATEGORY_DOC.get(message)
    card = retrieval.doc_card(doc) if doc else None
    async for token in lead_agents.ask_format(labels.label_for("category", message, "en"), lang):
        yield TextEvent(token)
    if card:
        yield CarouselEvent(cards=[{"title": card["title"], "image": "",
                                    "description": card["description"], "value": f"doc:{doc}"}])
    yield ButtonsEvent(buttons=labels.buttons("format", lang))
    state.current_step = Step.FORMAT_SELECT
    yield DoneEvent(step=state.current_step.value, input_enabled=False)


async def handle_format(state: SessionState, message: str) -> AsyncIterator[Event]:
    if message not in labels.values("format"):
        async for e in _reask(state, "format", Step.FORMAT_SELECT):
            yield e
        return
    lang = state.default_language
    state.format = message
    async for token in lead_agents.ask_project(
            labels.label_for("category", state.category or "", "en"),
            labels.label_for("format", message, "en"), lang):
        yield TextEvent(token)
    state.current_step = Step.PROJECT_INPUT
    yield DoneEvent(step=state.current_step.value, input_enabled=True)
