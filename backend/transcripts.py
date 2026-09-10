import json
import asyncpg
from models import SessionState


async def append(
    session_id: str,
    user_message: str,
    state: SessionState,
    assistant_text: str,
    conn: asyncpg.Connection,
    assistant_payload: dict | None = None,
    cost: float | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    model: str | None = None,
) -> None:
    payload_json = json.dumps(assistant_payload) if assistant_payload else None
    step = state.current_step.value
    await conn.executemany(
        """
        INSERT INTO transcripts
            (session_id, role, content, step, payload,
             cost, prompt_tokens, completion_tokens, model)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        [
            (session_id, "user", user_message, step, None,
             None, None, None, None),
            (session_id, "assistant", assistant_text, step, payload_json,
             cost, prompt_tokens, completion_tokens, model),
        ],
    )
