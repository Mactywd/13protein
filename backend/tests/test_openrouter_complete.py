import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services import openrouter


@pytest.mark.asyncio
async def test_complete_returns_message_content():
    fake = MagicMock()
    fake.raise_for_status = MagicMock()
    fake.json = MagicMock(return_value={"choices": [{"message": {"content": "avanti"}}]})
    with patch("services.openrouter.httpx.AsyncClient") as Client:
        inst = Client.return_value.__aenter__.return_value
        inst.post = AsyncMock(return_value=fake)
        out = await openrouter.complete("sys", "user")
    assert out == "avanti"


@pytest.mark.asyncio
async def test_web_complete_returns_message_content():
    from services import openrouter

    captured = {}

    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": '{"testa": ["limone"]}'}}]}

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, **kw):
            captured["json"] = kw["json"]
            return FakeResp()

    with patch("services.openrouter.httpx.AsyncClient", return_value=FakeClient()):
        out = await openrouter.web_complete("sys", "usr")
    assert out == '{"testa": ["limone"]}'
    assert captured["json"]["model"] == openrouter.WEB_SEARCH_MODEL
