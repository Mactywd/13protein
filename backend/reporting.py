# backend/reporting.py
"""Aggregazioni per periodo del Resoconto admin. Ogni funzione fa una query
SQL; build_report le compone nel dict servito da GET /report. **Tutti i numeri
sono calcolati qui in SQL**: la narrativa LLM (report_agents.py) scrive solo la
prosa intorno, non ricalcola nulla e non deve produrre cifre."""
from __future__ import annotations
from datetime import datetime
import asyncpg

# Colonne di qualificazione su cui si può fare il breakdown. Whitelist esplicita:
# il nome finisce interpolato nella query, un parametro non basterebbe.
BREAKDOWN_COLUMNS = ("profile", "category", "format")


async def breakdown(conn: asyncpg.Connection, column: str, date_from: datetime,
                    date_to: datetime) -> list[dict]:
    """Sessioni e tasso di completamento per valore di una colonna di qualificazione."""
    if column not in BREAKDOWN_COLUMNS:
        raise ValueError(f"colonna non ammessa per il breakdown: {column!r}")
    rows = await conn.fetch(
        f"""
        SELECT {column} AS value,
               count(*) AS total,
               count(*) FILTER (WHERE completed_at IS NOT NULL) AS completed
          FROM sessions
         WHERE is_testing = false AND {column} IS NOT NULL
           AND created_at BETWEEN $1 AND $2
         GROUP BY {column}
         ORDER BY total DESC
        """,
        date_from, date_to,
    )
    out = []
    for r in rows:
        total = r["total"] or 0
        completed = r["completed"] or 0
        out.append({
            "value": r["value"],
            "total": total,
            "completed": completed,
            "completion_rate": (completed / total) if total else 0.0,
        })
    return out


async def quote_rate(conn: asyncpg.Connection, date_from: datetime,
                     date_to: datetime) -> dict:
    """Quota di richieste di preventivo sulle sessioni che hanno superato l'intro
    (profile valorizzato): prima di quel punto il preventivo non è proponibile."""
    row = await conn.fetchrow(
        """
        SELECT count(*) FILTER (WHERE quote_requested = true) AS requested,
               count(*) AS qualified
          FROM sessions
         WHERE is_testing = false AND profile IS NOT NULL
           AND created_at BETWEEN $1 AND $2
        """,
        date_from, date_to,
    )
    qualified = row["qualified"] or 0
    requested = row["requested"] or 0
    return {"requested": requested, "qualified": qualified,
            "rate": (requested / qualified) if qualified else 0.0}


async def duration_stats(conn: asyncpg.Connection, date_from: datetime,
                         date_to: datetime) -> dict:
    row = await conn.fetchrow(
        """
        SELECT percentile_cont(0.5) WITHIN GROUP (
                 ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at))
               ) AS median_seconds,
               avg(EXTRACT(EPOCH FROM (completed_at - created_at))) AS mean_seconds
          FROM sessions
         WHERE is_testing = false AND completed_at IS NOT NULL
           AND created_at BETWEEN $1 AND $2
        """,
        date_from, date_to,
    )
    return {
        "median_seconds": float(row["median_seconds"]) if row["median_seconds"] is not None else None,
        "mean_seconds": float(row["mean_seconds"]) if row["mean_seconds"] is not None else None,
    }


async def friction_stats(conn: asyncpg.Connection, date_from: datetime,
                         date_to: datetime) -> dict:
    """Le note di attrito libere delle valutazioni, per le sessioni del periodo.
    L'agente del report ci legge dentro i temi ricorrenti da sé (nessuna
    categorizzazione qui). La lista è tagliata a 100 (più recenti prima) per
    limitare i token del report; sessions_with_problems è il conteggio pieno."""
    problem_rows = await conn.fetch(
        """
        SELECT s.profile, s.category, e.outcome, e.friction_note AS note
          FROM evaluations e
          JOIN sessions s ON s.id = e.session_id
         WHERE s.is_testing = false AND s.created_at BETWEEN $1 AND $2
           AND e.friction_note IS NOT NULL AND btrim(e.friction_note) <> ''
         ORDER BY s.created_at DESC
         LIMIT 100
        """,
        date_from, date_to,
    )
    count_row = await conn.fetchrow(
        """
        SELECT count(*) AS n
          FROM evaluations e
          JOIN sessions s ON s.id = e.session_id
         WHERE s.is_testing = false AND s.created_at BETWEEN $1 AND $2
           AND e.friction_note IS NOT NULL AND btrim(e.friction_note) <> ''
        """,
        date_from, date_to,
    )
    return {
        "sessions_with_problems": count_row["n"] or 0,
        "problems": [{"profile": r["profile"], "category": r["category"],
                      "outcome": r["outcome"], "note": r["note"]} for r in problem_rows],
    }


