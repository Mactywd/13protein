"""Strumento di sviluppo: anteprima dei prompt conversazionali eseguendo i veri
wrapper degli agent con fixture realistiche.

Uso (da backend/, con .env caricato):
    set -a && . ./.env && set +a
    python -m scripts.preview_prompts all           # tutti i prompt, inglese
    python -m scripts.preview_prompts qa_answer     # un prompt solo
    python -m scripts.preview_prompts all it        # controllo in italiano

Non è un test: l'output di un LLM non è deterministico. Serve a guardare a
occhio impatto e scansionabilità secondo agents/prompts/LINEEGUIDA.md §2. Con
LLM_PROVIDER=mock stampa le risposte segnaposto, senza spendere nulla."""
from __future__ import annotations
import asyncio
import sys
from typing import AsyncIterator, Callable

from agents import lead_agents, qa_agents, contact_agents

# --- Fixture --------------------------------------------------------------

PROFILE = "I have a product idea"
CATEGORY = "Proteins"
FORMAT = "Powders"

PROJECT_RAW = (
    "U: A whey protein for gyms\n"
    "A: Which market and customer are you targeting?\n"
    "U: Target market Italy, 2 kg tubs, chocolate and vanilla, launch in spring"
)
PROJECT_DESCRIPTION = (
    "A protein powder for the gym channel on the Italian market, in 2 kg tubs, "
    "chocolate and vanilla, with a spring launch."
)

CHUNKS = [
    {"page_title": "Quality", "url": "https://13protein.com/quality",
     "text": "Our production sites operate to internationally recognized standards."},
    {"page_title": "Private Label", "url": "https://13protein.com/private-label",
     "text": "Custom formulation developed with your team, from concept to finished product."},
]

LEAD = {
    "profile": "product_idea", "category": "proteins", "format": "powders",
    "projectDescription": PROJECT_DESCRIPTION,
    "questionsAsked": ["Are you certified?"], "topicsCited": ["quality"],
    "quoteRequested": True,
    "contact": {"name": "Mario Rossi", "company": "Rossi Nutrition",
                "email": "mario@example.com"},
    "language": "en",
}

CONTACT_MESSAGE = "Mario Rossi, Rossi Nutrition, mario@example.com"

# slug -> callable che restituisce un async iterator di token, oppure una coroutine
REGISTRY: dict[str, Callable[[str], object]] = {
    "introduction": lambda lang: lead_agents.introduction(lang),
    "ask_category": lambda lang: lead_agents.ask_category(PROFILE, lang),
    "ask_format": lambda lang: lead_agents.ask_format(CATEGORY, lang),
    "ask_project": lambda lang: lead_agents.ask_project(CATEGORY, FORMAT, lang),
    "validate_project": lambda lang: lead_agents.validate_project(PROJECT_RAW, lang),
    "summarize_project": lambda lang: lead_agents.summarize_project(PROJECT_RAW, lang),
    "qa_intro": lambda lang: qa_agents.qa_intro(PROJECT_DESCRIPTION, lang),
    "qa_answer": lambda lang: qa_agents.qa_answer("Are you certified?", CHUNKS, lang),
    "ask_contact": lambda lang: contact_agents.ask_contact(lang),
    "extract_contact": lambda lang: contact_agents.extract_contact(CONTACT_MESSAGE, lang),
    "confirm_lead": lambda lang: lead_agents.confirm_lead(LEAD, lang),
}


async def _render(slug: str, lang: str) -> None:
    print(f"\n{'=' * 70}\n{slug}  [{lang}]\n{'=' * 70}")
    result = REGISTRY[slug](lang)
    if isinstance(result, AsyncIterator) or hasattr(result, "__aiter__"):
        async for token in result:
            print(token, end="", flush=True)
        print()
    else:
        print(await result)


async def main(slugs: list[str], lang: str) -> None:
    for slug in slugs:
        await _render(slug, lang)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    language = sys.argv[2] if len(sys.argv) > 2 else "en"
    selected = list(REGISTRY) if which == "all" else [which]
    unknown = [s for s in selected if s not in REGISTRY]
    if unknown:
        raise SystemExit(f"slug sconosciuti: {unknown}. Disponibili: {sorted(REGISTRY)}")
    asyncio.run(main(selected, language))
