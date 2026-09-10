from __future__ import annotations
import asyncio
import logging
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import services.db as db
import session
import transcripts
import chats
import testing_env
import reporting
import report_agents
import retention
from services import usage
from agents.evaluation import run_evaluation
from models import Step, ButtonsEvent, CarouselEvent, ErrorEvent, MessageBreakEvent, MESSAGE_BREAK
from router import dispatch
from stream import format_sse
from config import settings

# Uvicorn configures only its own `uvicorn.*` loggers and leaves the root one at
# WARNING with no handler, so every logger.info() in this app went nowhere. That
# silently included the retention purge line — the only evidence that the daily
# job ran at all (compliance C13), and the very thing the checklist tells you to
# grep for. The chatty third parties stay at WARNING: an INFO-level httpx logs a
# line per LLM call, which would bury the one line worth reading and inflate the
# log volume the 6-month rotation has to hold.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")
for _noisy in ("httpx", "httpcore", "asyncpg", "urllib3"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Shown to the user (per language) when a turn fails mid-stream (e.g. OpenRouter
# 401/timeout). Keeps the SSE contract: the client always gets a clean `error`
# event instead of a silently truncated stream.
_STREAM_ERROR_MESSAGE = {
    "en": "Sorry, something went wrong. Please try again in a moment.",
    "it": "Ci dispiace, si è verificato un problema. Riprovi tra un istante.",
}


def collect_payload(events) -> dict | None:
    """Collect the structured assistant payload to persist for a turn.

    Un turno può emettere sia un carosello sia una riga di bottoni (lo step
    categoria mostra la card della categoria più i bottoni dei formati): si
    persistono entrambi, l'admin li ri-espande in bolle separate. I turni di
    solo testo non hanno payload."""
    payload: dict = {}
    carousel = next((e for e in events if isinstance(e, CarouselEvent)), None)
    if carousel is not None:
        payload["cards"] = carousel.cards
    buttons = next((e for e in events if isinstance(e, ButtonsEvent)), None)
    if buttons is not None:
        payload["buttons"] = buttons.buttons
    return payload or None


def new_topics(before: set[str], state) -> list[str]:
    """Doc del knowledgebase citati in questo turno e non prima, in ordine di
    citazione. Serve a riempire session_topics senza toccare ogni handler che
    può aggiungerne uno."""
    return [d for d in state.topics_cited if d not in before]


_background_tasks: set = set()


def _fire_eval(session_id: str) -> None:
    """Fire-and-forget evaluation; keep a ref so the task isn't GC'd mid-flight."""
    task = asyncio.create_task(run_evaluation(session_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _abandon_sweep_loop() -> None:
    """Periodically mark idle non-completed chats abandoned + run their eval."""
    while True:
        try:
            async with db.transaction() as conn:
                ids = await chats.sweep_abandoned(conn)
            for sid, profile in ids:
                if profile is not None:
                    _fire_eval(sid)
        except Exception:
            logger.exception("abandon sweep failed")
        await asyncio.sleep(60)


_PURGE_INTERVAL_SECONDS = 24 * 60 * 60


async def _retention_purge_loop() -> None:
    """Daily retention purge (compliance C13). A no-op unless RETENTION_ENABLED
    — `retention.purge_cycle` is the gate; only row counts are ever logged."""
    while True:
        try:
            async with db.transaction() as conn:
                await retention.purge_cycle(conn, settings)
        except Exception:
            logger.exception("retention purge failed")
        await asyncio.sleep(_PURGE_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool(settings.database_url)
    sweep_task = asyncio.create_task(_abandon_sweep_loop())
    purge_task = asyncio.create_task(_retention_purge_loop())
    yield
    for task in (sweep_task, purge_task):
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    await db.close_pool()


app = FastAPI(title="13 Protein Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod via env var
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Bounds on client-supplied fields: session ids are ~30 chars in practice, and
# user messages are capped to keep a single turn's LLM prompt cost bounded
# (the UI textarea enforces a lower limit; this is the server-side backstop).
MAX_SESSION_ID_LEN = 64
MAX_MESSAGE_LEN = 2000


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=MAX_SESSION_ID_LEN)
    message: str
    default_language: str | None = None
    is_testing: bool = False


class ResetResponse(BaseModel):
    session_id: str


class SkipResponse(BaseModel):
    lead_info: dict


@app.post("/chat")
async def chat(req: ChatRequest):
    collected_text: list[str] = []

    # Server-side backstop on message size (the UI textarea enforces a lower
    # limit); truncating instead of rejecting keeps a pasted-too-much turn alive.
    user_message = req.message[:MAX_MESSAGE_LEN]

    async def generate():
        seen_events: list = []
        usage_token = usage.start()
        try:
            # Two short transactions bracket the turn instead of one held open
            # across it: the handler's LLM calls can take tens of seconds, and a
            # connection pinned for that long exhausts the pool under concurrent
            # load (worse: exposure.get_counts acquires a second connection
            # mid-turn, which can deadlock a saturated pool). Handlers never
            # touch the request connection — they only mutate `state` — so
            # nothing is lost by releasing it during streaming. Failure
            # semantics are unchanged: a handler error means the write
            # transaction never runs, so no half-saved turn is persisted.
            async with db.transaction() as conn:
                state = await session.load(req.session_id, conn)
            if req.default_language:
                state.default_language = req.default_language
            before_topics = set(state.topics_cited)
            handler = dispatch(state.current_step)
            async for event in handler(state, user_message):
                seen_events.append(event)
                chunk = format_sse(event)
                if hasattr(event, "token"):
                    collected_text.append(event.token)
                elif isinstance(event, MessageBreakEvent):
                    # Mark the bubble split so the stored transcript can be
                    # re-expanded into two bubbles, matching the live client.
                    collected_text.append(MESSAGE_BREAK)
                yield chunk
            acc = usage.current()
            assistant_text = "".join(collected_text)
            payload = collect_payload(seen_events)
            has_visible_content = (
                any(seg.strip() for seg in assistant_text.split(MESSAGE_BREAK))
                or bool(payload and (payload.get("cards") or payload.get("buttons")))
            )
            if has_visible_content:
                turn_cost = acc.cost + state.pending_cost
                turn_prompt_tokens = acc.prompt_tokens + state.pending_prompt_tokens
                turn_completion_tokens = (
                    acc.completion_tokens + state.pending_completion_tokens
                )
                turn_models = set(acc.models) | set(state.pending_models)
                state.pending_cost = 0.0
                state.pending_prompt_tokens = 0
                state.pending_completion_tokens = 0
                state.pending_models = []
            else:
                state.pending_cost += acc.cost
                state.pending_prompt_tokens += acc.prompt_tokens
                state.pending_completion_tokens += acc.completion_tokens
                state.pending_models = list(set(state.pending_models) | set(acc.models))
                turn_cost = turn_prompt_tokens = turn_completion_tokens = None
                turn_models = None
            async with db.transaction() as conn:
                new_docs = new_topics(before_topics, state)
                if new_docs:
                    await conn.executemany(
                        "INSERT INTO session_topics (session_id, doc) VALUES ($1, $2)",
                        [(req.session_id, d) for d in new_docs],
                    )
                await session.save(req.session_id, state, conn, is_testing=req.is_testing)
                model_str = ",".join(sorted(turn_models)) if turn_models else None
                await transcripts.append(
                    req.session_id, user_message, state,
                    assistant_text, conn,
                    assistant_payload=payload,
                    cost=turn_cost, prompt_tokens=turn_prompt_tokens,
                    completion_tokens=turn_completion_tokens, model=model_str,
                )
                await chats.add_usage(
                    req.session_id, acc.cost, acc.prompt_tokens,
                    acc.completion_tokens, conn,
                )
                just_completed = (
                    state.current_step == Step.COMPLETED
                    and await chats.mark_completed(req.session_id, conn)
                )
            if just_completed:
                _fire_eval(req.session_id)
        except Exception:
            # Any open transaction already rolled back, so no half-saved turn is
            # persisted; emit a clean `error` event so the client isn't left with a
            # truncated stream.
            logger.exception("chat turn failed for session %s", req.session_id)
            lang = req.default_language or "en"
            message = _STREAM_ERROR_MESSAGE.get(lang, _STREAM_ERROR_MESSAGE["en"])
            yield format_sse(ErrorEvent(message=message))
        finally:
            usage.reset(usage_token)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/chats")
async def chats_list(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    def _parse(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    df = _parse(date_from)
    dt = _parse(date_to)
    if dt is not None:
        dt += timedelta(days=1)  # inclusive calendar day -> exclusive bound
    async with db.transaction() as conn:
        abandoned = await chats.sweep_abandoned(conn)
        result = await chats.list_chats(conn, df, dt)
    for sid, profile in abandoned:
        if profile is not None:
            _fire_eval(sid)
    return result


@app.get("/chats/{session_id}")
async def chats_detail(session_id: str):
    async with db.transaction() as conn:
        result = await chats.get_chat(session_id, conn)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="chat not found")
    return result


class SettingsBody(BaseModel):
    abandon_timeout_minutes: int


@app.get("/settings")
async def get_settings():
    async with db.transaction() as conn:
        return {"abandon_timeout_minutes": await chats.get_abandon_timeout(conn)}


@app.put("/settings")
async def put_settings(body: SettingsBody):
    minutes = max(0, int(body.abandon_timeout_minutes))
    async with db.transaction() as conn:
        await chats.set_abandon_timeout(conn, minutes)
    return {"abandon_timeout_minutes": minutes}


@app.get("/report")
async def report(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    narrative: bool = Query(True),
):
    from fastapi import HTTPException

    try:
        date_from = datetime.fromisoformat(from_)
        date_to = datetime.fromisoformat(to) + timedelta(days=1) - timedelta(microseconds=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="from/to must be ISO dates (YYYY-MM-DD)")
    async with db.transaction() as conn:
        stats = await reporting.build_report(conn, date_from, date_to)
    if not narrative:
        # Solo la parte deterministica: usata dal Resoconto per l'aggiornamento
        # istantaneo al cambio date (zero costi LLM).
        return {"stats": stats}
    # by_weekday is deterministic-only data (admin charts + client-built report
    # text): keep it out of the narrative LLM's input so the prose never
    # mentions it.
    narrative_out = await report_agents.generate_narrative(
        {k: v for k, v in stats.items() if k != "by_weekday"})
    return {"stats": stats, "narrative": narrative_out}


@app.post("/reset", response_model=ResetResponse)
async def reset():
    return ResetResponse(session_id=str(uuid.uuid4()))


@app.post("/chat/{session_id}/skip", response_model=SkipResponse)
async def skip(session_id: str):
    from fastapi import HTTPException

    async with db.transaction() as conn:
        if not await session.is_testing(session_id, conn):
            raise HTTPException(status_code=403, detail="Session is not a testing session")
        state = await session.load(session_id, conn)
        facsimile = testing_env.load_facsimile(state.profile)
        merged = testing_env.merge_with_facsimile(state.to_lead_info(), facsimile)
        state.current_step = Step.COMPLETED
        await session.save(session_id, state, conn, is_testing=True)
        just_completed = await chats.mark_completed(session_id, conn)
    if just_completed:
        _fire_eval(session_id)
    return SkipResponse(lead_info=merged)


@app.get("/health")
async def health():
    return {"status": "ok"}
