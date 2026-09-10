# backend/agents/evaluation.py
"""Background evaluation of a completed conversation. Fired (fire-and-forget)
from main.py when a session first reaches the completed step. Runs on its own
DB connection because the request transaction is already closed."""
from __future__ import annotations
import logging
from agents import prompts
import chats
import services.db as db
from services import llm, usage

log = logging.getLogger(__name__)


def format_transcript(rows) -> str:
    lines = []
    for r in rows:
        prefix = "U" if r["role"] == "user" else "A"
        lines.append(f"{prefix}: {r['content']}")
    return "\n".join(lines)


async def _upsert(conn, session_id: str, **fields) -> None:
    cols = ", ".join(fields)
    sets = ", ".join(f"{k} = EXCLUDED.{k}" for k in fields)
    placeholders = ", ".join(f"${i + 2}" for i in range(len(fields)))
    await conn.execute(
        f"""INSERT INTO evaluations (session_id, {cols}, updated_at)
            VALUES ($1, {placeholders}, now())
            ON CONFLICT (session_id) DO UPDATE
              SET {sets}, updated_at = now()""",
        session_id, *fields.values(),
    )


async def run_evaluation(session_id: str) -> None:
    try:
        async with db.transaction() as conn:
            await _upsert(conn, session_id, status="pending")
            rows = await conn.fetch(
                "SELECT role, content FROM transcripts WHERE session_id = $1 ORDER BY id ASC",
                session_id,
            )
        transcript = format_transcript(rows)
        prompt = prompts.load("evaluation", transcript=transcript)
        token = usage.start()
        try:
            result = await llm.complete_structured(prompt, "Valuta la conversazione.")
            acc = usage.current()
        finally:
            usage.reset(token)
        async with db.transaction() as conn:
            await _upsert(
                conn, session_id,
                outcome=result.get("outcome"),
                summary=result.get("path_summary"),
                friction_note=result.get("problem"),
                quote_requested=bool(result.get("quote_requested", False)),
                model=llm.model_name(), status="done",
                cost=acc.cost, prompt_tokens=acc.prompt_tokens,
                completion_tokens=acc.completion_tokens,
            )
            await chats.add_usage(session_id, acc.cost, acc.prompt_tokens,
                                  acc.completion_tokens, conn)
    except Exception:  # noqa: BLE001 — background task, must not crash the loop
        log.exception("Evaluation failed for session %s", session_id)
        try:
            async with db.transaction() as conn:
                await _upsert(conn, session_id, status="error")
        except Exception:
            log.exception("Could not mark evaluation error for %s", session_id)
