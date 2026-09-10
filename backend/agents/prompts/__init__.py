"""Carica agents/prompts/<slug>.txt e riempie i {placeholder} con str.replace
(non str.format: graffe spurie nel testo non devono rompere nulla).

La prima riga del prompt restituito è sempre `# Prompt: <slug>`: innocua per un
LLM vero, indispensabile per il provider mock (services/llm_mock.py), che
sceglie la risposta in base allo slug."""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent

# Prepeso a ogni prompt. Corto: ogni chiamata paga questi token.
_HEADER = (
    "# Shared Guidelines (apply to every message)\n"
    "- **Brand**: you represent \"13 Protein\" (13 e Protein Import AB, Sweden), a European "
    "B2B contract manufacturer of food supplements. The brand name stays as is in every language.\n"
    "- **Audience**: companies looking for a manufacturer (brand owners, startups, distributors), "
    "not consumers. Assume business literacy, explain manufacturing terms briefly.\n"
    "- **Tone**: professional, concrete, helpful; never pushy, never hype.\n"
    "- **Punctuation**: NEVER use em dashes. Use commas, colons, parentheses, or separate sentences.\n"
    "- **Never invent**: prices, minimum order quantities, lead times, certifications, or figures. "
    "If asked, say a quote is needed and offer to collect the request.\n"
    "- **Placeholder**: this is a MOCK prompt set. Answer with plausible example data; the prompts "
    "will be rewritten once the agent's tasks are defined.\n\n"
)


@lru_cache(maxsize=None)
def _raw(slug: str) -> str:
    return (_DIR / f"{slug}.txt").read_text(encoding="utf-8")


def load(slug: str, **placeholders: object) -> str:
    text = f"# Prompt: {slug}\n" + _HEADER + _raw(slug)
    for key, value in placeholders.items():
        text = text.replace("{" + key + "}", str(value))
    return text
