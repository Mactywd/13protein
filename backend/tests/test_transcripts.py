import json
import pytest
import transcripts
from models import SessionState, Step


@pytest.mark.asyncio
async def test_append_writes_payload_json():
    captured = {}

    class FakeConn:
        async def executemany(self, q, rows):
            captured["rows"] = rows

    state = SessionState(current_step=Step.INTRO)
    await transcripts.append(
        "sess-1", "ciao", state, "benvenuto",
        FakeConn(), assistant_payload={"buttons": [{"label": "Memoria", "value": "memory"}]},
    )
    user_row, assistant_row = captured["rows"]
    assert user_row[1] == "user" and user_row[4] is None
    assert assistant_row[1] == "assistant"
    assert json.loads(assistant_row[4])["buttons"][0]["value"] == "memory"


@pytest.mark.asyncio
async def test_append_without_payload_is_none():
    captured = {}

    class FakeConn:
        async def executemany(self, q, rows):
            captured["rows"] = rows

    state = SessionState(current_step=Step.INTRO)
    await transcripts.append("sess-1", "ciao", state, "ok", FakeConn())
    assert captured["rows"][1][4] is None


@pytest.mark.asyncio
async def test_append_writes_usage_on_assistant_row():
    captured = {}

    class FakeConn:
        async def executemany(self, q, rows):
            captured["rows"] = rows

    state = SessionState(current_step=Step.INTRO)
    await transcripts.append(
        "sess-1", "ciao", state, "benvenuto", FakeConn(),
        assistant_payload=None,
        cost=0.0031, prompt_tokens=120, completion_tokens=44,
        model="google/gemma,perplexity/sonar",
    )
    user_row, assistant_row = captured["rows"]
    # user row: usage columns are None
    assert user_row[5:9] == (None, None, None, None)
    # assistant row carries the usage
    assert assistant_row[5] == 0.0031
    assert assistant_row[6] == 120
    assert assistant_row[7] == 44
    assert assistant_row[8] == "google/gemma,perplexity/sonar"
