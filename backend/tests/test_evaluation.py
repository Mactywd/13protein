import json
import pytest
from unittest.mock import AsyncMock, patch
from agents import evaluation


def test_format_transcript():
    rows = [
        {"role": "user", "content": "Vorrei produrre una whey"},
        {"role": "assistant", "content": "Per quale mercato?"},
    ]
    out = evaluation.format_transcript(rows)
    assert "U: Vorrei produrre una whey" in out
    assert "A: Per quale mercato?" in out


@pytest.mark.asyncio
async def test_run_evaluation_happy_path():
    calls = []

    class FakeConn:
        async def execute(self, q, *a): calls.append(("execute", q, a))
        async def fetch(self, q, *a):
            return [{"role": "user", "content": "ciao"},
                    {"role": "assistant", "content": "benvenuto"}]

    fake_conn = FakeConn()

    class FakeTx:
        async def __aenter__(self): return fake_conn
        async def __aexit__(self, *a): return False

    structured = {"outcome": "completed", "path_summary": "Riassunto di prova",
                 "problem": "", "quote_requested": True}

    with patch("agents.evaluation.db.transaction", return_value=FakeTx()), \
         patch("agents.evaluation.llm.complete_structured",
               new=AsyncMock(return_value=structured)):
        await evaluation.run_evaluation("sess-1")

    assert any("Riassunto di prova" in str(c[2]) for c in calls)


@pytest.mark.asyncio
async def test_run_evaluation_marks_error_on_failure():
    statuses = []

    class FakeConn:
        async def execute(self, q, *a):
            statuses.append(a)
        async def fetch(self, q, *a):
            return [{"role": "user", "content": "ciao"}]

    fake_conn = FakeConn()

    class FakeTx:
        async def __aenter__(self): return fake_conn
        async def __aexit__(self, *a): return False

    with patch("agents.evaluation.db.transaction", return_value=FakeTx()), \
         patch("agents.evaluation.llm.complete_structured",
               new=AsyncMock(side_effect=RuntimeError("boom"))):
        await evaluation.run_evaluation("sess-1")

    assert any("error" in str(s) for s in statuses)


@pytest.mark.asyncio
async def test_run_evaluation_attributes_cost_to_session(monkeypatch):
    import agents.evaluation as ev
    from services import usage as usage_mod

    upserts = []
    add_usage_calls = []

    # Fake DB connection / transaction
    class FakeConn:
        async def execute(self, *a, **kw): pass
        async def fetch(self, *a, **kw):
            return [{"role": "user", "content": "ciao"}]

    class FakeTx:
        async def __aenter__(self): return FakeConn()
        async def __aexit__(self, *a): return False

    monkeypatch.setattr(ev.db, "transaction", lambda: FakeTx())

    async def fake_upsert(conn, session_id, **fields):
        upserts.append(fields)
    monkeypatch.setattr(ev, "_upsert", fake_upsert)

    async def fake_complete_structured(system, user):
        usage_mod.record({"cost": 0.005, "prompt_tokens": 30, "completion_tokens": 10},
                         model=ev.llm.model_name())
        return {"outcome": "completed", "path_summary": "Riassunto",
               "problem": "", "quote_requested": True}
    monkeypatch.setattr(ev.llm, "complete_structured", fake_complete_structured)

    async def fake_add_usage(session_id, cost, pt, ct, conn):
        add_usage_calls.append((cost, pt, ct))
    monkeypatch.setattr(ev.chats, "add_usage", fake_add_usage)

    await ev.run_evaluation("sess-1")

    assert add_usage_calls and round(add_usage_calls[0][0], 4) == 0.005
    assert add_usage_calls[0][1] == 30 and add_usage_calls[0][2] == 10
    done = [u for u in upserts if u.get("status") == "done"][0]
    assert round(done["cost"], 4) == 0.005
    assert done["prompt_tokens"] == 30 and done["completion_tokens"] == 10
    assert done["summary"] == "Riassunto"


@pytest.mark.asyncio
async def test_run_evaluation_stores_structured_fields(monkeypatch):
    import agents.evaluation as ev

    upserts = []

    class FakeConn:
        async def execute(self, *a, **kw): pass
        async def fetch(self, *a, **kw):
            return [{"role": "user", "content": "ciao"}]

    class FakeTx:
        async def __aenter__(self): return FakeConn()
        async def __aexit__(self, *a): return False

    monkeypatch.setattr(ev.db, "transaction", lambda: FakeTx())

    async def fake_upsert(conn, session_id, **fields):
        upserts.append(fields)
    monkeypatch.setattr(ev, "_upsert", fake_upsert)

    structured = {
        "outcome": "completed",
        "path_summary": "Il cliente ha completato la qualificazione.",
        "problem": "Il cliente ha faticato a descrivere il progetto.",
        "quote_requested": True,
    }

    async def fake_complete_structured(system, user):
        return structured
    monkeypatch.setattr(ev.llm, "complete_structured", fake_complete_structured)

    async def fake_add_usage(session_id, cost, pt, ct, conn): pass
    monkeypatch.setattr(ev.chats, "add_usage", fake_add_usage)

    await ev.run_evaluation("sess-1")

    done = [u for u in upserts if u.get("status") == "done"][0]
    assert done["outcome"] == "completed"
    assert done["summary"] == "Il cliente ha completato la qualificazione."
    assert done["friction_note"] == "Il cliente ha faticato a descrivere il progetto."
    assert done["quote_requested"] is True


@pytest.mark.asyncio
async def test_run_evaluation_marks_error_on_malformed_json(monkeypatch):
    import agents.evaluation as ev

    upserts = []

    class FakeConn:
        async def execute(self, *a, **kw): pass
        async def fetch(self, *a, **kw):
            return [{"role": "user", "content": "ciao"}]

    class FakeTx:
        async def __aenter__(self): return FakeConn()
        async def __aexit__(self, *a): return False

    monkeypatch.setattr(ev.db, "transaction", lambda: FakeTx())

    async def fake_upsert(conn, session_id, **fields):
        upserts.append(fields)
    monkeypatch.setattr(ev, "_upsert", fake_upsert)

    async def fake_complete_structured(system, user):
        raise json.JSONDecodeError("bad", "doc", 0)
    monkeypatch.setattr(ev.llm, "complete_structured", fake_complete_structured)

    await ev.run_evaluation("sess-1")

    assert any(u.get("status") == "error" for u in upserts)
