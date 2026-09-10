import pytest
from models import SessionState, Step, TextEvent, ButtonsEvent, CarouselEvent, DoneEvent
from handlers import intro
from tests.handlers.conftest import fake_stream, collect, types_of


@pytest.fixture(autouse=True)
def agents(monkeypatch):
    monkeypatch.setattr(intro.lead_agents, "introduction", fake_stream("Benvenuto"))
    monkeypatch.setattr(intro.lead_agents, "ask_category", fake_stream("Cosa vuole creare?"))
    monkeypatch.setattr(intro.lead_agents, "ask_format", fake_stream("Che formato?"))
    monkeypatch.setattr(intro.lead_agents, "ask_project", fake_stream("Mi racconti il progetto"))


async def test_handle_opens_with_text_and_profile_buttons():
    state = SessionState()
    events = await collect(intro.handle(state, ""))
    assert types_of(events) == ["TextEvent", "ButtonsEvent", "DoneEvent"]
    assert [b["value"] for b in events[1].buttons][0] == "product_idea"
    assert state.current_step == Step.PROFILE_SELECT
    assert events[-1].input_enabled is False


async def test_handle_profile_stores_value_and_offers_categories():
    state = SessionState(current_step=Step.PROFILE_SELECT)
    events = await collect(intro.handle_profile(state, "new_brand"))
    assert state.profile == "new_brand"
    assert state.current_step == Step.CATEGORY_SELECT
    assert "proteins" in [b["value"] for b in events[1].buttons]


async def test_handle_profile_reasks_on_unknown_value():
    state = SessionState(current_step=Step.PROFILE_SELECT)
    events = await collect(intro.handle_profile(state, "qualcosa"))
    assert types_of(events) == ["ButtonsEvent", "DoneEvent"]
    assert state.profile is None
    assert state.current_step == Step.PROFILE_SELECT


async def test_handle_category_emits_carousel_card(monkeypatch):
    monkeypatch.setattr(intro.retrieval, "doc_card",
                        lambda doc: {"title": "Protein Powders", "description": "d", "url": "u"})
    state = SessionState(current_step=Step.CATEGORY_SELECT)
    events = await collect(intro.handle_category(state, "proteins"))
    assert types_of(events) == ["TextEvent", "CarouselEvent", "ButtonsEvent", "DoneEvent"]
    assert events[1].cards[0]["value"] == "doc:protein-powders"
    assert state.category == "proteins"
    assert state.current_step == Step.FORMAT_SELECT


async def test_handle_category_not_sure_has_no_carousel(monkeypatch):
    monkeypatch.setattr(intro.retrieval, "doc_card",
                        lambda doc: pytest.fail("nessuna card per not_sure_yet"))
    state = SessionState(current_step=Step.CATEGORY_SELECT)
    events = await collect(intro.handle_category(state, "not_sure_yet"))
    assert "CarouselEvent" not in types_of(events)
    assert state.category == "not_sure_yet"


async def test_handle_category_reasks_on_unknown_value():
    state = SessionState(current_step=Step.CATEGORY_SELECT)
    events = await collect(intro.handle_category(state, "boh"))
    assert types_of(events) == ["ButtonsEvent", "DoneEvent"]
    assert state.category is None


async def test_handle_format_opens_free_text_step():
    state = SessionState(current_step=Step.FORMAT_SELECT, category="proteins")
    events = await collect(intro.handle_format(state, "powders"))
    assert types_of(events) == ["TextEvent", "DoneEvent"]
    assert state.format == "powders"
    assert state.current_step == Step.PROJECT_INPUT
    assert events[-1].input_enabled is True


async def test_handle_format_reasks_on_unknown_value():
    state = SessionState(current_step=Step.FORMAT_SELECT)
    events = await collect(intro.handle_format(state, "vetro"))
    assert types_of(events) == ["ButtonsEvent", "DoneEvent"]
    assert state.format is None


async def test_buttons_are_localized():
    state = SessionState(default_language="it")
    events = await collect(intro.handle(state, ""))
    assert events[1].buttons[0]["label"] == "Ho un'idea di prodotto"
