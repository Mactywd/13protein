from unittest.mock import AsyncMock
from agents import contact_agents


async def test_ask_contact_streams(monkeypatch):
    captured = {}

    async def stream(system, user, history=None, model=None):
        captured["system"] = system
        yield "x"

    monkeypatch.setattr(contact_agents.llm, "stream", stream)
    out = "".join([t async for t in contact_agents.ask_contact("en")])
    assert out == "x"
    assert captured["system"].startswith("# Prompt: ask_contact\n")


async def test_extract_contact_returns_dict_untouched(monkeypatch):
    data = {"name": "Mario", "company": None, "email": "m@x.it", "valid": True}
    monkeypatch.setattr(contact_agents.llm, "complete_structured", AsyncMock(return_value=data))
    assert await contact_agents.extract_contact("Mario, m@x.it", "it") is data
