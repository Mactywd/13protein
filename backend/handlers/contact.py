from __future__ import annotations
from typing import AsyncIterator
from models import (SessionState, Step, Event, TextEvent, ButtonsEvent, LeadInfoEvent,
                    DoneEvent)
from agents import contact_agents, lead_agents
from lib import labels

COMPLETED_MSG = {
    "en": "Thank you. Your request has been sent to the 13 Protein team.",
    "it": "Grazie. La sua richiesta è stata inviata al team di 13 Protein.",
}


async def start(state: SessionState) -> AsyncIterator[Event]:
    lang = state.default_language
    async for token in contact_agents.ask_contact(lang):
        yield TextEvent(token)
    state.current_step = Step.CONTACT_INPUT
    yield DoneEvent(step=state.current_step.value, input_enabled=True)


async def handle_input(state: SessionState, message: str) -> AsyncIterator[Event]:
    lang = state.default_language
    data = await contact_agents.extract_contact(message, lang)
    if not data.get("valid"):
        async for e in start(state):
            yield e
        return
    state.contact = {"name": data.get("name"), "company": data.get("company"),
                     "email": data.get("email")}
    async for token in lead_agents.confirm_lead(state.to_lead_info(), lang):
        yield TextEvent(token)
    yield ButtonsEvent(buttons=labels.buttons("confirm", lang))
    state.current_step = Step.CONTACT_CONFIRM
    yield DoneEvent(step=state.current_step.value, input_enabled=False)


async def handle_confirm(state: SessionState, message: str) -> AsyncIterator[Event]:
    if message == labels.EDIT:
        state.contact = None
        async for e in start(state):
            yield e
        return
    if message != labels.CONFIRM:
        yield ButtonsEvent(buttons=labels.buttons("confirm", state.default_language))
        yield DoneEvent(step=Step.CONTACT_CONFIRM.value, input_enabled=False)
        return
    state.lead_info = state.to_lead_info()
    yield LeadInfoEvent(state.lead_info)
    state.current_step = Step.COMPLETED
    yield DoneEvent(step="completed", input_enabled=False)


async def handle_completed(state: SessionState, message: str) -> AsyncIterator[Event]:
    yield TextEvent(COMPLETED_MSG.get(state.default_language, COMPLETED_MSG["en"]))
    yield DoneEvent(step="completed", input_enabled=False)
