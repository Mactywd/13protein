import pytest
from unittest.mock import AsyncMock
from models import SessionState, Step
from handlers import contact
from tests.handlers.conftest import fake_stream, collect, types_of

VALID = {"name": "Mario Rossi", "company": "Rossi Nutrition",
         "email": "mario@example.com", "valid": True}


@pytest.fixture(autouse=True)
def agents(monkeypatch):
    monkeypatch.setattr(contact.contact_agents, "ask_contact", fake_stream("Nome, azienda, email?"))
    monkeypatch.setattr(contact.lead_agents, "confirm_lead", fake_stream("Riepilogo"))


async def test_invalid_contact_reasks(monkeypatch):
    monkeypatch.setattr(contact.contact_agents, "extract_contact",
                        AsyncMock(return_value={"valid": False}))
    state = SessionState(current_step=Step.CONTACT_INPUT)
    events = await collect(contact.handle_input(state, "Mario Rossi"))
    assert types_of(events) == ["TextEvent", "DoneEvent"]
    assert state.contact is None
    assert state.current_step == Step.CONTACT_INPUT


async def test_valid_contact_asks_confirmation(monkeypatch):
    monkeypatch.setattr(contact.contact_agents, "extract_contact",
                        AsyncMock(return_value=VALID))
    state = SessionState(current_step=Step.CONTACT_INPUT)
    events = await collect(contact.handle_input(state, "Mario Rossi, Rossi Nutrition, mario@example.com"))
    assert types_of(events) == ["TextEvent", "ButtonsEvent", "DoneEvent"]
    assert state.contact["email"] == "mario@example.com"
    assert [b["value"] for b in events[1].buttons] == ["confirm", "edit"]
    assert state.current_step == Step.CONTACT_CONFIRM
    assert events[-1].input_enabled is False


async def test_edit_returns_to_contact_input():
    state = SessionState(current_step=Step.CONTACT_CONFIRM, contact=dict(VALID))
    events = await collect(contact.handle_confirm(state, "edit"))
    assert state.contact is None
    assert state.current_step == Step.CONTACT_INPUT
    assert types_of(events) == ["TextEvent", "DoneEvent"]


async def test_confirm_emits_lead_info_and_completes():
    state = SessionState(current_step=Step.CONTACT_CONFIRM, profile="product_idea",
                         category="proteins", format="powders", quote_requested=True,
                         contact={"name": "Mario", "company": "Rossi", "email": "m@x.it"})
    events = await collect(contact.handle_confirm(state, "confirm"))
    assert types_of(events) == ["LeadInfoEvent", "DoneEvent"]
    assert events[0].info["contact"]["email"] == "m@x.it"
    assert events[0].info["quoteRequested"] is True
    assert state.lead_info == events[0].info
    assert state.current_step == Step.COMPLETED
    assert events[-1].step == "completed" and events[-1].input_enabled is False


async def test_unknown_value_at_confirm_reasks():
    state = SessionState(current_step=Step.CONTACT_CONFIRM)
    events = await collect(contact.handle_confirm(state, "boh"))
    assert types_of(events) == ["ButtonsEvent", "DoneEvent"]
    assert state.lead_info is None
    assert state.current_step == Step.CONTACT_CONFIRM


async def test_completed_step_repeats_closing_message():
    state = SessionState(current_step=Step.COMPLETED, default_language="it")
    events = await collect(contact.handle_completed(state, "ciao"))
    assert types_of(events) == ["TextEvent", "DoneEvent"]
    assert "13 Protein" in events[0].token
    assert events[-1].input_enabled is False
