from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

import main
from models import SessionState, Step, TextEvent
from services import usage as usage_module


def _patch_runtime(monkeypatch, state, save_mock, transcripts_mock, add_usage_mock):
    @asynccontextmanager
    async def fake_transaction():
        yield object()

    async def fake_load(session_id, conn):
        return state

    async def noop(*a, **k):
        return None

    monkeypatch.setattr(main.db, "init_pool", noop)
    monkeypatch.setattr(main.db, "close_pool", noop)
    monkeypatch.setattr(main.db, "transaction", fake_transaction)
    monkeypatch.setattr(main.session, "load", fake_load)
    monkeypatch.setattr(main.session, "save", save_mock)
    monkeypatch.setattr(main.transcripts, "append", transcripts_mock)
    monkeypatch.setattr(main.chats, "add_usage", add_usage_mock)
    monkeypatch.setattr(main.chats, "mark_completed", AsyncMock(return_value=False))
    monkeypatch.setattr(main, "_fire_eval", Mock())


def test_silent_turn_carries_cost_into_pending_state(monkeypatch):
    """A turn with no visible bubble (no text, no cards/buttons) must not
    attach its cost to that (invisible) transcript row - it must instead be
    carried forward in state.pending_* so a later visible turn can show it."""
    state = SessionState(current_step=Step.INTRO)
    save_mock = AsyncMock()
    transcripts_mock = AsyncMock()
    add_usage_mock = AsyncMock()
    _patch_runtime(monkeypatch, state, save_mock, transcripts_mock, add_usage_mock)

    async def silent_handler(state, message):
        if False:
            yield None
        usage_module.record(
            {"cost": 0.05, "prompt_tokens": 10, "completion_tokens": 20},
            model="test-model",
        )

    monkeypatch.setattr(main, "dispatch", lambda step: silent_handler)

    with TestClient(main.app) as client:
        resp = client.post(
            "/chat",
            json={"session_id": "s1", "message": "ciao", "default_language": "it"},
        )
    assert resp.status_code == 200

    _, kwargs = transcripts_mock.call_args
    assert kwargs["cost"] is None
    assert kwargs["prompt_tokens"] is None
    assert kwargs["completion_tokens"] is None
    assert kwargs["model"] is None

    saved_state = save_mock.call_args[0][1]
    assert saved_state.pending_cost == 0.05
    assert saved_state.pending_prompt_tokens == 10
    assert saved_state.pending_completion_tokens == 20
    assert saved_state.pending_models == ["test-model"]

    add_usage_mock.assert_called_once()
    assert add_usage_mock.call_args[0][1] == 0.05


def test_visible_turn_absorbs_carried_cost_and_clears_pending(monkeypatch):
    """A turn that does produce a visible bubble must pick up any cost
    carried forward from a prior silent turn, and clear the carry afterward."""
    state = SessionState(
        current_step=Step.INTRO,
        pending_cost=0.05,
        pending_prompt_tokens=10,
        pending_completion_tokens=20,
        pending_models=["test-model"],
    )
    save_mock = AsyncMock()
    transcripts_mock = AsyncMock()
    add_usage_mock = AsyncMock()
    _patch_runtime(monkeypatch, state, save_mock, transcripts_mock, add_usage_mock)

    async def visible_handler(state, message):
        usage_module.record(
            {"cost": 0.01, "prompt_tokens": 2, "completion_tokens": 3},
            model="test-model-2",
        )
        yield TextEvent(token="Ciao")

    monkeypatch.setattr(main, "dispatch", lambda step: visible_handler)

    with TestClient(main.app) as client:
        resp = client.post(
            "/chat",
            json={"session_id": "s1", "message": "ciao", "default_language": "it"},
        )
    assert resp.status_code == 200

    _, kwargs = transcripts_mock.call_args
    assert round(kwargs["cost"], 4) == 0.06
    assert kwargs["prompt_tokens"] == 12
    assert kwargs["completion_tokens"] == 23
    assert kwargs["model"] == "test-model,test-model-2"

    saved_state = save_mock.call_args[0][1]
    assert saved_state.pending_cost == 0.0
    assert saved_state.pending_prompt_tokens == 0
    assert saved_state.pending_completion_tokens == 0
    assert saved_state.pending_models == []

    add_usage_mock.assert_called_once()
    assert add_usage_mock.call_args[0][1] == 0.01
