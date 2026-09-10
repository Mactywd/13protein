from __future__ import annotations
from typing import AsyncIterator
from models import (SessionState, Step, Event, TextEvent, ButtonsEvent, DoneEvent,
                    MessageBreakEvent)
from agents import lead_agents, qa_agents
from lib import labels

# Oltre questo numero di rilanci si passa avanti anche se la descrizione è
# povera: meglio un lead incompleto di un cliente che abbandona.
MAX_FOLLOWUPS = 2


async def handle(state: SessionState, message: str) -> AsyncIterator[Event]:
    lang = state.default_language
    if message:
        state.project_raw = f"{state.project_raw}\nU: {message}".strip()
    enough, question = await lead_agents.validate_project(state.project_raw, lang)
    if not enough and state.followup_count < MAX_FOLLOWUPS and question:
        state.followup_count += 1
        state.project_raw = f"{state.project_raw}\nA: {question}".strip()
        yield TextEvent(question)
        state.current_step = Step.PROJECT_INPUT
        yield DoneEvent(step=state.current_step.value, input_enabled=True)
        return
    state.project_description = await lead_agents.summarize_project(state.project_raw, lang)
    # Riassunto e invito alle domande sono due bolle distinte, come nel client:
    # il sentinella MESSAGE_BREAK le tiene separate anche nel transcript.
    yield TextEvent(state.project_description)
    yield MessageBreakEvent()
    async for e in start_qa(state):
        yield e


async def start_qa(state: SessionState) -> AsyncIterator[Event]:
    lang = state.default_language
    async for token in qa_agents.qa_intro(state.project_description or "", lang):
        yield TextEvent(token)
    yield ButtonsEvent(buttons=labels.buttons("quote", lang))
    state.current_step = Step.QA
    yield DoneEvent(step=state.current_step.value, input_enabled=True)
