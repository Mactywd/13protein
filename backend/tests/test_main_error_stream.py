import json
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

import main
from models import SessionState, Step, TextEvent


def _parse_events(body: str):
    events = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        name = data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        events.append((name, data))
    return events


def _patch_runtime(monkeypatch):
    """Stub out the DB so the lifespan and the turn run without Postgres."""
    @asynccontextmanager
    async def fake_transaction():
        yield object()

    async def fake_load(session_id, conn):
        return SessionState(current_step=Step.INTRO)

    async def noop(*a, **k):
        return None

    monkeypatch.setattr(main.db, "init_pool", noop)
    monkeypatch.setattr(main.db, "close_pool", noop)
    monkeypatch.setattr(main.db, "transaction", fake_transaction)
    monkeypatch.setattr(main.session, "load", fake_load)


def test_handler_failure_emits_clean_error_event(monkeypatch):
    _patch_runtime(monkeypatch)

    async def boom(state, message):
        if False:  # make it an async generator
            yield None
        raise RuntimeError("openrouter exploded")

    monkeypatch.setattr(main, "dispatch", lambda step: boom)

    with TestClient(main.app) as client:
        resp = client.post(
            "/chat",
            json={"session_id": "s1", "message": "ciao", "default_language": "it"},
        )
    assert resp.status_code == 200
    events = _parse_events(resp.text)
    assert ("error", {"message": main._STREAM_ERROR_MESSAGE["it"]}) in events


def test_partial_stream_then_failure_still_emits_error(monkeypatch):
    _patch_runtime(monkeypatch)

    async def half_then_boom(state, message):
        yield TextEvent(token="Ciao")
        raise RuntimeError("died mid-stream")

    monkeypatch.setattr(main, "dispatch", lambda step: half_then_boom)

    with TestClient(main.app) as client:
        resp = client.post(
            "/chat",
            json={"session_id": "s1", "message": "ciao", "default_language": "en"},
        )
    assert resp.status_code == 200
    events = _parse_events(resp.text)
    assert ("text", {"token": "Ciao"}) in events
    assert ("error", {"message": main._STREAM_ERROR_MESSAGE["en"]}) in events
