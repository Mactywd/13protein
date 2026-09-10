from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import main
from models import SessionState, Step


def _patch_runtime(monkeypatch, save_mock):
    @asynccontextmanager
    async def fake_transaction():
        yield object()

    async def fake_load(session_id, conn):
        return SessionState(current_step=Step.COMPLETED)

    async def noop(*a, **k):
        return None

    monkeypatch.setattr(main.db, "init_pool", noop)
    monkeypatch.setattr(main.db, "close_pool", noop)
    monkeypatch.setattr(main.db, "transaction", fake_transaction)
    monkeypatch.setattr(main.session, "load", fake_load)
    monkeypatch.setattr(main.session, "save", save_mock)
    monkeypatch.setattr(main.transcripts, "append", AsyncMock())
    monkeypatch.setattr(main.chats, "add_usage", AsyncMock())
    monkeypatch.setattr(main.chats, "mark_completed", AsyncMock(return_value=False))

    async def empty_handler(state, message):
        if False:
            yield None

    monkeypatch.setattr(main, "dispatch", lambda step: empty_handler)


def test_chat_forwards_is_testing_true(monkeypatch):
    save_mock = AsyncMock()
    _patch_runtime(monkeypatch, save_mock)
    with TestClient(main.app) as client:
        resp = client.post(
            "/chat",
            json={"session_id": "s1", "message": "ciao", "is_testing": True},
        )
    assert resp.status_code == 200
    _, kwargs = save_mock.call_args
    assert save_mock.call_args[1].get("is_testing") is True or save_mock.call_args[0][-1] is True


def test_chat_defaults_is_testing_false(monkeypatch):
    save_mock = AsyncMock()
    _patch_runtime(monkeypatch, save_mock)
    with TestClient(main.app) as client:
        resp = client.post("/chat", json={"session_id": "s1", "message": "ciao"})
    assert resp.status_code == 200
    assert save_mock.call_args[1].get("is_testing") is False or save_mock.call_args[0][-1] is False
