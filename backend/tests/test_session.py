import pytest
from unittest.mock import AsyncMock
from models import SessionState, Step
import session
from session import save


@pytest.mark.asyncio
async def test_load_returns_default_for_new_session():
    conn = AsyncMock()
    conn.fetchrow.return_value = None
    state = await session.load("new-id", conn)
    assert state.current_step == Step.INTRO
    assert state.topics_cited == []


@pytest.mark.asyncio
async def test_load_restores_saved_state():
    conn = AsyncMock()
    saved = SessionState(current_step=Step.PROJECT_INPUT, default_language="it")
    conn.fetchrow.return_value = {"state": saved.model_dump_json()}
    state = await session.load("existing-id", conn)
    assert state.current_step == Step.PROJECT_INPUT
    assert state.default_language == "it"


@pytest.mark.asyncio
async def test_save_calls_upsert():
    conn = AsyncMock()
    state = SessionState(current_step=Step.CATEGORY_SELECT)
    await session.save("test-id", state, conn)
    conn.execute.assert_called_once()
    sql, session_id, *_ = conn.execute.call_args[0]
    assert "INSERT INTO sessions" in sql
    assert session_id == "test-id"


@pytest.mark.asyncio
async def test_save_clears_abandoned_at_on_resume():
    """Una chat ripresa deve perdere il marchio abbandonata."""
    conn = AsyncMock()
    await session.save("test-id", SessionState(current_step=Step.QA), conn)
    sql = conn.execute.call_args[0][0]
    assert "abandoned_at = NULL" in sql


@pytest.mark.asyncio
async def test_save_and_load_roundtrip():
    state = SessionState(
        current_step=Step.QA,
        topics_cited=["quality", "home"],
        questions_asked=["Are you certified?"],
    )
    restored = SessionState.model_validate_json(state.model_dump_json())
    assert restored.current_step == Step.QA
    assert restored.topics_cited == ["quality", "home"]
    assert restored.questions_asked == ["Are you certified?"]


@pytest.mark.asyncio
async def test_save_passes_is_testing_true():
    conn = AsyncMock()
    await session.save("s1", SessionState(), conn, is_testing=True)
    args, _ = conn.execute.call_args
    assert "is_testing" in args[0]
    assert args[3] is True


@pytest.mark.asyncio
async def test_save_defaults_is_testing_false():
    conn = AsyncMock()
    await session.save("s1", SessionState(), conn)
    assert conn.execute.call_args[0][3] is False


@pytest.mark.asyncio
async def test_save_is_testing_sticky_in_sql():
    conn = AsyncMock()
    await session.save("s1", SessionState(), conn, is_testing=True)
    sql = conn.execute.call_args[0][0]
    assert "sessions.is_testing OR EXCLUDED.is_testing" in sql


@pytest.mark.asyncio
async def test_save_writes_reporting_columns():
    seen = {}

    class FakeConn:
        async def execute(self, q, *a):
            seen["q"] = q
            seen["args"] = a

    state = SessionState(profile="new_brand", category="proteins",
                         format="powders", quote_requested=True)
    await save("sess-1", state, FakeConn())

    for column in ("profile", "category", "format", "quote_requested"):
        assert column in seen["q"]
    # ordine: session_id, state_json, is_testing, profile, category, format, quote_requested
    assert seen["args"][3] == "new_brand"
    assert seen["args"][4] == "proteins"
    assert seen["args"][5] == "powders"
    assert seen["args"][6] is True


@pytest.mark.asyncio
async def test_save_reporting_columns_null_before_selection():
    seen = {}

    class FakeConn:
        async def execute(self, q, *a):
            seen["args"] = a

    await save("sess-1", SessionState(), FakeConn())
    assert seen["args"][3] is None
    assert seen["args"][6] is False
