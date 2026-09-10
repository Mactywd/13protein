from __future__ import annotations
from typing import AsyncIterator
from models import SessionState, Step, Event, TextEvent, ButtonsEvent, DoneEvent
from agents import qa_agents
from services import retrieval
from handlers import contact
from lib import labels


async def handle(state: SessionState, message: str) -> AsyncIterator[Event]:
    lang = state.default_language
    if message == labels.REQUEST_QUOTE:
        state.quote_requested = True
        async for e in contact.start(state):
            yield e
        return
    chunks = await retrieval.search(message, limit=3)
    state.questions_asked.append(message)
    for c in chunks:
        if c.get("doc") and c["doc"] not in state.topics_cited:
            state.topics_cited.append(c["doc"])
    async for token in qa_agents.qa_answer(message, chunks, lang):
        yield TextEvent(token)
    yield ButtonsEvent(buttons=labels.buttons("quote", lang))
    state.current_step = Step.QA
    yield DoneEvent(step=state.current_step.value, input_enabled=True)
