"""Supporto al pulsante "Salta conversazione" dell'ambiente /testing.

Fonde il `lead_info` corrente (quasi tutto ai valori vuoti) con un facsimile per
profilo, sostituendo solo i campi ancora al loro valore di "non risposto": i
sentinella qui sotto sono esattamente quelli prodotti da
SessionState.to_lead_info() su uno stato vergine (models.py).
"""
from __future__ import annotations
import json
from pathlib import Path

FACSIMILES_PATH = Path(__file__).parent / "data" / "testing_facsimiles.json"

DEFAULT_PROFILE = "product_idea"

FIELD_SENTINELS: dict[str, object] = {
    "profile": None,
    "category": None,
    "format": None,
    "projectDescription": None,
    "questionsAsked": [],
    "topicsCited": [],
    "quoteRequested": False,
    "contact": {"name": None, "company": None, "email": None},
}


def load_facsimile(profile: str | None) -> dict:
    with FACSIMILES_PATH.open(encoding="utf-8") as f:
        facsimiles = json.load(f)
    key = profile if profile in facsimiles else DEFAULT_PROFILE
    return facsimiles[key]


def merge_with_facsimile(current: dict, facsimile: dict) -> dict:
    merged = dict(current)
    for field, sentinel in FIELD_SENTINELS.items():
        if merged.get(field) == sentinel and field in facsimile:
            merged[field] = facsimile[field]
    return merged
