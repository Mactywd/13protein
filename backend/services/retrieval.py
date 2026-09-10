"""Facciata del retrieval: keyword (default) o qdrant, scelto da settings."""
from __future__ import annotations
from pathlib import Path
from config import settings
from services import retrieval_keyword

# Slug del form del sito (lib/labels.py) -> `doc` del knowledgebase.jsonl.
CATEGORY_DOC = {
    "proteins": "protein-powders",
    "performance_and_training": "performance-training",
    "health_and_wellness": "health-wellness",
    "weight_management_and_meal_solutions": "weight-management",
    "drinks_shots_gels": "drinks-shots-gels",
    "stick_packs_and_single_servings": "stick-packs",
    "skincare_and_cosmetics": "skincare-cosmetics",
}
format_context = retrieval_keyword.format_context
_index: retrieval_keyword.Index | None = None


def _kb_path() -> Path:
    p = Path(settings.kb_path)
    return p if p.is_absolute() else (Path(__file__).parent.parent / p).resolve()


def index() -> retrieval_keyword.Index:
    global _index
    if _index is None:
        _index = retrieval_keyword.Index.from_jsonl(_kb_path())
    return _index


async def search(query: str, limit: int = 3, exclude_docs: list[str] | None = None) -> list[dict]:
    if settings.retrieval_provider == "qdrant":
        from services import qdrant
        return await qdrant.search(query, limit=limit, exclude_docs=exclude_docs)
    return index().search(query, limit=limit, exclude_docs=exclude_docs)


def doc_card(doc: str) -> dict | None:
    return index().doc_card(doc)
