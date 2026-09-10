import json
import pytest
from unittest.mock import AsyncMock
from agents import lead_agents


def _fake_stream(captured):
    async def stream(system, user, history=None, model=None):
        captured["system"] = system
        captured["user"] = user
        for token in ["ciao ", "mondo"]:
            yield token
    return stream


async def test_introduction_streams_and_fills_language(monkeypatch):
    captured = {}
    monkeypatch.setattr(lead_agents.llm, "stream", _fake_stream(captured))
    out = "".join([t async for t in lead_agents.introduction("it")])
    assert out == "ciao mondo"
    assert captured["system"].startswith("# Prompt: introduction\n")
    assert "italian" in captured["system"]
    assert "{default_language}" not in captured["system"]


async def test_ask_category_passes_profile(monkeypatch):
    captured = {}
    monkeypatch.setattr(lead_agents.llm, "stream", _fake_stream(captured))
    [t async for t in lead_agents.ask_category("I have a product idea", "en")]
    assert "I have a product idea" in captured["system"]
    assert "{profile}" not in captured["system"]


async def test_ask_project_passes_category_and_format(monkeypatch):
    captured = {}
    monkeypatch.setattr(lead_agents.llm, "stream", _fake_stream(captured))
    [t async for t in lead_agents.ask_project("Proteins", "Powders", "en")]
    assert "Proteins" in captured["system"] and "Powders" in captured["system"]


@pytest.mark.parametrize("data,expected", [
    ({"enough": True, "question": "ignorata"}, (True, "")),
    ({"enough": False, "question": " Dimmi di più "}, (False, "Dimmi di più")),
    ({}, (False, "")),
])
async def test_validate_project_maps_json(monkeypatch, data, expected):
    monkeypatch.setattr(lead_agents.llm, "complete_structured", AsyncMock(return_value=data))
    assert await lead_agents.validate_project("U: whey", "en") == expected


async def test_summarize_project_strips(monkeypatch):
    monkeypatch.setattr(lead_agents.llm, "complete", AsyncMock(return_value="  Riassunto  "))
    assert await lead_agents.summarize_project("U: whey", "it") == "Riassunto"


async def test_confirm_lead_serializes_lead_without_ascii_escapes(monkeypatch):
    captured = {}
    monkeypatch.setattr(lead_agents.llm, "stream", _fake_stream(captured))
    lead = {"profile": "product_idea", "contact": {"name": "Mario Rossì"}}
    [t async for t in lead_agents.confirm_lead(lead, "it")]
    assert "Mario Rossì" in captured["system"]
    assert json.loads(captured["user"]) == lead
