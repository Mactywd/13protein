from unittest.mock import AsyncMock
from services import llm


async def test_dispatch_to_mock_by_default(monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_provider", "mock")
    out = await llm.complete("# Prompt: ask_contact\n", "x")
    assert out


async def test_dispatch_to_openrouter(monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_provider", "openrouter")
    monkeypatch.setattr(llm.openrouter, "complete", AsyncMock(return_value="real"))
    assert await llm.complete("s", "u") == "real"


async def test_stream_dispatches_to_mock(monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_provider", "mock")
    out = "".join([t async for t in llm.stream("# Prompt: introduction\n", "")])
    assert "13 Protein" in out