async def top_topics(conn: asyncpg.Connection, date_from: datetime,
                     date_to: datetime, limit: int = 5) -> list[dict]:
    """Le pagine del knowledgebase più citate nelle risposte del periodo."""
    rows = await conn.fetch(
        """
        SELECT st.doc, count(*) AS n
          FROM session_topics st
          JOIN sessions s ON s.id = st.session_id
         WHERE s.is_testing = false AND s.created_at BETWEEN $1 AND $2
         GROUP BY st.doc
         ORDER BY n DESC
         LIMIT $3
        """,
        date_from, date_to, limit,
    )
    return [{"doc": r["doc"], "count": r["n"]} for r in rows]


async def total_sessions(conn: asyncpg.Connection, date_from: datetime,
                         date_to: datetime) -> int:
    row = await conn.fetchrow(
        "SELECT count(*) AS n FROM sessions WHERE is_testing = false AND created_at BETWEEN $1 AND $2",
        date_from, date_to,
    )
    return row["n"] or 0


async def sessions_by_weekday(conn: asyncpg.Connection, date_from: datetime,
                              date_to: datetime) -> list[dict]:
    """Quota di conversazioni per giorno ISO (1=lun .. 7=dom). Resa solo nelle
    tabelle admin: il chiamante di build_report la toglie dalle stat passate
    alla narrativa. I giorni senza sessioni compaiono comunque a 0."""
    rows = await conn.fetch(
        """
        SELECT EXTRACT(ISODOW FROM created_at)::int AS dow, count(*) AS n
          FROM sessions
         WHERE is_testing = false AND created_at BETWEEN $1 AND $2
         GROUP BY dow
         ORDER BY dow
        """,
        date_from, date_to,
    )
    counts = {r["dow"]: r["n"] for r in rows}
    total = sum(counts.values())
    return [
        {"weekday": d, "count": counts.get(d, 0),
         "share": (counts.get(d, 0) / total) if total else 0.0}
        for d in range(1, 8)
    ]


async def outcome_stats(conn: asyncpg.Connection, date_from: datetime,
                        date_to: datetime) -> dict:
    """Esiti delle conversazioni nel periodo. Le quote sono calcolate su
    completate+abbandonate+inizializzate ("decided_total"); le sessioni ancora
    in corso sono solo un conteggio informativo, mai nel denominatore."""
    row = await conn.fetchrow(
        """
        SELECT count(*) FILTER (WHERE completed_at IS NOT NULL) AS completed,
               count(*) FILTER (WHERE completed_at IS NULL AND abandoned_at IS NOT NULL
                                  AND profile IS NOT NULL) AS abandoned,
               count(*) FILTER (WHERE completed_at IS NULL AND abandoned_at IS NOT NULL
                                  AND profile IS NULL) AS initialized,
               count(*) FILTER (WHERE completed_at IS NULL AND abandoned_at IS NULL) AS in_progress
          FROM sessions
         WHERE is_testing = false AND created_at BETWEEN $1 AND $2
        """,
        date_from, date_to,
    )
    completed = row["completed"] or 0
    abandoned = row["abandoned"] or 0
    initialized = row["initialized"] or 0
    decided = completed + abandoned + initialized
    return {
        "completed": completed,
        "abandoned": abandoned,
        "initialized": initialized,
        "in_progress": row["in_progress"] or 0,
        "decided_total": decided,
        "completed_share": (completed / decided) if decided else 0.0,
        "abandoned_share": (abandoned / decided) if decided else 0.0,
        "initialized_share": (initialized / decided) if decided else 0.0,
    }


async def build_report(conn: asyncpg.Connection, date_from: datetime,
                       date_to: datetime) -> dict:
    return {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "total_sessions": await total_sessions(conn, date_from, date_to),
        "outcomes": await outcome_stats(conn, date_from, date_to),
        "by_profile": await breakdown(conn, "profile", date_from, date_to),
        "by_category": await breakdown(conn, "category", date_from, date_to),
        "by_format": await breakdown(conn, "format", date_from, date_to),
        "quote": await quote_rate(conn, date_from, date_to),
        "duration": await duration_stats(conn, date_from, date_to),
        "friction": await friction_stats(conn, date_from, date_to),
        "top_topics": await top_topics(conn, date_from, date_to),
        "by_weekday": await sessions_by_weekday(conn, date_from, date_to),
    }
