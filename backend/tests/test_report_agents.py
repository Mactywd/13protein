import pytest
from unittest.mock import AsyncMock, patch
import report_agents


@pytest.mark.asyncio
async def test_generate_narrative_passes_stats_and_returns_structured_result():
    stats = {"total_sessions": 10, "by_profile": []}
    expected = {"friction_text": "test", "recommendations": ["a"]}
    with patch("report_agents.llm.complete_structured",
               new=AsyncMock(return_value=expected)) as mock_call:
        out = await report_agents.generate_narrative(stats)
    assert out == expected
    system_arg = mock_call.call_args[0][0]
    assert system_arg.startswith("# Prompt: report_summary\n")
    assert '"total_sessions": 10' in system_arg


@pytest.mark.asyncio
async def test_generate_narrative_keeps_accents_unescaped():
    with patch("report_agents.llm.complete_structured",
               new=AsyncMock(return_value={})) as mock_call:
        await report_agents.generate_narrative({"note": "però"})
    assert "però" in mock_call.call_args[0][0]
