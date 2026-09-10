import asyncpg
from models import SessionState


async def load(session_id: str, conn: asyncpg.Connection) -> SessionState:
    row = await conn.fetchrow(
        "SELECT state FROM sessions WHERE id = $1",
        session_id,
    )
    if row is None:
        return SessionState()
    return SessionState.model_validate_json(row["state"])


async def is_testing(session_id: str, conn: asyncpg.Connection) -> bool:
    """Whether the session is already flagged is_testing in Postgres.

    Returns False if the session doesn't exist yet (e.g. a session_id that
    was never used in a prior /chat turn)."""
    row = await conn.fetchrow(
        "SELECT is_testing FROM sessions WHERE id = $1",
        session_id,
    )
    if row is None:
        return False
    return bool(row["is_testing"])


async def save(
    session_id: str,
    state: SessionState,
    conn: asyncpg.Connection,
    is_testing: bool = False,
) -> None:
    await conn.execute(
        """
        INSERT INTO sessions (id, state, updated_at, is_testing,
                              profile, category, format, quote_requested)
        VALUES ($1, $2::jsonb, now(), $3, $4, $5, $6, $7)
        ON CONFLICT (id) DO UPDATE
            SET state = $2::jsonb, updated_at = now(), abandoned_at = NULL,
                is_testing = sessions.is_testing OR EXCLUDED.is_testing,
                profile = EXCLUDED.profile,
                category = EXCLUDED.category,
                format = EXCLUDED.format,
                quote_requested = EXCLUDED.quote_requested
        """,
        session_id,
        state.model_dump_json(),
        is_testing,
        state.profile,
        state.category,
        state.format,
        state.quote_requested,
    )
