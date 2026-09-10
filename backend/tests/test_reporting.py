import pytest
from datetime import datetime, timezone
import reporting

FROM = datetime(2026, 6, 1, tzinfo=timezone.utc)
TO = datetime(2026, 7, 1, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_breakdown_computes_completion_rate():
    class FakeConn:
        async def fetch(self, q, *a):
            return [
                {"value": "product_idea", "total": 10, "completed": 5},
                {"value": "new_brand", "total": 4, "completed": 4},
            ]
    out = await reporting.breakdown(FakeConn(), "profile", FROM, TO)
    assert out[0]["value"] == "product_idea" and out[0]["completion_rate"] == 0.5
    assert out[1]["completion_rate"] == 1.0


@pytest.mark.asyncio
async def test_breakdown_interpolates_only_whitelisted_columns():
    class FakeConn:
        async def fetch(self, q, *a):
            assert " category " in q or "category AS value" in q
            return []
    await reporting.breakdown(FakeConn(), "category", FROM, TO)
    with pytest.raises(ValueError):
        await reporting.breakdown(FakeConn(), "id; DROP TABLE sessions", FROM, TO)


@pytest.mark.asyncio
async def test_quote_rate_handles_zero_denominator():
    class FakeConn:
        async def fetchrow(self, q, *a):
            return {"requested": 0, "qualified": 0}
    assert await reporting.quote_rate(FakeConn(), FROM, TO) == {
        "requested": 0, "qualified": 0, "rate": 0.0}


@pytest.mark.asyncio
async def test_quote_rate_computes_ratio():
    class FakeConn:
        async def fetchrow(self, q, *a):
            return {"requested": 3, "qualified": 12}
    assert (await reporting.quote_rate(FakeConn(), FROM, TO))["rate"] == 0.25


@pytest.mark.asyncio
async def test_duration_stats_passes_through_nulls():
    class FakeConn:
        async def fetchrow(self, q, *a):
            return {"median_seconds": None, "mean_seconds": None}
    assert await reporting.duration_stats(FakeConn(), FROM, TO) == {
        "median_seconds": None, "mean_seconds": None}


@pytest.mark.asyncio
async def test_duration_stats_converts_to_float():
    class FakeConn:
        async def fetchrow(self, q, *a):
            return {"median_seconds": 439.0, "mean_seconds": 575.5}
    assert await reporting.duration_stats(FakeConn(), FROM, TO) == {
        "median_seconds": 439.0, "mean_seconds": 575.5}


@pytest.mark.asyncio
async def test_friction_stats_returns_problem_notes():
    class FakeConn:
        async def fetch(self, q, *a):
            return [{"profile": "new_brand", "category": "proteins",
                     "outcome": "abandoned", "note": "Bloccato sulla descrizione."}]
        async def fetchrow(self, q, *a):
            return {"n": 1}
    out = await reporting.friction_stats(FakeConn(), FROM, TO)
    assert out["sessions_with_problems"] == 1
    assert out["problems"][0]["note"] == "Bloccato sulla descrizione."
    assert out["problems"][0]["profile"] == "new_brand"


@pytest.mark.asyncio
async def test_top_topics_shapes_rows():
    class FakeConn:
        async def fetch(self, q, *a):
            return [{"doc": "quality", "n": 7}, {"doc": "private-label", "n": 3}]
    out = await reporting.top_topics(FakeConn(), FROM, TO)
    assert out == [{"doc": "quality", "count": 7}, {"doc": "private-label", "count": 3}]


@pytest.mark.asyncio
async def test_outcome_stats_shares_exclude_in_progress():
    class FakeConn:
        async def fetchrow(self, q, *a):
            return {"completed": 5, "abandoned": 3, "initialized": 2, "in_progress": 4}
    out = await reporting.outcome_stats(FakeConn(), FROM, TO)
    assert out["decided_total"] == 10
    assert out["completed_share"] == 0.5
    assert out["in_progress"] == 4


@pytest.mark.asyncio
async def test_sessions_by_weekday_fills_missing_days():
    class FakeConn:
        async def fetch(self, q, *a):
            return [{"dow": 1, "n": 3}, {"dow": 5, "n": 1}]
    out = await reporting.sessions_by_weekday(FakeConn(), FROM, TO)
    assert [r["weekday"] for r in out] == [1, 2, 3, 4, 5, 6, 7]
    assert out[0]["count"] == 3 and out[0]["share"] == 0.75
    assert out[1]["count"] == 0 and out[1]["share"] == 0.0


@pytest.mark.asyncio
async def test_build_report_keys():
    class FakeConn:
        async def fetch(self, q, *a):
            return []
        async def fetchrow(self, q, *a):
            return {"n": 0, "completed": 0, "abandoned": 0, "initialized": 0,
                    "in_progress": 0, "requested": 0, "qualified": 0,
                    "median_seconds": None, "mean_seconds": None}
    out = await reporting.build_report(FakeConn(), FROM, TO)
    assert set(out) == {"period", "total_sessions", "outcomes", "by_profile",
                        "by_category", "by_format", "quote", "duration",
                        "friction", "top_topics", "by_weekday"}
    assert out["period"]["from"] == FROM.isoformat()
