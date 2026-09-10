import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services import openrouter, usage


@pytest.mark.asyncio
async def test_complete_records_usage_and_sets_include():
    captured = {}
    fake = MagicMock()
    fake.status_code = 200
    fake.raise_for_status = MagicMock()
    fake.json = MagicMock(return_value={
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"cost": 0.004, "prompt_tokens": 10, "completion_tokens": 2},
    })

    async def fake_post(url, **kw):
        captured["json"] = kw["json"]
        return fake

    token = usage.start()
    with patch("services.openrouter.httpx.AsyncClient") as Client:
        inst = Client.return_value.__aenter__.return_value
        inst.post = AsyncMock(side_effect=fake_post)
        await openrouter.complete("sys", "user")
    acc = usage.current()
    usage.reset(token)
    assert captured["json"]["usage"] == {"include": True}
    assert round(acc.cost, 4) == 0.004
    assert acc.prompt_tokens == 10


@pytest.mark.asyncio
async def test_stream_records_usage_from_final_chunk():
    lines = [
        'data: ' + json.dumps({"choices": [{"delta": {"content": "hi"}}]}),
        'data: ' + json.dumps({"choices": [], "usage": {"cost": 0.002, "prompt_tokens": 4, "completion_tokens": 1}}),
        'data: [DONE]',
    ]

    class FakeStream:
        status_code = 200
        def raise_for_status(self): pass
        async def aread(self): return b""
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def aiter_lines(self):
            for ln in lines:
                yield ln

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        def stream(self, *a, **kw): return FakeStream()

    token = usage.start()
    out = []
    with patch("services.openrouter.httpx.AsyncClient", return_value=FakeClient()):
        async for tok in openrouter.stream("sys", "user"):
            out.append(tok)
    acc = usage.current()
    usage.reset(token)
    assert "".join(out) == "hi"
    assert round(acc.cost, 4) == 0.002
    assert acc.completion_tokens == 1


@pytest.mark.asyncio
async def test_complete_records_model():
    fake = MagicMock()
    fake.status_code = 200
    fake.raise_for_status = MagicMock()
    fake.json = MagicMock(return_value={
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"cost": 0.004, "prompt_tokens": 10, "completion_tokens": 2},
    })

    async def fake_post(url, **kw):
        return fake

    token = usage.start()
    with patch("services.openrouter.httpx.AsyncClient") as Client:
        inst = Client.return_value.__aenter__.return_value
        inst.post = AsyncMock(side_effect=fake_post)
        await openrouter.complete("sys", "user", model="test/model-x")
    models = usage.current().models
    usage.reset(token)
    assert "test/model-x" in models


@pytest.mark.asyncio
async def test_stream_records_model():
    lines = [
        'data: ' + json.dumps({"choices": [{"delta": {"content": "hi"}}]}),
        'data: ' + json.dumps({"choices": [], "usage": {"cost": 0.002, "prompt_tokens": 4, "completion_tokens": 1}}),
        'data: [DONE]',
    ]

    class FakeStream:
        status_code = 200
        def raise_for_status(self): pass
        async def aread(self): return b""
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def aiter_lines(self):
            for ln in lines:
                yield ln

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        def stream(self, *a, **kw): return FakeStream()

    token = usage.start()
    with patch("services.openrouter.httpx.AsyncClient", return_value=FakeClient()):
        async for _ in openrouter.stream("sys", "user", model="stream/model-y"):
            pass
    models = usage.current().models
    usage.reset(token)
    assert "stream/model-y" in models
