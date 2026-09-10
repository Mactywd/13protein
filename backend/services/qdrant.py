# backend/services/qdrant.py
"""Adapter Qdrant per il retrieval sul knowledgebase.

Non è verificato in questa sessione: il default resta `RETRIEVAL_PROVIDER=keyword`
e questo modulo esiste perché il passaggio a embedding non richieda di riscrivere
i chiamanti. Su qualunque errore ricade sull'indice a parole chiave, che è
lessicale e non semantico: il log è rumoroso apposta."""
from __future__ import annotations
import logging
import httpx
from config import settings
from services.openrouter import _headers as openrouter_headers

log = logging.getLogger(__name__)

EMBED_MODEL = "openai/text-embedding-3-small"
EMBED_DIM = 1536


def collection() -> str:
    return settings.qdrant_collection


async def embed(text: str) -> list[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers=openrouter_headers(),
            json={"model": EMBED_MODEL, "input": text},
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]


async def search(
    query: str,
    limit: int = 3,
    exclude_docs: list[str] | None = None,
) -> list[dict]:
    """Cerca su Qdrant; sull'errore ricade sull'indice a parole chiave."""
    try:
        vector = await embed(query)
        payload: dict = {"vector": vector, "limit": limit, "with_payload": True}
        if exclude_docs:
            payload["filter"] = {
                "must_not": [{"key": "doc", "match": {"any": exclude_docs}}]
            }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.qdrant_url}/collections/{collection()}/points/search",
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            return [r["payload"] for r in response.json()["result"]]
    except Exception:
        log.exception(
            "Ricerca Qdrant fallita (query=%r): ricado sull'indice a parole chiave, "
            "i risultati non sono ordinati semanticamente", query,
        )
        from services import retrieval
        return retrieval.index().search(query, limit=limit, exclude_docs=exclude_docs)
