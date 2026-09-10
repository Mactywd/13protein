"""Retention purge — art. 5.1.e GDPR (compliance C13).

Two cutoffs, because the personal content and the reporting row do not have
the same lifetime:

  content_days  the conversation itself. Transcript rows are deleted and the
                narrative kept in `sessions.state` is scrubbed — that JSONB
                carries the description the user wrote and their contact
                details, so leaving it behind would make the transcript
                deletion cosmetic. The session row survives with its
                non-personal reporting columns (profile, category, format,
                cost), so the Resoconto keeps its history.
  session_days  the row itself, cascading `evaluations`, `transcripts` and
                `session_topics` (all `ON DELETE CASCADE`).

Everything here counts rows and returns counts: the caller logs numbers, never
content — a purge job that logs what it deleted just moves the data into the
log file.

I termini in `config.py` sono **segnaposto** (24 mesi entrambi) e il purge gira
in dry run finché non li fissa il titolare e non esiste un'informativa. Lo stadio
sul contenuto gira comunque per primo nella stessa passata, quindi abbassare
`RETENTION_CONTENT_DAYS` è una modifica a una variabile sola che lascia in vita
più a lungo la riga di reporting.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Rows are selected by *last activity*, not creation: a session idle for
# `content_days` is expired regardless of how long it ran.
_DELETE_TRANSCRIPTS = """
    DELETE FROM transcripts
     WHERE session_id IN (SELECT id FROM sessions WHERE updated_at < $1)
"""
_COUNT_TRANSCRIPTS = """
    SELECT count(*) FROM transcripts
     WHERE session_id IN (SELECT id FROM sessions WHERE updated_at < $1)
"""
_SCRUB_STATE = """
    UPDATE sessions SET state = '{}'::jsonb
     WHERE updated_at < $1 AND state <> '{}'::jsonb
"""
_COUNT_STATE = """
    SELECT count(*) FROM sessions
     WHERE updated_at < $1 AND state <> '{}'::jsonb
"""
_DELETE_SESSIONS = "DELETE FROM sessions WHERE updated_at < $1"
_COUNT_SESSIONS = "SELECT count(*) FROM sessions WHERE updated_at < $1"


def _rows(tag: str) -> int:
    """asyncpg returns a command tag ("DELETE 12"); we want the count.

    Il conteggio è deliberatamente l'unica traccia che il purge lascia — non si
    logga il contenuto — quindi uno zero silenzioso su un tag inatteso renderebbe
    "non ho trovato nulla" indistinguibile da "ho svuotato il database". Zero
    resta il valore di ritorno, ma non passa più inosservato.
    """
    try:
        return int(str(tag).rsplit(" ", 1)[1])
    except (IndexError, ValueError):
        logger.warning("retention: command tag non interpretabile (%r): conteggio riportato a 0", tag)
        return 0


async def purge_expired(
    conn,
    *,
    content_days: int,
    session_days: int,
    now: datetime | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Delete expired data, or count it without touching anything (dry run).

    Raises ValueError on a configuration that would delete more than intended —
    a stray `RETENTION_CONTENT_DAYS=0` must fail loudly, not wipe the database
    on the next tick.
    """
    if content_days <= 0 or session_days <= 0:
        raise ValueError("retention terms must be positive")
    if session_days < content_days:
        raise ValueError("sessions must outlive their content")

    now = now or datetime.now(timezone.utc)
    content_cutoff = now - timedelta(days=content_days)
    session_cutoff = now - timedelta(days=session_days)

    if dry_run:
        return {
            "transcripts": await conn.fetchval(_COUNT_TRANSCRIPTS, content_cutoff),
            "states_scrubbed": await conn.fetchval(_COUNT_STATE, content_cutoff),
            "sessions": await conn.fetchval(_COUNT_SESSIONS, session_cutoff),
        }

    return {
        "transcripts": _rows(await conn.execute(_DELETE_TRANSCRIPTS, content_cutoff)),
        "states_scrubbed": _rows(await conn.execute(_SCRUB_STATE, content_cutoff)),
        "sessions": _rows(await conn.execute(_DELETE_SESSIONS, session_cutoff)),
    }


async def purge_cycle(conn, cfg) -> dict[str, int] | None:
    """One pass, gated on configuration. Returns None when disabled.

    Deletes, unless `RETENTION_DRY_RUN=true` puts it back to counting — which
    is how you look at the effect of a shorter term before it bites. The
    deletion is final and does not reach the backups (C15).
    """
    if not cfg.retention_enabled:
        return None

    counts = await purge_expired(
        conn,
        content_days=cfg.retention_content_days,
        session_days=cfg.retention_session_days,
        dry_run=cfg.retention_dry_run,
    )
    logger.info(
        "retention purge (%s): transcripts=%d states=%d sessions=%d",
        "dry-run" if cfg.retention_dry_run else "applied",
        counts["transcripts"], counts["states_scrubbed"], counts["sessions"],
    )
    return counts
