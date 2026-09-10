import pytest
from unittest.mock import AsyncMock
from models import SessionState, Step
from handlers import project
from tests.handlers.conftest import fake_stream, collect, types_of


@pytest.fixture(autouse=True)
def agents(monkeypatch):
    monkeypatch.setattr(project.qa_agents, "qa_intro", fake_stream("Ha domande?"))
    monkeypatch.setattr(project.lead_agents, "summarize_project",
                        AsyncMock(return_value="Una whey per palestre."))


async def test_first_turn_asks_one_followup(monkeypatch):
    monkeypatch.setattr(project.lead_agents, "validate_project",
                        AsyncMock(return_value=(False, "Per quale mercato?")))
    state = SessionState(current_step=Step.PROJECT_INPUT)
    events = await collect(project.handle(state, "A whey protein for gyms"))
    assert types_of(events) == ["TextEvent", "DoneEvent"]
    assert events[0].token == "Per quale mercato?"
    assert state.followup_count == 1
    assert state.current_step == Step.PROJECT_INPUT
    assert events[-1].input_enabled is True
    assert "U: A whey protein for gyms" in state.project_raw
    assert "A: Per quale mercato?" in state.project_raw


async def test_enough_moves_to_qa_with_summary_and_break(monkeypatch):
    monkeypatch.setattr(project.lead_agents, "validate_project",
                        AsyncMock(return_value=(True, "")))
    state = SessionState(current_step=Step.PROJECT_INPUT, followup_count=1,
                         project_raw="U: prima risposta")
    events = await collect(project.handle(state, "Mercato Italia, barattoli da 2 kg"))
    assert types_of(events) == ["TextEvent", "MessageBreakEvent", "TextEvent",
                                "ButtonsEvent", "DoneEvent"]
    assert events[0].token == "Una whey per palestre."
    assert state.project_description == "Una whey per palestre."
    assert [b["value"] for b in events[3].buttons] == ["request_quote"]
    assert state.current_step == Step.QA
    assert events[-1].input_enabled is True


async def test_followup_cap_forces_progress(monkeypatch):
    monkeypatch.setattr(project.lead_agents, "validate_project",
                        AsyncMock(return_value=(False, "Ancora poco chiaro")))
    state = SessionState(current_step=Step.PROJECT_INPUT,
                         followup_count=project.MAX_FOLLOWUPS)
    events = await collect(project.handle(state, "boh"))
    assert state.current_step == Step.QA
    assert state.followup_count == project.MAX_FOLLOWUPS
    assert "ButtonsEvent" in types_of(events)


async def test_empty_message_does_not_pollute_transcript(monkeypatch):
    monkeypatch.setattr(project.lead_agents, "validate_project",
                        AsyncMock(return_value=(True, "")))
    state = SessionState(current_step=Step.PROJECT_INPUT)
    await collect(project.handle(state, ""))
    assert state.project_raw == ""
