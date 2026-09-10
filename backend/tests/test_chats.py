import pytest
from datetime import datetime, timezone, timedelta
from chats import chat_summary, messages_from_row, get_abandon_timeout, set_abandon_timeout, sweep_abandoned, get_chat, list_chats, DEFAULT_ABANDON_TIMEOUT_MIN


def test_messages_from_row_attaches_meta():
    ts = datetime(2026, 6, 30, 9, 15, 0, tzinfo=timezone.utc)
    row = {
        "role": "assistant", "content": "Benvenuto",
        "payload": {"buttons": [{"label": "Proteins", "value": "proteins"}]},
        "created_at": ts, "cost": 0.0021,
        "prompt_tokens": 80, "completion_tokens": 20, "model": "google/gemma",
    }
    msgs = messages_from_row(row)
    text = next(m for m in msgs if m["type"] == "text")
    buttons = next(m for m in msgs if m["type"] == "choice")
    assert text["meta"]["created_at"] == ts.isoformat()
    assert text["meta"]["cost"] == 0.0021
    assert text["meta"]["prompt_tokens"] == 80
    assert text["meta"]["completion_tokens"] == 20
    assert text["meta"]["model"] == "google/gemma"
    # non-text bubble: only timestamp, no usage keys
    assert buttons["meta"] == {"created_at": ts.isoformat()}


def test_messages_from_row_user_meta_timestamp_only():
    ts = datetime(2026, 6, 30, 9, 16, 0, tzinfo=timezone.utc)
    row = {"role": "user", "content": "ciao", "payload": None,
           "created_at": ts, "cost": None, "prompt_tokens": None,
           "completion_tokens": None, "model": None}
    msgs = messages_from_row(row)
    assert msgs[0]["meta"] == {"created_at": ts.isoformat()}


