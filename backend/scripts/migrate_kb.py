"""Popola la collection Qdrant con i chunk di knowledgebase.jsonl.

Legge il bundle indicato da `settings.kb_path`, calcola un embedding per chunk
via OpenRouter (stesso modello usato dalla ricerca a runtime), (ri)crea la
collection e fa upsert di ogni chunk con il chunk stesso come payload.

Da eseguire dalla cartella backend/, così config/.env viene caricato:

    cd backend && python -m scripts.migrate_kb              # upsert incrementale
    cd backend && python -m scripts.migrate_kb --recreate   # drop e ricostruzione

Richiede una chiave OpenRouter e un Qdrant raggiungibile: non fa parte della
verifica mock."""
from __future__ import annotations
import argparse
import asyncio

import httpx

from config import settings
from services.qdrant import EMBED_DIM, embed, collection
from services import retrieval


def _embed_text(chunk: dict) -> str:
    """Testo dato al modello di embedding: più ricco di qualsiasi campo singolo."""
    parts = [chunk.get("page_title"), chunk.get("section"), chunk.get("text")]
    return ". ".join(p for p in parts if p)


async def _recreate_collection(client: httpx.AsyncClient) -> None:
    await client.delete(f"{settings.qdrant_url}/collections/{collection()}")
    resp = await client.put(
        f"{settings.qdrant_url}/collections/{collection()}",
        json={"vectors": {"size": EMBED_DIM, "distance": "Cosine"}},
    )
    resp.raise_for_status()


async def main(recreate: bool) -> None:
    chunks = retrieval.index().rows
    print(f"Caricati {len(chunks)} chunk live da {settings.kb_path}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        if recreate:
            print(f"Ricreo la collection '{collection()}' (dim={EMBED_DIM})...")
            await _recreate_collection(client)

        points = []
        for i, chunk in enumerate(chunks):
            vector = await embed(_embed_text(chunk))
            points.append({"id": i, "vector": vector, "payload": chunk})
            print(f"  [{i + 1}/{len(chunks)}] {chunk.get('id')}")

        resp = await client.put(
            f"{settings.qdrant_url}/collections/{collection()}/points?wait=true",
            json={"points": points},
        )
        resp.raise_for_status()
    print("Fatto.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.recreate))
