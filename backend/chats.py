# backend/chats.py
"""DB layer + transforms for the chat-admin section."""
from __future__ import annotations
import json
import asyncpg
from datetime import datetime

from models import MESSAGE_BREAK

PREVIEW_LEN = 80

DEFAULT_ABANDON_TIMEOUT_MIN = 30
_TIMEOUT_KEY = "abandon_timeout_minutes"


async def get_abandon_timeout(conn) -> int:
    """Configured idle-minutes before a non-completed chat is abandoned.

    Missing row or unparsable value → DEFAULT_ABANDON_TIMEOUT_MIN. 0 = disabled."""
    row = await conn.fetchrow(
        "SELECT value FROM app_settings WHERE key = $1", _TIMEOUT_KEY
    )
    if row is None or row["value"] is None:
        return DEFAULT_ABANDON_TIMEOUT_MIN
    try:
        return int(row["value"])
    except (TypeError, ValueError):
        return DEFAULT_ABANDON_TIMEOUT_MIN


async def set_abandon_timeout(conn, minutes: int) -> None:
    await conn.execute(
        """INSERT INTO app_settings (key, value, updated_at)
                VALUES ($1, $2, now())
           ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = now()""",
        _TIMEOUT_KEY, str(int(minutes)),
    )


async def sweep_abandoned(conn) -> list[tuple[str, str | None]]:
    """Mark non-completed chats idle past the timeout as abandoned.

    A chat is swept when it has at least one transcript, is neither completed nor
    already abandoned, and its last activity (sessions.updated_at) is older than
    the configured timeout. Returns `(id, profile)` for each just-marked session,
    so the caller can fire the evaluation only for sessions that got past the
    intro (profile is set)."""
    minutes = await get_abandon_timeout(conn)
    if minutes <= 0:
        return []
    rows = await conn.fetch(
        """UPDATE sessions SET abandoned_at = now()
            WHERE completed_at IS NULL AND abandoned_at IS NULL
              AND updated_at < now() - make_interval(mins => $1)
              AND EXISTS (SELECT 1 FROM transcripts t WHERE t.session_id = sessions.id)
            RETURNING id, profile""",
        minutes,
    )
    return [(r["id"], r["profile"]) for r in rows]


def chat_summary(row) -> dict:
    """One sessions row (joined with first user message + eval status) → list item."""
    created = row["created_at"]
    completed = row["completed_at"]
    abandoned = row.get("abandoned_at")
    profile = row.get("profile")
    duration = int((completed - created).total_seconds()) if completed and created else None
    if completed:
        status = "completata"
    elif abandoned and profile is None:
        status = "inizializzata"
    elif abandoned:
        status = "abbandonata"
    else:
        status = "in_corso"
    return {
        "session_id": row["id"],
        "created_at": created.isoformat() if created else None,
        "completed_at": completed.isoformat() if completed else None,
        "duration_seconds": duration,
        "status": status,
        "total_cost": float(row["total_cost"] or 0),
        "prompt_tokens": int(row["prompt_tokens"] or 0),
        "completion_tokens": int(row["completion_tokens"] or 0),
        "preview": row["preview"],
        "profile": profile,
        "category": row.get("category"),
        "format": row.get("format"),
        "quote_requested": bool(row.get("quote_requested")),
        "eval_status": row["eval_status"],
        "is_testing": row.get("is_testing", False),
    }


def _ts(row) -> str | None:
    created = row.get("created_at")
    return created.isoformat() if created else None


def _text_msg(sender: str, content: str, meta: dict) -> dict:
    return {"sender": sender, "type": "text",
            "payload": {"message": content}, "additionalClasses": [], "meta": meta}