def test_chat_summary_completed_has_duration_and_status():
    start = datetime(2026, 6, 12, 10, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(seconds=125)
    row = {
        "id": "sess-1", "created_at": start, "completed_at": end,
        "total_cost": 0.0345, "prompt_tokens": 100, "completion_tokens": 40,
        "preview": "Vorrei produrre una whey per palestre", "eval_status": "done",
    }
    out = chat_summary(row)
    assert out["session_id"] == "sess-1"
    assert out["status"] == "completata"
    assert out["duration_seconds"] == 125
    assert out["total_cost"] == 0.0345
    assert out["preview"] == "Vorrei produrre una whey per palestre"
    assert out["eval_status"] == "done"


def test_chat_summary_incomplete_has_no_duration():
    row = {
        "id": "sess-2", "created_at": datetime.now(timezone.utc), "completed_at": None,
        "total_cost": 0.0, "prompt_tokens": 0, "completion_tokens": 0,
        "preview": None, "eval_status": None,
    }
    out = chat_summary(row)
    assert out["status"] == "in_corso"
    assert out["duration_seconds"] is None
    assert out["eval_status"] is None


def test_chat_summary_abandoned_status():
    start = datetime(2026, 6, 12, 10, 0, 0, tzinfo=timezone.utc)
    row = {
        "id": "sess-ab", "created_at": start, "completed_at": None,
        "abandoned_at": start + timedelta(minutes=40), "profile": "new_brand",
        "total_cost": 0.0, "prompt_tokens": 0, "completion_tokens": 0,
        "preview": None, "eval_status": "done",
    }
    out = chat_summary(row)
    assert out["status"] == "abbandonata"
    assert out["duration_seconds"] is None


def test_chat_summary_initialized_when_abandoned_without_profile():
    start = datetime(2026, 6, 12, 10, 0, 0, tzinfo=timezone.utc)
    row = {
        "id": "sess-init", "created_at": start, "completed_at": None,
        "abandoned_at": start + timedelta(minutes=40), "profile": None,
        "total_cost": 0.0, "prompt_tokens": 0, "completion_tokens": 0,
        "preview": None, "eval_status": None,
    }
    assert chat_summary(row)["status"] == "inizializzata"


def test_chat_summary_completed_beats_abandoned():
    start = datetime(2026, 6, 12, 10, 0, 0, tzinfo=timezone.utc)
    row = {
        "id": "sess-c", "created_at": start, "completed_at": start + timedelta(seconds=90),
        "abandoned_at": start + timedelta(minutes=40),
        "total_cost": 0.0, "prompt_tokens": 0, "completion_tokens": 0,
        "preview": None, "eval_status": "done",
    }
    assert chat_summary(row)["status"] == "completata"


def test_chat_summary_includes_is_testing():
    row = {
        "id": "s1",
        "created_at": None,
        "completed_at": None,
        "abandoned_at": None,
        "total_cost": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "preview": "ciao",
        "eval_status": None,
        "is_testing": True,
    }
    summary = chat_summary(row)
    assert summary["is_testing"] is True


@pytest.mark.asyncio
async def test_get_abandon_timeout_default_when_missing():
    class FakeConn:
        async def fetchrow(self, q, *a): return None
    assert await get_abandon_timeout(FakeConn()) == DEFAULT_ABANDON_TIMEOUT_MIN


@pytest.mark.asyncio
async def test_get_abandon_timeout_reads_stored_value():
    class FakeConn:
        async def fetchrow(self, q, *a): return {"value": "45"}
    assert await get_abandon_timeout(FakeConn()) == 45


@pytest.mark.asyncio
async def test_get_abandon_timeout_falls_back_on_garbage():
    class FakeConn:
        async def fetchrow(self, q, *a): return {"value": "abc"}
    assert await get_abandon_timeout(FakeConn()) == DEFAULT_ABANDON_TIMEOUT_MIN


@pytest.mark.asyncio
async def test_set_abandon_timeout_writes_string():
    seen = {}
    class FakeConn:
        async def execute(self, q, *a):
            seen["q"], seen["args"] = q, a
    await set_abandon_timeout(FakeConn(), 20)
    assert "app_settings" in seen["q"]
    assert seen["args"] == ("abandon_timeout_minutes", "20")


@pytest.mark.asyncio
async def test_sweep_abandoned_disabled_when_timeout_zero():
    class FakeConn:
        async def fetchrow(self, q, *a): return {"value": "0"}
        async def fetch(self, q, *a): raise AssertionError("should not query when disabled")
    assert await sweep_abandoned(FakeConn()) == []


@pytest.mark.asyncio
async def test_sweep_abandoned_returns_marked_ids():
    seen = {}
    class FakeConn:
        async def fetchrow(self, q, *a): return {"value": "30"}
        async def fetch(self, q, *a):
            seen["args"] = a
            return [{"id": "s1", "profile": "new_brand"}, {"id": "s2", "profile": None}]
    ids = await sweep_abandoned(FakeConn())
    assert ids == [("s1", "new_brand"), ("s2", None)]
    assert seen["args"] == (30,)


def test_messages_from_row_user_text():
    row = {"role": "user", "content": "ciao", "payload": None}
    assert messages_from_row(row) == [{
        "sender": "user", "type": "text",
        "payload": {"message": "ciao"}, "additionalClasses": [],
        "meta": {"created_at": None},
    }]


def test_messages_from_row_blank_user_launch_is_skipped():
    assert messages_from_row({"role": "user", "content": "", "payload": None}) == []
    assert messages_from_row({"role": "user", "content": "   ", "payload": None}) == []


def test_messages_from_row_empty_assistant_turn_is_skipped():
    # Il turno finale emette solo lead_info: niente testo, niente payload.
    assert messages_from_row({"role": "assistant", "content": "", "payload": None}) == []


def test_messages_from_row_assistant_text_then_buttons():
    # Narration text must NOT be dropped when the turn also has buttons.
    row = {"role": "assistant", "content": "Quale opzione la descrive meglio?",
           "payload": {"buttons": [{"label": "Proteins", "value": "proteins"}]}}
    out = messages_from_row(row)
    assert [m["type"] for m in out] == ["text", "choice"]
    assert out[0]["sender"] == "ai"
    assert out[0]["payload"]["message"] == "Quale opzione la descrive meglio?"
    btn = out[1]["payload"]["buttons"][0]
    # Message.jsx reads button.name and button.request.payload.label
    assert btn["name"] == "Proteins"
    assert btn["request"]["payload"]["label"] == "proteins"


def test_messages_from_row_splits_message_break_into_two_bubbles():
    # Il turno che chiude lo step progetto salva il riassunto e l'apertura
    # delle domande in una riga sola, separati dal sentinella MESSAGE_BREAK:
    # l'admin deve ri-espanderli in due bolle come fa il client live.
    from models import MESSAGE_BREAK
    row = {"role": "assistant",
           "content": f"Ecco cosa ho capito{MESSAGE_BREAK}Ha domande su 13 Protein?",
           "payload": {"buttons": [{"label": "Request a quote", "value": "request_quote"}]}}
    out = messages_from_row(row)
    assert [m["type"] for m in out] == ["text", "text", "choice"]
    assert out[0]["payload"]["message"] == "Ecco cosa ho capito"
    assert out[1]["payload"]["message"] == "Ha domande su 13 Protein?"


def test_messages_from_row_assistant_carousel_only():
    row = {"role": "assistant", "content": "",
           "payload": {"cards": [{"title": "Protein Powders", "image": "http://x/i.jpg",
                                   "description": "Whey, caseina, vegetali", "value": "doc:protein-powders"}]}}
    out = messages_from_row(row)
    assert [m["type"] for m in out] == ["carousel"]
    card = out[0]["payload"]["cards"][0]
    # Message.jsx legge card.imageUrl, card.title, card.description.text, card.buttons[0].name
    assert card["imageUrl"] == "http://x/i.jpg"
    assert card["title"] == "Protein Powders"
    assert card["description"]["text"] == "Whey, caseina, vegetali"
    assert card["buttons"][0]["name"] == "doc:protein-powders"


def test_messages_from_row_assistant_text_carousel_and_buttons():
    # Lo step categoria emette narrazione + carosello + bottoni in un turno solo:
    # tutti e tre devono sopravvivere, nell'ordine di visualizzazione.
    row = {"role": "assistant", "content": "Ottima scelta",
           "payload": {"cards": [{"title": "Protein Powders", "image": "http://x/i.jpg",
                                   "description": "Whey, caseina, vegetali", "value": "doc:protein-powders"}],
                       "buttons": [{"label": "Powders", "value": "powders"}]}}
    out = messages_from_row(row)
    assert [m["type"] for m in out] == ["text", "carousel", "choice"]
    assert out[0]["payload"]["message"] == "Ottima scelta"
    assert out[1]["payload"]["cards"][0]["title"] == "Protein Powders"
    assert out[2]["payload"]["buttons"][0]["name"] == "Powders"


@pytest.mark.asyncio
async def test_get_chat_includes_structured_evaluation_fields():
    class FakeConn:
        async def fetchrow(self, q, *a):
            if "FROM sessions" in q:
                return {"id": "s1", "created_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
                       "completed_at": None, "abandoned_at": None, "total_cost": 0,
                       "prompt_tokens": 0, "completion_tokens": 0, "is_testing": False,
                       "profile": None, "category": None, "format": None, "quote_requested": False}
            if "FROM evaluations" in q:
                return {"summary": "Riassunto", "model": "m", "status": "done",
                       "updated_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
                       "cost": 0.01, "prompt_tokens": 5, "completion_tokens": 5,
                       "outcome": "completed", "friction_note": "Attrito sulla richiesta del contatto.",
                       "quote_requested": True}
            return None
        async def fetch(self, q, *a): return []

    result = await get_chat("s1", FakeConn())
    assert result["evaluation"]["outcome"] == "completed"
    assert result["evaluation"]["friction_note"] == "Attrito sulla richiesta del contatto."
    assert result["evaluation"]["quote_requested"] is True


@pytest.mark.asyncio
async def test_list_chats_unfiltered_passes_no_args():
    captured = {}

    class FakeConn:
        async def fetch(self, q, *a):
            captured["q"], captured["a"] = q, a
            return []

    out = await list_chats(FakeConn())
    assert out == []
    assert "created_at >=" not in captured["q"]
    assert captured["a"] == ()


@pytest.mark.asyncio
async def test_list_chats_applies_date_bounds():
    captured = {}

    class FakeConn:
        async def fetch(self, q, *a):
            captured["q"], captured["a"] = q, a
            return []

    df = datetime(2026, 6, 1, tzinfo=timezone.utc)
    dt = datetime(2026, 7, 1, tzinfo=timezone.utc)
    await list_chats(FakeConn(), df, dt)
    assert "s.created_at >= $1" in captured["q"]
    assert "s.created_at < $2" in captured["q"]   # upper bound exclusive
    assert captured["a"] == (df, dt)


@pytest.mark.asyncio
async def test_list_chats_has_no_row_cap():
    """L'intervallo di date è l'unico taglio: nessun LIMIT sulle righe.

    Il `LIMIT 1` che resta è quello della sottoquery della preview, che deve
    restare — per questo il confronto è sul frammento parametrico `LIMIT $`.
    """
    captured = {}

    class FakeConn:
        async def fetch(self, q, *a):
            captured["q"] = q
            return []

    await list_chats(FakeConn(), datetime(2026, 1, 1, tzinfo=timezone.utc), None)
    assert "LIMIT $" not in captured["q"]


def test_chat_summary_exposes_lead_columns():
    row = {
        "id": "s-lead", "created_at": None, "completed_at": None, "abandoned_at": None,
        "total_cost": 0, "prompt_tokens": 0, "completion_tokens": 0,
        "preview": None, "eval_status": None,
        "profile": "product_idea", "category": "proteins",
        "format": "powders", "quote_requested": True,
    }
    out = chat_summary(row)
    assert out["profile"] == "product_idea"
    assert out["category"] == "proteins"
    assert out["format"] == "powders"
    assert out["quote_requested"] is True
