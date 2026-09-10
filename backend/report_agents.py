# backend/report_agents.py
"""Narrativa LLM del Resoconto: date le statistiche già calcolate, scrive la
prosa di raccordo. I numeri vengono da reporting.py e non sono mai inventati
né ricalcolati qui."""
from __future__ import annotations
import json
from agents import prompts
from services import llm


async def generate_narrative(stats: dict) -> dict:
    system = prompts.load("report_summary", stats_json=json.dumps(stats, ensure_ascii=False))
    return await llm.complete_structured(system, "Genera il commento.")
