import pytest
from unittest.mock import AsyncMock
from models import SessionState, Step
from handlers import qa
from tests.handlers.conftest import fake_stream, collect, types_of

CHUNKS = [
    {"doc": "quality", "page_title": "Quality", "url": "u", "text": "t"},
    {"doc": "quality", "page_title": "Quality", "url": "u", "text": "t2"},
    {"doc": "about-us", "page_title": "About Us", "url": "u", "text": "t3"},
]


@pytest.fixture(autouse=True)
def agents(monkeypatch):
    monkeypatch.setattr(qa.qa_agents, "qa_answer", fake_stream("Risposta"))
    monkeypatch.setattr(qa.contact.contact_agents, "ask_contact", fake_stream("Nome, azienda, email?"))
    monkeypatch.setattr(qa.retrieval, "search", AsyncMock(return_value=CHUNKS))


async def test_question_answers_and_records_topics():
    state = SessionState(current_step=Step.QA)
    events = await collect(qa.handle(state, "Are you certified?"))
    assert types_of(events) == ["TextEvent", "ButtonsEvent", "DoneEvent"]
    assert state.questions_asked == ["Are you certified?"]
    assert state.topics_cited == ["quality", "about-us"]   # dedup, ordine di citazione
    assert state.current_step == Step.QA
    assert events[-1].input_enabled is True


async def test_second_question_does_not_duplicate_topics():
    state = SessionState(current_step=Step.QA, topics_cited=["quality"])
    await collect(qa.handle(state, "E i formati?"))
    assert state.topics_cited == ["quality", "about-us"]
    assert len(state.questions_asked) == 1


async def test_request_quote_moves_to_contact():
    state = SessionState(current_step=Step.QA)
    events = await collect(qa.handle(state, "request_quote"))
    assert state.quote_requested is True
    assert state.current_step == Step.CONTACT_INPUT
    assert types_of(events) == ["TextEvent", "DoneEvent"]
    assert events[-1].input_enabled is True


async def test_no_results_still_answers(monkeypatch):
    monkeypatch.setattr(qa.retrieval, "search", AsyncMock(return_value=[]))
    state = SessionState(current_step=Step.QA)
    events = await collect(qa.handle(state, "zzz"))
    assert types_of(events) == ["TextEvent", "ButtonsEvent", "DoneEvent"]
    assert state.topics_cited == []
