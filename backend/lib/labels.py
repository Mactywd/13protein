"""Bottoni canonici: valore = slug del form del sito (knowledgebase/site/forms.md),
etichette EN/IT. Il backend salva sempre il valore, il client mostra la label."""
from __future__ import annotations

# group -> [(english_label, italian_label, value)]
_TABLE: dict[str, list[tuple[str, str, str]]] = {
    "profile": [
        ("I have a product idea", "Ho un'idea di prodotto", "product_idea"),
        ("I'm launching a new brand", "Sto lanciando un nuovo brand", "new_brand"),
        ("I already have a supplement brand", "Ho già un brand di integratori", "supplement_brand"),
        ("I'm looking for a manufacturing partner", "Cerco un partner produttivo", "manufacturing_partner"),
    ],
    "category": [
        ("Proteins", "Proteine", "proteins"),
        ("Performance & Training", "Performance e allenamento", "performance_and_training"),
        ("Health & Wellness", "Salute e benessere", "health_and_wellness"),
        ("Weight Management & Meal Solutions", "Controllo del peso e pasti", "weight_management_and_meal_solutions"),
        ("Drinks, Shots & Gels", "Bevande, shot e gel", "drinks_shots_gels"),
        ("Stick Packs & Single Servings", "Stick pack e monodose", "stick_packs_and_single_servings"),
        ("Skincare & Cosmetics", "Skincare e cosmetici", "skincare_and_cosmetics"),
        ("Not sure yet", "Non lo so ancora", "not_sure_yet"),
    ],
    "format": [
        ("Powders", "Polveri", "powders"),
        ("Capsules & Tablets", "Capsule e compresse", "capsules_and_tablets"),
        ("Softgels", "Softgel", "softgels"),
        ("Gummies", "Gummies", "gummies"),
        ("Stick packs", "Stick pack", "stick_packs"),
        ("RTDs", "Pronti da bere (RTD)", "rtds"),
        ("Shots", "Shot", "shots"),
        ("Not sure yet", "Non lo so ancora", "not_sure_yet"),
    ],
    "quote": [("Request a quote", "Richiedi un preventivo", "request_quote")],
    "confirm": [("Confirm", "Conferma", "confirm"), ("Edit", "Modifica", "edit")],
}

NOT_SURE = "not_sure_yet"
REQUEST_QUOTE = "request_quote"
CONFIRM = "confirm"
EDIT = "edit"


def buttons(group: str, lang: str) -> list[dict]:
    idx = 1 if lang == "it" else 0
    return [{"label": r[idx], "value": r[2]} for r in _TABLE[group]]


def values(group: str) -> list[str]:
    return [r[2] for r in _TABLE[group]]


def label_for(group: str, value: str, lang: str) -> str:
    idx = 1 if lang == "it" else 0
    return next((r[idx] for r in _TABLE[group] if r[2] == value), value)


def dynamic_buttons(values_: list[str]) -> list[dict]:
    return [{"label": v, "value": v} for v in values_]
