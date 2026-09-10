"""Provider LLM mock: risposte deterministiche per slug del prompt.

Serve a far girare l'intero stack senza chiavi. Le regole dinamiche qui sotto
esistono solo per far avanzare la state machine (validazione progetto,
estrazione contatto, citazione del contesto): non simulano qualità."""
from __future__ import annotations
import asyncio
import json
import re
from pathlib import Path
from typing import AsyncIterator
from services import usage as _usage

_DATA = Path(__file__).parent.parent / "data" / "mock_llm.json"
_SLUG_RE = re.compile(r"^# Prompt: (\S+)", re.MULTILINE)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_TITLE_RE = re.compile(r"^\[\d+\] (.+?) \(", re.MULTILINE)
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)
MODEL = "mock"
_USAGE = {"cost": 0.0001, "prompt_tokens": 100, "completion_tokens": 50}
_table: dict | None = None


def _load() -> dict:
    global _table
    if _table is None:
        _table = json.loads(_DATA.read_text(encoding="utf-8"))
    return _table


def slug_of(system: str) -> str | None:
    m = _SLUG_RE.search(system)
    return m.group(1) if m else None


def lang_of(system: str) -> str:
    """La lingua si legge SOLO dalla sezione `# Language` del prompt.

    Cercare "italian" in tutto il system prompt sembrava equivalente e non lo
    è: ogni prompt conversazionale ha una sezione `## Italian` fra gli esempi,
    quindi ogni conversazione in inglese riceveva risposte in italiano."""
    section = _section(system, "# Language")
    return "it" if "italian" in section.lower() else "en"


def _record() -> None:
    _usage.record(dict(_USAGE), model=MODEL)


def _section(system: str, heading: str) -> str:
    """Il testo di una sezione di primo livello del prompt, già riempita dal
    loader. Si ferma alla sezione successiva: prendere fino a fine file, come
    farebbe un taglio ingenuo, si porterebbe dietro tutto il resto."""
    i = system.find(heading)
    if i < 0:
        return ""
    rest = system[i + len(heading):]
    j = rest.find("\n# ")
    return (rest[:j] if j >= 0 else rest).strip()


def _input_section(system: str) -> str:
    return _section(system, "# Input")


def _lead_bullets(system: str) -> str:
    """`confirm_lead` riceve il lead come JSON dopo `# Input`: lo rendiamo a
    bullet, così la conferma nel mock mostra i dati veri della sessione."""
    match = _JSON_OBJ_RE.search(_input_section(system))
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            value = ", ".join(f"{k}: {v}" for k, v in value.items() if v)
        if isinstance(value, list):
            value = ", ".join(map(str, value))
        if value not in (None, "", [], {}, False):
            lines.append(f"• **{key}**: {value}")
    return "\n".join(lines) or "• (empty)"


def _text(slug: str | None, lang: str, user: str, system: str) -> str:
    entry = _load().get(slug or "", {})
    text = (entry.get("text") or {}).get(lang) or (entry.get("text") or {}).get("en")
    if text is None:
        return f"[mock:{slug}] {user[:80]}"
    if slug == "qa_answer":
        titles = ", ".join(_TITLE_RE.findall(user)) or "none"
        return text.replace("{titles}", titles)
    if slug == "confirm_lead":
        return text.replace("{lead_bullets}", _lead_bullets(system))
    return text


def _json(slug: str | None, user: str) -> dict:
    entry = _load().get(slug or "", {})
    base = dict(entry.get("json") or {})
    if slug == "validate_project":
        # Primo giro sempre insufficiente, secondo sempre sufficiente: serve a
        # far vedere il follow-up senza rendere il flusso infinito.
        turns = user.count("U:")
        enough = turns >= 2 or len(user) > 80
        return {"enough": enough, "question": "" if enough else base.get("question", "Tell me more.")}
    if slug == "extract_contact":
        email = _EMAIL_RE.search(user)
        parts = [p.strip() for p in re.split(r"[,\n;]+", user) if p.strip() and "@" not in p]
        return {
            "name": parts[0] if parts else None,
            "company": parts[1] if len(parts) > 1 else None,
            "email": email.group(0) if email else None,
            "valid": bool(email),
        }
    if not base:
        return {"mock": slug}
    return base


async def stream(system: str, user: str, history=None, model=None) -> AsyncIterator[str]:
    text = _text(slug_of(system), lang_of(system), user, system)
    words = text.split(" ")
    for i in range(0, len(words), 4):
        await asyncio.sleep(0)
        yield " ".join(words[i:i + 4]) + (" " if i + 4 < len(words) else "")
    _record()


async def complete(system: str, user: str, model=None) -> str:
    _record()
    return _text(slug_of(system), lang_of(system), user, system)


async def complete_structured(system: str, user: str, model=None) -> dict:
    _record()
    return _json(slug_of(system), user)


async def web_complete(system: str, user: str, model: str = "") -> str:
    return await complete(system, user)