def messages_from_row(row) -> list[dict]:
    """One transcripts row → an ordered list of Message.jsx-shaped messages.

    A single assistant turn can produce several bubbles in the live client
    (src/api/Retrieve.jsx handles streamed text, carousel, and buttons through
    separate handlers): the narration text, a category carousel, and a buttons
    row. We persist one transcript row per turn (content + payload), so expand it
    back into that same sequence of bubbles here, in display order
    (text → carousel → buttons). The structured payloads are transformed into the
    exact shape Message.jsx consumes (button.name / button.request.payload.label;
    card.imageUrl / card.description.text / card.buttons[0].name)."""
    payload = row["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    base_meta = {"created_at": _ts(row)}
    if row["role"] == "user":
        # The conversation is kicked off with an empty launch message; don't
        # render it (or any blank user turn) as an empty bubble.
        if not (row["content"] or "").strip():
            return []
        return [_text_msg("user", row["content"], dict(base_meta))]
    # assistant: text bubbles carry full usage meta; carousel/buttons only timestamp.
    ai_meta = {
        **base_meta,
        "cost": float(row["cost"]) if row.get("cost") is not None else None,
        "prompt_tokens": row.get("prompt_tokens"),
        "completion_tokens": row.get("completion_tokens"),
        "model": row.get("model"),
    }
    # narration text first, then carousel, then buttons. A turn that emitted a
    # MessageBreakEvent stored a MESSAGE_BREAK sentinel in its content; split on
    # it so each segment renders as its own bubble, as live.
    out: list[dict] = []
    for segment in (row["content"] or "").split(MESSAGE_BREAK):
        if segment.strip():
            out.append(_text_msg("ai", segment.strip(), dict(ai_meta)))
    if payload and payload.get("cards"):
        cards = [
            {"title": c["title"], "imageUrl": c["image"],
             "description": {"text": c["description"]},
             "buttons": [{"name": c["value"], "label": c["title"]}]}
            for c in payload["cards"]
        ]
        out.append({"sender": "ai", "type": "carousel",
                    "payload": {"cards": cards}, "additionalClasses": [],
                    "meta": dict(base_meta)})
    if payload and payload.get("buttons"):
        buttons = [
            {"name": b["label"],
             "request": {"type": "text", "payload": {"label": b["value"], "name": b["label"]}}}
            for b in payload["buttons"]
        ]
        out.append({"sender": "ai", "type": "choice",
                    "payload": {"buttons": buttons}, "additionalClasses": [],
                    "meta": dict(base_meta)})
    # A turn with no text and no structured payload (e.g. the final completion
    # turn that only emits lead_info) yields nothing to render.
    return out


# Nessun tetto sul numero di chat restituite: il taglio lo fa il periodo. La
# lista admin chiede sempre un intervallo di date (default: ultimi 30 giorni) e
# il vecchio `LIMIT 2000` non lo diceva a nessuno — su un intervallo ampio
# spariva la coda più vecchia senza che l'interfaccia mostrasse alcun segno.
async def list_chats(conn: asyncpg.Connection,
                     date_from: datetime | None = None,
                     date_to: datetime | None = None) -> list[dict]:
    """Chat summaries, newest first. Optional [date_from, date_to) bounds on
    created_at (date_to exclusive — the API layer passes day+1 for an
    inclusive calendar range)."""
    where = ["EXISTS (SELECT 1 FROM transcripts t WHERE t.session_id = s.id)"]
    args: list = []
    if date_from is not None:
        args.append(date_from)
        where.append(f"s.created_at >= ${len(args)}")
    if date_to is not None:
        args.append(date_to)
        where.append(f"s.created_at < ${len(args)}")
    rows = await conn.fetch(
        f"""
        SELECT s.id, s.created_at, s.completed_at, s.abandoned_at, s.profile, s.category, s.format, s.quote_requested, s.total_cost,
               s.prompt_tokens, s.completion_tokens, s.is_testing,
               (SELECT content FROM transcripts t
                  WHERE t.session_id = s.id AND t.role = 'user'
                    AND btrim(t.content) <> ''
                  ORDER BY t.id ASC LIMIT 1) AS preview,
               e.status AS eval_status
          FROM sessions s
          LEFT JOIN evaluations e ON e.session_id = s.id
         WHERE {' AND '.join(where)}
         ORDER BY s.created_at DESC
        """,
        *args,
    )
    out = []
    for r in rows:
        d = dict(r)
        if d.get("preview"):
            d["preview"] = d["preview"][:PREVIEW_LEN]
        out.append(chat_summary(d))
    return out


async def get_chat(session_id: str, conn: asyncpg.Connection) -> dict | None:
    srow = await conn.fetchrow(
        """SELECT id, created_at, completed_at, abandoned_at, profile, category, format, quote_requested, total_cost, prompt_tokens, completion_tokens, is_testing
             FROM sessions WHERE id = $1""",
        session_id,
    )
    if srow is None:
        return None
    trows = await conn.fetch(
        """SELECT role, content, payload, created_at,
                  cost, prompt_tokens, completion_tokens, model
             FROM transcripts
            WHERE session_id = $1 ORDER BY id ASC""",
        session_id,
    )
    erow = await conn.fetchrow(
        """SELECT summary, model, status, updated_at,
                  cost, prompt_tokens, completion_tokens,
                  outcome, friction_note, quote_requested
             FROM evaluations WHERE session_id = $1""",
        session_id,
    )
    sdict = dict(srow)
    sdict["preview"] = None
    sdict["eval_status"] = erow["status"] if erow else None
    messages: list[dict] = []
    for t in trows:
        messages.extend(messages_from_row(dict(t)))
    evaluation = None
    if erow:
        evaluation = {
            "summary": erow["summary"], "model": erow["model"],
            "status": erow["status"],
            "cost": float(erow["cost"]) if erow["cost"] is not None else None,
            "prompt_tokens": erow["prompt_tokens"],
            "completion_tokens": erow["completion_tokens"],
            "updated_at": erow["updated_at"].isoformat() if erow["updated_at"] else None,
            "outcome": erow["outcome"],
            "friction_note": erow["friction_note"],
            "quote_requested": erow["quote_requested"],
        }
    return {
        "session": chat_summary(sdict),
        "messages": messages,
        "evaluation": evaluation,
    }


async def add_usage(session_id: str, cost: float, prompt_tokens: int,
                    completion_tokens: int, conn: asyncpg.Connection) -> None:
    await conn.execute(
        """UPDATE sessions
              SET total_cost = COALESCE(total_cost, 0) + $2,
                  prompt_tokens = COALESCE(prompt_tokens, 0) + $3,
                  completion_tokens = COALESCE(completion_tokens, 0) + $4
            WHERE id = $1""",
        session_id, cost, prompt_tokens, completion_tokens,
    )


async def mark_completed(session_id: str, conn: asyncpg.Connection) -> bool:
    """Set completed_at if not already set. Returns True if it transitioned now."""
    row = await conn.fetchrow(
        """UPDATE sessions SET completed_at = now()
            WHERE id = $1 AND completed_at IS NULL
            RETURNING id""",
        session_id,
    )
    return row is not None
