"""Retrieval a parole chiave in memoria su knowledgebase.jsonl. Nessuna
dipendenza, nessun embedding: basta per verificare il cablaggio della chat
(spec D3). Punteggio = somma dei termini della query presenti in
page_title (x3), section (x2), text (x1). Le righe `status: draft` sono
escluse: non sono contenuto live.

I termini sono confrontati per **radice troncata** a 5 caratteri: senza questo
"are you certified" non trova la pagina Quality, che scrive "certification".
È una stemmatizzazione grossolana e può accorpare parole diverse: accettabile
per un indice mock, da sostituire con gli embedding (provider qdrant)."""
from __future__ import annotations
import json
import re
from pathlib import Path

_TOKEN_RE = re.compile(r"[a-zà-ÿ0-9]+")
_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "you",
         "your", "we", "our", "do", "does", "with", "at", "by", "it", "be", "can", "i",
         "il", "la", "lo", "le", "gli", "di", "da", "che", "e", "un", "una", "per", "con", "siete"}


STEM_LEN = 5


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOP and len(t) > 1]


def stems(text: str) -> set[str]:
    return {t[:STEM_LEN] for t in tokens(text)}


def format_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[{i}] {c.get('page_title', '')} ({c.get('url', '')})\n{c.get('text', '')}")
    return "\n\n".join(parts)


class Index:
    def __init__(self, rows: list[dict]):
        self.rows = [r for r in rows if r.get("status", "publish") != "draft"]
        self._prepared = [
            (stems(r.get("page_title")), stems(r.get("section")), stems(r.get("text")))
            for r in self.rows
        ]

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "Index":
        rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
        return cls(rows)

    def search(self, query: str, limit: int = 3, exclude_docs: list[str] | None = None) -> list[dict]:
        q = stems(query)
        if not q:
            return []
        excluded = set(exclude_docs or [])
        scored = []
        for row, (t, s, x) in zip(self.rows, self._prepared):
            if row.get("doc") in excluded:
                continue
            score = 3 * len(q & t) + 2 * len(q & s) + len(q & x)
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda p: (-p[0], p[1].get("id", "")))
        return [{**row, "score": score} for score, row in scored[:limit]]

    def doc_card(self, doc: str) -> dict | None:
        for row in self.rows:
            if row.get("doc") == doc and (row.get("text") or "").strip():
                first = next((l for l in row["text"].splitlines()
                              if l.strip() and not l.startswith("![")), "")
                return {"title": row.get("page_title", doc),
                        "description": first.strip("#* ").strip()[:200],
                        "url": row.get("url", "")}
        return None
