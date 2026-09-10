"""Tests for the GDPR retention purge (compliance C13).

The purge is the mechanism behind art. 5.1.e: two cutoffs, not one.
  - `content_days`  — the conversation itself (transcripts + the narrative
    stored in `sessions.state`) disappears, but the session row survives so
    the Resoconto keeps its history;
  - `session_days`  — the row itself goes, cascading evaluations and
    session_essences.

Every test drives a fake connection: what matters is *which* rows the SQL
targets and that a dry run touches nothing.
"""
import pytest
from datetime import datetime, timezone, timedelta

import retention

NOW = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)


class FakeConn:
    """Records executed statements; answers with an asyncpg-style tag."""

    def __init__(self, tags: list[str] | None = None):
        self.calls: list[tuple[str, tuple]] = []
        self._tags = list(tags or [])

    async def execute(self, query: str, *args) -> str:
        self.calls.append((query, args))
        return self._tags.pop(0) if self._tags else "DELETE 0"

    async def fetchval(self, query: str, *args) -> int:
        self.calls.append((query, args))
        return self._tags.pop(0) if self._tags else 0


@pytest.mark.asyncio
async def test_purge_reports_rows_removed_per_category():
    conn = FakeConn(["DELETE 12", "UPDATE 4", "DELETE 2"])
    out = await retention.purge_expired(
        conn, content_days=365, session_days=730, now=NOW
    )
    assert out == {"transcripts": 12, "states_scrubbed": 4, "sessions": 2}


@pytest.mark.asyncio
async def test_purge_uses_the_two_distinct_cutoffs():
    conn = FakeConn(["DELETE 1", "UPDATE 1", "DELETE 1"])
    await retention.purge_expired(conn, content_days=365, session_days=730, now=NOW)

    cutoffs = [args[0] for _, args in conn.calls]
    assert cutoffs[0] == NOW - timedelta(days=365)   # transcripts
    assert cutoffs[1] == NOW - timedelta(days=365)   # state scrub
    assert cutoffs[2] == NOW - timedelta(days=730)   # session rows


@pytest.mark.asyncio
async def test_purge_scrubs_the_narrative_before_dropping_the_row():
    """The state JSONB holds the memory the user told us — it must be part of
    the content purge, not survive until the session cutoff."""
    conn = FakeConn(["DELETE 0", "UPDATE 3", "DELETE 0"])
    await retention.purge_expired(conn, content_days=365, session_days=730, now=NOW)

    scrub = conn.calls[1][0].lower()
    assert "update sessions" in scrub
    assert "state" in scrub


@pytest.mark.asyncio
async def test_dry_run_counts_without_deleting_anything():
    conn = FakeConn([7, 3, 1])
    out = await retention.purge_expired(
        conn, content_days=365, session_days=730, now=NOW, dry_run=True
    )
    assert out == {"transcripts": 7, "states_scrubbed": 3, "sessions": 1}
    assert not any(
        q.lstrip().lower().startswith(("delete", "update")) for q, _ in conn.calls
    )


class FakeCfg:
    def __init__(self, **kw):
        self.retention_enabled = kw.get("enabled", False)
        self.retention_dry_run = kw.get("dry_run", False)
        self.retention_content_days = kw.get("content_days", 365)
        self.retention_session_days = kw.get("session_days", 730)


@pytest.mark.asyncio
async def test_cycle_does_nothing_while_the_terms_are_unapproved():
    """Disabled is the default: no term has been signed off by the controller
    (L5), so the job must not delete anything until it is switched on."""
    conn = FakeConn()
    assert await retention.purge_cycle(conn, FakeCfg(enabled=False)) is None
    assert conn.calls == []


@pytest.mark.asyncio
async def test_cycle_honours_dry_run_when_enabled():
    conn = FakeConn([5, 0, 0])
    out = await retention.purge_cycle(conn, FakeCfg(enabled=True, dry_run=True))
    assert out["transcripts"] == 5
    assert all(q.lstrip().lower().startswith("select") for q, _ in conn.calls)


@pytest.mark.asyncio
async def test_cycle_deletes_when_enabled_and_not_dry_running():
    conn = FakeConn(["DELETE 9", "UPDATE 0", "DELETE 0"])
    out = await retention.purge_cycle(conn, FakeCfg(enabled=True, dry_run=False))
    assert out["transcripts"] == 9
    assert conn.calls[0][0].lstrip().lower().startswith("delete")


@pytest.mark.asyncio
async def test_purge_refuses_a_non_positive_retention():
    """A misconfigured `RETENTION_CONTENT_DAYS=0` would wipe the database on
    the next tick — fail loudly instead."""
    conn = FakeConn()
    with pytest.raises(ValueError):
        await retention.purge_expired(conn, content_days=0, session_days=730, now=NOW)
    assert conn.calls == []


@pytest.mark.asyncio
async def test_purge_refuses_a_session_cutoff_shorter_than_the_content_one():
    """Sessions must outlive their content, never the reverse."""
    conn = FakeConn()
    with pytest.raises(ValueError):
        await retention.purge_expired(conn, content_days=730, session_days=365, now=NOW)
    assert conn.calls == []
