from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

import main
from models import SessionState, Step


def _patch_runtime(
    monkeypatch,
    state,
    save_mock,
    mark_completed_mock=None,
    fire_eval_mock=None,
    is_testing=True,
):
    @asynccontextmanager
    async def fake_transaction():
        yield object()

    async def fake_load(session_id, conn):
        return state

    async def fake_is_testing(session_id, conn):
        return is_testing

    async def noop(*a, **k):
        return None

    monkeypatch.setattr(main.db, "init_pool", noop)
    monkeypatch.setattr(main.db, "close_pool", noop)
    monkeypatch.setattr(main.db, "transaction", fake_transaction)
    monkeypatch.setattr(main.session, "load", fake_load)
    monkeypatch.setattr(main.session, "is_testing", fake_is_testing)
    monkeypatch.setattr(main.session, "save", save_mock)
    monkeypatch.setattr(
        main.chats, "mark_completed", mark_completed_mock or AsyncMock(return_value=True)
    )
    monkeypatch.setattr(main, "_fire_eval", fire_eval_mock or Mock())


def test_skip_fills_unanswered_fields_from_default_facsimile(monkeypatch):
    state = SessionState(current_step=Step.PROJECT_INPUT)  # profilo mai scelto
    save_mock = AsyncMock()
    mark_completed_mock = AsyncMock(return_value=True)
    fire_eval_mock = Mock()
    _patch_runtime(monkeypatch, state, save_mock, mark_completed_mock, fire_eval_mock)

    with TestClient(main.app) as client:
        resp = client.post("/chat/s1/skip")

    assert resp.status_code == 200
    info = resp.json()["lead_info"]
    assert info["profile"] == "product_idea"
    assert info["contact"]["email"] == "mario@example.com"
    assert info["quoteRequested"] is True
    assert save_mock.call_args[1]["is_testing"] is True
    saved_state = save_mock.call_args[0][1]
    assert saved_state.current_step == Step.COMPLETED

    assert mark_completed_mock.call_count == 1
    assert mark_completed_mock.call_args[0][0] == "s1"
    fire_eval_mock.assert_called_once_with("s1")


def test_skip_keeps_answered_fields_and_uses_matching_profile_facsimile(monkeypatch):
    state = SessionState(
        current_step=Step.QA,
        profile="new_brand",
        category="proteins",
        topics_cited=["quality"],
    )
    save_mock = AsyncMock()
    _patch_runtime(monkeypatch, state, save_mock)

    with TestClient(main.app) as client:
        resp = client.post("/chat/s1/skip")

    assert resp.status_code == 200
    info = resp.json()["lead_info"]
    assert info["category"] == "proteins"       # risposto -> tenuto
    assert info["topicsCited"] == ["quality"]   # risposto (parziale) -> tenuto, non riempito
    assert info["format"] == "stick_packs"      # sentinella -> dal facsimile new_brand


def test_skip_does_not_fire_eval_when_already_completed(monkeypatch):
    """If mark_completed returns False (session was already completata), no
    duplicate evaluation should be fired — same contract as the /chat handler."""
    state = SessionState(current_step=Step.PROJECT_INPUT)
    save_mock = AsyncMock()
    mark_completed_mock = AsyncMock(return_value=False)
    fire_eval_mock = Mock()
    _patch_runtime(monkeypatch, state, save_mock, mark_completed_mock, fire_eval_mock)

    with TestClient(main.app) as client:
        resp = client.post("/chat/s1/skip")

    assert resp.status_code == 200
    assert mark_completed_mock.call_count == 1
    fire_eval_mock.assert_not_called()


def test_skip_rejects_non_testing_session(monkeypatch):
    """A session never flagged is_testing (e.g. a real customer's session_id)
    must not be skippable — guards against force-completing/mis-flagging a
    live chat via the skip endpoint."""
    state = SessionState(current_step=Step.PROJECT_INPUT)
    save_mock = AsyncMock()
    mark_completed_mock = AsyncMock(return_value=True)
    fire_eval_mock = Mock()
    _patch_runtime(
        monkeypatch,
        state,
        save_mock,
        mark_completed_mock,
        fire_eval_mock,
        is_testing=False,
    )

    with TestClient(main.app) as client:
        resp = client.post("/chat/s1/skip")

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Session is not a testing session"
    save_mock.assert_not_called()
    mark_completed_mock.assert_not_called()
    fire_eval_mock.assert_not_called()
