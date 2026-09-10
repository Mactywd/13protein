import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import main


@pytest.mark.asyncio
async def test_report_route_merges_stats_and_narrative(monkeypatch):
    class FakeConn:
        pass

    class FakeTx:
        async def __aenter__(self): return FakeConn()
        async def __aexit__(self, *a): return False

    monkeypatch.setattr(main.db, "transaction", lambda: FakeTx())

    fake_stats = {"total_sessions": 3, "period": {"from": "x", "to": "y"}}
    fake_narrative = {"friction_text": "ok", "recommendations": []}

    async def fake_build_report(conn, date_from, date_to):
        return fake_stats
    monkeypatch.setattr(main.reporting, "build_report", fake_build_report)

    async def fake_generate_narrative(stats):
        assert stats == fake_stats
        return fake_narrative
    monkeypatch.setattr(main.report_agents, "generate_narrative", fake_generate_narrative)

    client = TestClient(main.app)
    resp = client.get("/report", params={"from": "2026-06-01", "to": "2026-07-01"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["stats"] == fake_stats
    assert body["narrative"] == fake_narrative


@pytest.mark.asyncio
async def test_report_route_strips_by_weekday_from_narrative_input(monkeypatch):
    class FakeConn:
        pass

    class FakeTx:
        async def __aenter__(self): return FakeConn()
        async def __aexit__(self, *a): return False

    monkeypatch.setattr(main.db, "transaction", lambda: FakeTx())

    fake_stats = {"total_sessions": 3,
                  "by_weekday": [{"weekday": 1, "count": 3, "share": 1.0}]}

    async def fake_build_report(conn, date_from, date_to):
        return fake_stats
    monkeypatch.setattr(main.reporting, "build_report", fake_build_report)

    captured = {}

    async def fake_generate_narrative(stats):
        captured["stats"] = stats
        return {"recommendations": []}
    monkeypatch.setattr(main.report_agents, "generate_narrative", fake_generate_narrative)

    client = TestClient(main.app)
    resp = client.get("/report", params={"from": "2026-06-01", "to": "2026-07-01"})
    assert resp.status_code == 200
    # The API response keeps by_weekday for the admin tables…
    assert resp.json()["stats"]["by_weekday"] == fake_stats["by_weekday"]
    # …but the narrative LLM never sees it.
    assert "by_weekday" not in captured["stats"]
    assert captured["stats"]["total_sessions"] == 3


@pytest.mark.asyncio
async def test_report_route_skips_narrative_when_disabled(monkeypatch):
    class FakeConn:
        pass

    class FakeTx:
        async def __aenter__(self): return FakeConn()
        async def __aexit__(self, *a): return False

    monkeypatch.setattr(main.db, "transaction", lambda: FakeTx())

    fake_stats = {"total_sessions": 3}

    async def fake_build_report(conn, date_from, date_to):
        return fake_stats
    monkeypatch.setattr(main.reporting, "build_report", fake_build_report)

    async def fail_narrative(stats):
        raise AssertionError("generate_narrative non deve essere chiamato")
    monkeypatch.setattr(main.report_agents, "generate_narrative", fail_narrative)

    client = TestClient(main.app)
    resp = client.get("/report", params={"from": "2026-06-01", "to": "2026-07-01",
                                         "narrative": "false"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["stats"] == fake_stats
    assert "narrative" not in body
