# Harness mock dell'agente 13protein — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Portare in questa repo la parte generica dell'Alchimista (`/home/user/alchimista_ndc`, commit `12ffcac`, **sola lettura**) e costruire sopra un agente 13protein interamente mock: flusso di qualificazione lead + domande libere sul knowledgebase, prompt segnaposto, provider LLM mock e retrieval a parole chiave, così che l'intero stack giri e si verifichi end-to-end senza credenziali.

**Architecture:** Tre livelli su singola origine, invariati: React/Vite (`src/`) → Express (`server/`, proxy SSE, admin, analytics JSONL) → FastAPI (`backend/`, state machine per step, agenti, Postgres). Due nuovi seam nel backend: `services/llm.py` (mock | openrouter) e `services/retrieval.py` (keyword | qdrant). L'oggetto finale della chat è `lead_info`.

**Tech Stack:** Python 3.11+ (FastAPI, pydantic v2, asyncpg, httpx, pytest `asyncio_mode=auto`), Node 22 (Express, vitest), React 19 + Vite 7 + react-router 7 + recharts, Postgres 16.

**Spec:** `docs/superpowers/specs/2026-09-09-mock-harness-design.md`

## Global Constraints

- **Mai scrivere in `/home/user/alchimista_ndc`.** Si copia con `cp` dalla sorgente, si modifica solo la copia. Prima di ogni copia leggere il file sorgente: i percorsi indicati sotto sono relativi a `/home/user/alchimista_ndc` (sorgente, `SRC`) e a `/home/user/13protein` (destinazione, `DST`).
- Ogni task finisce con test verdi e un commit sul branch `claude/13protein-ai-agent-setup-kkti3l`. Messaggi di commit in italiano, senza identificatori di modello nel corpo.
- Convenzioni di test dell'Alchimista: backend con `monkeypatch` su `main.db.transaction`, `main.session.load/save`, e sugli agent (`AsyncMock`, async generator finti); mai un Postgres reale nei test. Node: solo `server/lib/*.test.js` e `server/routes/*.test.js` puri; nessun test di componenti React.
- Ogni prompt `.txt` inizia con la riga `# Prompt: <slug>` **scritta dal loader**, non nel file. I file seguono `backend/agents/prompts/LINEEGUIDA.md`; i placeholder restano byte-identici e vengono verificati con `python -m scripts.check_prompt_placeholders <slug> a,b,c`.
- Valori canonici dei bottoni = slug inglesi del form del sito (`knowledgebase/site/forms.md`); le etichette IT/EN stanno solo in `lib/labels.py` e `src/i18n/translations.js`.
- Lingua di default `en`. `_LANG_NAME = {"en": "english", "it": "italian"}`.
- Il mock deve permettere di completare una conversazione con **esattamente** questa sequenza di messaggi (usata da `scripts/e2e-mock.sh` e dal test Playwright): `""` (launch) → `product_idea` → `proteins` → `powders` → `A whey protein for gyms` (risposta `enough:false`) → `Target market Italy, 2 kg tubs, chocolate and vanilla, launch in spring` (`enough:true`) → `Are you certified?` (risposta KB) → `request_quote` → `Mario Rossi, Rossi Nutrition, mario@example.com` → `confirm` → `done` con `step=completed`.
- Nessuna dipendenza Python oltre a quelle di `pyproject.toml` dell'Alchimista; nessuna dipendenza Node nuova.

---

### Task 0: Bootstrap della repo (config, tooling, ignore)

**Files:**
- Create: `package.json`, `package-lock.json` (copiato), `vite.config.js`, `eslint.config.js`, `index.html`, `admin.html`, `.gitignore`, `.dockerignore`, `.env.example`
- Create: `backend/pyproject.toml`, `backend/.env.example`, `backend/.gitignore`, `backend/.dockerignore`, `backend/conftest.py`
- Modify: `CLAUDE.md` (solo la sezione Struttura: aggiungere le nuove cartelle; la riscrittura completa è nel Task 16)

- [x] **Step 1: Copiare i file di tooling dalla sorgente**

```bash
SRC=/home/user/alchimista_ndc; DST=/home/user/13protein
cp $SRC/package.json $SRC/package-lock.json $SRC/vite.config.js $SRC/eslint.config.js $SRC/index.html $SRC/admin.html $SRC/.dockerignore $DST/
cp $SRC/backend/pyproject.toml $SRC/backend/.dockerignore $SRC/backend/conftest.py $DST/backend/
```

- [x] **Step 2: Rinominare e adattare**

- `package.json`: `"name": "agent13"`; scripts invariati (`dev`, `build`, `start`, `lint`, `test`, `preview`).
- `backend/pyproject.toml`: `name = "agent13-backend"`, `requires-python = ">=3.11"`.
- `index.html` / `admin.html`: `<title>13 Protein · Assistant</title>` / `<title>13 Protein · Admin</title>`; togliere i `<link>` ai Google Fonts dell'Alchimista (Cormorant/Italianno) e il favicon `ndc_favicon.png`; tenere la meta viewport **con** `interactive-widget=resizes-content` (gotcha mobile documentata in CLAUDE.md sorgente).
- `.gitignore` (nuovo, da scrivere): `node_modules/`, `dist/`, `.env`, `.env.*`, `!.env.example`, `!.env.*.example`, `data/`, `.cache/`, `*.sql` (il dump da 1 GB), `__pycache__/`, `.pytest_cache/`, `backend/.env`.
- `backend/.gitignore`: `.env`, `__pycache__/`, `.pytest_cache/`, `*.egg-info/`.
- `.env.example`:

```
BACKEND_URL=http://localhost:8000
PORT=3000
ANALYTICS_LOG=./data/analytics/events.jsonl
ADMIN_USERS_FILE=./data/admin/users.json
POSTGRES_USER=agent13
POSTGRES_PASSWORD=changeme
RETENTION_ENABLED=true
RETENTION_DRY_RUN=true
RETENTION_ANALYTICS_DAYS=425
RETENTION_CONTENT_DAYS=730
DOMAIN=agent.example.com
```

- `backend/.env.example`:

```
LLM_PROVIDER=mock            # mock | openrouter
RETRIEVAL_PROVIDER=keyword   # keyword | qdrant
KB_PATH=../knowledgebase/knowledgebase.jsonl
OPENROUTER_API_KEY=
OPENROUTER_API_KEY_FALLBACK=
DATABASE_URL=postgresql+asyncpg://agent13:changeme@localhost/agent13
QDRANT_URL=http://localhost:6333
ENV=development
RETENTION_ENABLED=true
RETENTION_DRY_RUN=true
RETENTION_CONTENT_DAYS=730
RETENTION_SESSION_DAYS=730
```

- [x] **Step 3: Installare le dipendenze e verificare**

Run: `cd $DST && npm ci && cd backend && pip install -e ".[dev]"`
Expected: entrambe senza errori; `python -c "import fastapi, asyncpg"` ok.

- [x] **Step 4: Commit**

```bash
git add package.json package-lock.json vite.config.js eslint.config.js index.html admin.html .gitignore .dockerignore .env.example backend/pyproject.toml backend/.env.example backend/.gitignore backend/.dockerignore backend/conftest.py
git commit -m "Bootstrap dell'harness: tooling Node e Python copiati dall'Alchimista"
```

---

### Task 1: Servizi generici del backend (db, usage, openrouter, stream, session, transcripts, chats, config)

**Files:**
- Create: `backend/services/__init__.py`, `backend/services/db.py`, `backend/services/usage.py`, `backend/services/openrouter.py`, `backend/stream.py`, `backend/session.py`, `backend/transcripts.py`, `backend/chats.py`, `backend/config.py`
- Test: `backend/tests/test_usage.py`, `test_openrouter_usage.py`, `test_openrouter_complete.py`, `test_stream.py`, `test_session.py`, `test_transcripts.py`, `test_chats.py`, `test_config.py` (copiati e adattati)

**Interfaces:**
- Produces: `config.settings` con i nuovi campi `llm_provider: str = "mock"`, `retrieval_provider: str = "keyword"`, `kb_path: str = "../knowledgebase/knowledgebase.jsonl"`, `qdrant_collection: str = "kb13"`; `database_url` default `postgresql+asyncpg://agent13:changeme@localhost/agent13`.
- Produces: `session.save(session_id, state, conn, is_testing=False)` che scrive le colonne `profile`, `category`, `format`, `quote_requested` (Task 2 definisce `SessionState`).

- [x] **Step 1: Copiare**

```bash
cp $SRC/backend/services/{__init__,db,usage,openrouter}.py $DST/backend/services/
cp $SRC/backend/{stream,session,transcripts,chats,config}.py $DST/backend/
cp $SRC/backend/tests/{test_usage,test_openrouter_usage,test_openrouter_complete,test_stream,test_session,test_transcripts,test_chats,test_config}.py $DST/backend/tests/
```

- [x] **Step 2: Adattare `config.py`** (riscrivere in pieno)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Provider: il mock non ha bisogno di chiavi e permette di far girare
    # l'intero stack in locale e nei test (spec D2/D3).
    llm_provider: str = "mock"          # mock | openrouter
    retrieval_provider: str = "keyword"  # keyword | qdrant
    kb_path: str = "../knowledgebase/knowledgebase.jsonl"

    database_url: str = "postgresql+asyncpg://agent13:changeme@localhost/agent13"
    openrouter_api_key: str = ""
    openrouter_api_key_fallback: str = ""
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "kb13"
    web_search_model: str = "perplexity/sonar"
    env: str = "development"

    # Retention (GDPR art. 5.1.e). Termini segnaposto: da decidere con il
    # titolare prima di pubblicare un'informativa. Dry run di default.
    retention_enabled: bool = True
    retention_dry_run: bool = True
    retention_content_days: int = 730
    retention_session_days: int = 730


settings = Settings()
```

- [x] **Step 3: Adattare `openrouter.py`**

- `"HTTP-Referer": "https://13protein.com"`.
- `DEFAULT_MODEL = "google/gemma-4-26b-a4b-it:nitro"` resta (è un default, si cambia da chiamante).
- Nessun altro cambio: il modulo è generico.

- [x] **Step 4: Adattare `stream.py`**

Sostituire `GeneralInfoEvent` → `LeadInfoEvent` e il nome evento `"general_info"` → `"lead_info"` (l'import da `models` arriva nel Task 2; fino ad allora il test di `stream` fallisce, è atteso).

- [x] **Step 5: Adattare `session.py`**

In `save()`, sostituire le colonne di reporting:

```python
    await conn.execute(
        """
        INSERT INTO sessions (id, state, updated_at, is_testing,
                              profile, category, format, quote_requested)
        VALUES ($1, $2::jsonb, now(), $3, $4, $5, $6, $7)
        ON CONFLICT (id) DO UPDATE
            SET state = $2::jsonb, updated_at = now(), abandoned_at = NULL,
                is_testing = sessions.is_testing OR EXCLUDED.is_testing,
                profile = EXCLUDED.profile,
                category = EXCLUDED.category,
                format = EXCLUDED.format,
                quote_requested = EXCLUDED.quote_requested
        """,
        session_id, state.model_dump_json(), is_testing,
        state.profile, state.category, state.format, state.quote_requested,
    )
```

- [x] **Step 6: Adattare `chats.py`**

- In `chat_summary`: la condizione `inizializzata` diventa `abandoned and row.get("profile") is None`; i campi `path`/`fragrance_subpath` diventano `profile`/`category`/`format`.
- In `sweep_abandoned`: `RETURNING id, profile` (il chiamante salta l'evaluation se `profile is None`).
- In `list_chats` e `get_chat`: selezionare `s.profile, s.category, s.format, s.quote_requested` al posto di `s.path, s.fragrance_subpath`; nella `evaluation` di `get_chat` sostituire `essence_modified` con `quote_requested`.
- `messages_from_row` invariato (carte e bottoni hanno la stessa forma).

- [x] **Step 7: Adattare `transcripts.py`**: invariato.

- [x] **Step 8: Adattare i test copiati**

- `test_session.py`: le asserzioni su `path`/`fragrance_subpath`/`delegate_used` diventano `profile`/`category`/`format`/`quote_requested`.
- `test_chats.py`: righe di fixture con `profile` invece di `path`; `inizializzata` quando `profile is None`.
- `test_config.py`: aggiungere `assert settings.llm_provider == "mock"` e `settings.retrieval_provider == "keyword"`.
- `test_stream.py`: `LeadInfoEvent` / `"event: lead_info"`.

- [x] **Step 9: Eseguire i test**

Run: `cd $DST/backend && python -m pytest tests/test_usage.py tests/test_openrouter_usage.py tests/test_openrouter_complete.py tests/test_config.py -q`
Expected: verdi. (`test_stream`, `test_session`, `test_chats`, `test_transcripts` dipendono da `models.py`: verdi dal Task 2.)

- [x] **Step 10: Commit**

```bash
git add backend/services backend/stream.py backend/session.py backend/transcripts.py backend/chats.py backend/config.py backend/tests
git commit -m "Backend: servizi generici (db, usage, openrouter, stream, sessione, transcript, chat)"
```

---

### Task 2: `models.py` — Step, SessionState, eventi, `lead_info`

**Files:**
- Create: `backend/models.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Produces: `Step`, `SessionState`, `to_lead_info()`, eventi `TextEvent | ButtonsEvent | CarouselEvent | ErrorEvent | LeadInfoEvent | DoneEvent | MessageBreakEvent`, `MESSAGE_BREAK`.

- [x] **Step 1: Scrivere il test**

```python
# backend/tests/test_models.py
from models import SessionState, Step


def test_defaults():
    s = SessionState()
    assert s.current_step == Step.INTRO
    assert s.default_language == "en"
    assert s.profile is None and s.quote_requested is False


def test_to_lead_info_shape():
    s = SessionState(profile="product_idea", category="proteins", format="powders",
                     project_description="Whey for gyms", questions_asked=["Certified?"],
                     topics_cited=["quality"], quote_requested=True,
                     contact={"name": "Mario", "company": "Rossi", "email": "m@example.com"})
    info = s.to_lead_info()
    assert info["profile"] == "product_idea"
    assert info["projectDescription"] == "Whey for gyms"
    assert info["topicsCited"] == ["quality"]
    assert info["contact"]["email"] == "m@example.com"
    assert info["language"] == "en"


def test_to_lead_info_placeholders_when_empty():
    info = SessionState().to_lead_info()
    assert info["profile"] is None
    assert info["contact"] == {"name": None, "company": None, "email": None}
    assert info["questionsAsked"] == []


def test_state_roundtrip_json():
    s = SessionState(profile="new_brand", topics_cited=["home"])
    assert SessionState.model_validate_json(s.model_dump_json()) == s
```

- [x] **Step 2: Eseguire il test** — Run: `python -m pytest tests/test_models.py -q` — Expected: FAIL (`ModuleNotFoundError: models`).

- [x] **Step 3: Scrivere `backend/models.py`**

```python
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel, Field


class Step(str, Enum):
    INTRO = "intro"
    PROFILE_SELECT = "profile_select"
    CATEGORY_SELECT = "category_select"
    FORMAT_SELECT = "format_select"
    PROJECT_INPUT = "project_input"
    QA = "qa"
    CONTACT_INPUT = "contact_input"
    CONTACT_CONFIRM = "contact_confirm"
    COMPLETED = "completed"


class SessionState(BaseModel):
    current_step: Step = Step.INTRO
    default_language: str = "en"

    # qualificazione (slug del form del sito, vedi lib/labels.py)
    profile: str | None = None
    category: str | None = None
    format: str | None = None

    # progetto
    project_raw: str = ""                 # transcript U:/A: dello step progetto
    project_description: str | None = None
    followup_count: int = 0

    # domande libere
    questions_asked: list[str] = Field(default_factory=list)
    topics_cited: list[str] = Field(default_factory=list)   # doc del KB citati
    quote_requested: bool = False

    # contatto e output
    contact: dict | None = None           # {name, company, email}
    lead_info: dict | None = None

    # carry-forward dei costi di un turno senza bolle visibili (main.py::chat)
    pending_cost: float = 0.0
    pending_prompt_tokens: int = 0
    pending_completion_tokens: int = 0
    pending_models: list[str] = Field(default_factory=list)

    def to_lead_info(self) -> dict:
        contact = self.contact or {}
        return {
            "profile": self.profile,
            "category": self.category,
            "format": self.format,
            "projectDescription": self.project_description,
            "questionsAsked": list(self.questions_asked),
            "topicsCited": list(self.topics_cited),
            "quoteRequested": self.quote_requested,
            "contact": {
                "name": contact.get("name"),
                "company": contact.get("company"),
                "email": contact.get("email"),
            },
            "language": self.default_language,
        }


@dataclass
class TextEvent:
    token: str


@dataclass
class ButtonsEvent:
    buttons: list[dict]  # [{"label": str, "value": str}]


@dataclass
class CarouselEvent:
    cards: list[dict]  # [{"title", "image", "description", "value"}]


@dataclass
class ErrorEvent:
    message: str


@dataclass
class LeadInfoEvent:
    info: dict


@dataclass
class DoneEvent:
    step: str
    input_enabled: bool = True


# Separatore inserito nel transcript a un MessageBreakEvent (chats.messages_from_row
# lo usa per ri-espandere un turno in più bolle, come nel client).
MESSAGE_BREAK = "\x1e"


@dataclass
class MessageBreakEvent:
    """Chiude la bolla corrente senza chiudere il turno."""


Event = (TextEvent | ButtonsEvent | CarouselEvent | ErrorEvent | LeadInfoEvent
         | DoneEvent | MessageBreakEvent)
```

- [x] **Step 4: Eseguire i test** — Run: `python -m pytest tests/test_models.py tests/test_stream.py tests/test_session.py tests/test_chats.py tests/test_transcripts.py -q` — Expected: verdi.

- [x] **Step 5: Commit** — `git add backend/models.py backend/tests/test_models.py && git commit -m "Backend: modelli dello stato lead e contratto eventi SSE"`

---

### Task 3: Prompt loader, linee guida e 13 prompt segnaposto

**Files:**
- Create: `backend/agents/__init__.py`, `backend/agents/prompts/__init__.py`, `backend/agents/prompts/LINEEGUIDA.md`, 13 file `backend/agents/prompts/<slug>.txt`
- Create: `backend/scripts/__init__.py`, `backend/scripts/check_prompt_placeholders.py` (copiato)
- Test: `backend/tests/test_prompts_loader.py`

**Interfaces:**
- Produces: `prompts.load(slug, **placeholders) -> str`, il cui risultato inizia con `# Prompt: <slug>\n` seguito da `_HEADER` e dal corpo.

- [x] **Step 1: Copiare linee guida e script**

```bash
mkdir -p $DST/backend/agents/prompts $DST/backend/scripts
cp $SRC/backend/agents/__init__.py $DST/backend/agents/
cp $SRC/backend/agents/prompts/LINEEGUIDA.md $DST/backend/agents/prompts/
cp $SRC/backend/scripts/__init__.py $SRC/backend/scripts/check_prompt_placeholders.py $DST/backend/scripts/
cp $SRC/backend/tests/test_prompts_loader.py $DST/backend/tests/
```

In `LINEEGUIDA.md` §4: brand "13 Protein" al posto di "Note del Chianti", pubblico "aziende che cercano un produttore", tono "professionale e concreto, dare del lei in italiano"; rimuovere il riferimento alle essenze.

- [x] **Step 2: Scrivere `backend/agents/prompts/__init__.py`**

```python
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
```

- [x] **Step 3: Adattare `test_prompts_loader.py`**: aggiungere

```python
def test_load_starts_with_slug_line():
    assert prompts.load("introduction", default_language="english").startswith("# Prompt: introduction\n")

def test_header_mentions_brand_and_no_invention_rule():
    text = prompts.load("introduction", default_language="english")
    assert "13 Protein" in text and "Never invent" in text
```

e togliere le asserzioni sui prompt dell'Alchimista.

- [x] **Step 4: Scrivere i 13 prompt segnaposto**

Tutti con la stessa ossatura. Template per i **conversazionali** (esempio `introduction.txt`):

```
# Role
You are a placeholder sales assistant for 13 Protein, a European B2B contract manufacturer of food supplements. Answer with plausible example data: this prompt will be rewritten.

# Language
Write the ENTIRE message in {default_language}.

# Task
Open the conversation: greet, say in one sentence that you help companies define a supplement project and route it to the right team, then ask which option best describes the visitor. Do NOT list the options (they are shown as buttons).

**Format:** 2 short paragraphs, **bold** on the key words of the closing question.

**Output:** only the message, no commentary, no code fences.

# Examples

## English
Welcome to 13 Protein. I help brands and startups shape a supplement project and get it to the right people in our team.

To start: **which option best describes you?**

## Italian
Benvenuto in 13 Protein. La aiuto a definire un progetto di integratori e a indirizzarlo al team giusto.

Per iniziare: **quale opzione la descrive meglio?**
```

Placeholder attesi per file (verificare ognuno con `check_prompt_placeholders`):

| slug | placeholder | note sul task |
|---|---|---|
| `introduction` | `default_language` | sopra |
| `ask_category` | `default_language`, `profile` | ringrazia per il profilo e chiede cosa vuole creare (bottoni) |
| `ask_format` | `default_language`, `category` | una riga sulla categoria (esempio) e chiede il formato (bottoni) |
| `ask_project` | `default_language`, `category`, `format` | chiede di descrivere il progetto: target, ingredienti, formato, quantità; elenco a bullet di cosa scrivere |
| `validate_project` | `default_language`, `project_raw` | JSON `{"enough": bool, "question": str}`; `enough` se ci sono almeno target e un'idea di prodotto |
| `summarize_project` | `default_language`, `project_raw` | 2-3 frasi in terza persona, niente dati personali |
| `qa_intro` | `default_language`, `project_description` | recap del progetto + invito a fare domande o chiedere un preventivo (bottone) |
| `qa_answer` | `default_language` | risponde SOLO con il contesto ricevuto nel messaggio utente (`Question:` + `Context:` con `[n] Title (url)`), cita la pagina, se il contesto non basta lo dice e rimanda al preventivo |
| `ask_contact` | `default_language` | chiede nome, azienda, email in un messaggio |
| `extract_contact` | `default_language` | JSON `{"name","company","email","valid"}`; `valid:false` se manca l'email |
| `confirm_lead` | `default_language`, `lead_json` | recap a bullet dei campi del lead + "Confirm or Edit" |
| `evaluation` | `transcript` | JSON `{"outcome","path_summary","problem","quote_requested"}`; minimizzazione: niente nomi/aziende/email nel riassunto |
| `report_summary` | `stats_json` | JSON `{"friction_text","recommendations"}` in italiano, solo giudizi, mai numeri nuovi |

- [x] **Step 5: Verificare i placeholder**

Run (dal `backend/`): per ogni slug, es. `python -m scripts.check_prompt_placeholders ask_format default_language,category`
Expected: exit 0 per tutti e 13.

- [x] **Step 6: Test** — Run: `python -m pytest tests/test_prompts_loader.py -q` — Expected: verde.

- [x] **Step 7: Commit** — `git add backend/agents backend/scripts backend/tests/test_prompts_loader.py && git commit -m "Prompt loader con riga slug e 13 prompt segnaposto"`

---

### Task 4: Provider LLM mock e dispatcher `services/llm.py`

**Files:**
- Create: `backend/services/llm.py`, `backend/services/llm_mock.py`, `backend/data/mock_llm.json`
- Test: `backend/tests/test_llm_mock.py`, `backend/tests/test_llm_dispatch.py`

**Interfaces:**
- Produces: `llm.stream(system, user, history=None, model=None) -> AsyncIterator[str]`, `llm.complete(system, user, model=None) -> str`, `llm.complete_structured(system, user, model=None) -> dict`, `llm.web_complete(system, user, model="") -> str`. Tutti gli agent importano **solo** `services.llm`.
- Produces: `llm_mock.slug_of(system) -> str | None`, `llm_mock.lang_of(system) -> "en" | "it"`.

- [x] **Step 1: Scrivere i test**

```python
# backend/tests/test_llm_mock.py
import pytest
from services import llm_mock, usage


def _sys(slug, lang="english"):
    return f"# Prompt: {slug}\n# Language\nWrite in {lang}.\n"


def test_slug_and_lang():
    assert llm_mock.slug_of(_sys("introduction")) == "introduction"
    assert llm_mock.lang_of(_sys("x", "italian")) == "it"
    assert llm_mock.lang_of(_sys("x")) == "en"
    assert llm_mock.slug_of("no header") is None


async def test_stream_yields_text_and_records_usage():
    token = usage.start()
    try:
        out = "".join([t async for t in llm_mock.stream(_sys("introduction"), "start")])
        acc = usage.current()
    finally:
        usage.reset(token)
    assert "13 Protein" in out
    assert acc.cost > 0 and "mock" in acc.models


async def test_validate_project_rule():
    short = await llm_mock.complete_structured(_sys("validate_project"), "U: A whey protein for gyms")
    assert short["enough"] is False and short["question"]
    long = await llm_mock.complete_structured(
        _sys("validate_project"), "U: A whey protein for gyms\nA: For whom?\nU: Target market Italy, 2 kg tubs")
    assert long["enough"] is True


async def test_extract_contact_rule():
    ok = await llm_mock.complete_structured(_sys("extract_contact"), "Mario Rossi, Rossi Nutrition, mario@example.com")
    assert ok == {"name": "Mario Rossi", "company": "Rossi Nutrition", "email": "mario@example.com", "valid": True}
    bad = await llm_mock.complete_structured(_sys("extract_contact"), "Mario Rossi")
    assert bad["valid"] is False


async def test_qa_answer_cites_context_titles():
    user = "Question: Are you certified?\n\nContext:\n[1] Quality (https://x/quality)\nsome text\n[2] About Us (https://x/about)\n"
    out = "".join([t async for t in llm_mock.stream(_sys("qa_answer"), user)])
    assert "Quality" in out and "About Us" in out


async def test_unknown_slug_falls_back():
    out = await llm_mock.complete(_sys("does_not_exist"), "x")
    assert out.startswith("[mock:does_not_exist]")
```

```python
# backend/tests/test_llm_dispatch.py
from unittest.mock import AsyncMock
from services import llm


async def test_dispatch_to_mock_by_default(monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_provider", "mock")
    out = await llm.complete("# Prompt: ask_contact\n", "x")
    assert out


async def test_dispatch_to_openrouter(monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_provider", "openrouter")
    monkeypatch.setattr(llm.openrouter, "complete", AsyncMock(return_value="real"))
    assert await llm.complete("s", "u") == "real"
```

- [x] **Step 2: Eseguire** — Expected: FAIL (moduli mancanti).

- [x] **Step 3: Scrivere `backend/data/mock_llm.json`**

Chiavi = slug. Ogni voce ha `text: {en, it}` (usato da `stream`/`complete`) oppure `json` (usato da `complete_structured`). Le voci con regole dinamiche (`validate_project`, `extract_contact`, `qa_answer`, `summarize_project`) hanno qui solo il fallback; la regola vive in `llm_mock.py`.

```json
{
  "introduction": {"text": {
    "en": "Welcome to 13 Protein. I help brands and startups shape a supplement project and get it to the right people in our team.\n\nTo start: **which option best describes you?**",
    "it": "Benvenuto in 13 Protein. La aiuto a definire un progetto di integratori e a indirizzarlo al team giusto.\n\nPer iniziare: **quale opzione la descrive meglio?**"}},
  "ask_category": {"text": {
    "en": "Great, thank you. Now tell me **what you are looking to create**: pick one of the product categories below.",
    "it": "Perfetto, grazie. Ora mi dica **cosa vuole creare**: scelga una delle categorie qui sotto."}},
  "ask_format": {"text": {
    "en": "Good choice. As an example, in this category we typically work on powders, ready-to-drink formats and single servings.\n\n**Do you already have a preferred format?**",
    "it": "Ottima scelta. A titolo di esempio, in questa categoria lavoriamo tipicamente su polveri, formati pronti da bere e monodose.\n\n**Ha già un formato preferito?**"}},
  "ask_project": {"text": {
    "en": "Now **tell me about your project**. Useful details:\n\n• Target market and customer\n• Preferred ingredients or claims\n• Expected volumes or pack size\n• Timeline\n\nA few lines are enough.",
    "it": "Ora **mi racconti il progetto**. Dettagli utili:\n\n• Mercato e cliente target\n• Ingredienti o claim preferiti\n• Volumi o formato confezione\n• Tempistiche\n\nBastano poche righe."}},
  "validate_project": {"json": {"enough": false, "question": "Which market and customer are you targeting, and do you have volumes in mind?"}},
  "summarize_project": {"text": {
    "en": "Example summary: a protein powder for the gym channel, with target market, pack size and flavours already outlined and a spring launch in mind.",
    "it": "Riassunto di esempio: una proteina in polvere per il canale palestre, con mercato, formato e gusti già definiti e un lancio previsto in primavera."}},
  "qa_intro": {"text": {
    "en": "Thank you, here is what I understood:\n\n{project_description}\n\n**Any questions about 13 Protein?** Ask me anything about how we work, or request a quote when you are ready.",
    "it": "Grazie, ecco cosa ho capito:\n\n{project_description}\n\n**Ha domande su 13 Protein?** Mi chieda pure come lavoriamo, oppure richieda un preventivo quando è pronto."}},
  "qa_answer": {"text": {
    "en": "Example answer based on the pages: {titles}. For prices, minimum quantities and lead times we prepare a quote.",
    "it": "Risposta di esempio basata sulle pagine: {titles}. Per prezzi, quantità minime e tempi di consegna prepariamo un preventivo."}},
  "ask_contact": {"text": {
    "en": "To send you a quote I need three things in one message: **your name, your company and your e-mail**.",
    "it": "Per inviarle un preventivo mi servono tre cose in un messaggio: **nome, azienda ed e-mail**."}},
  "extract_contact": {"json": {"name": null, "company": null, "email": null, "valid": false}},
  "confirm_lead": {"text": {
    "en": "Here is the summary of your request:\n\n{lead_bullets}\n\n**Confirm** to send it to our team, or **Edit** to change the contact details.",
    "it": "Ecco il riepilogo della richiesta:\n\n{lead_bullets}\n\n**Conferma** per inviarla al nostro team, oppure **Modifica** per cambiare i contatti."}},
  "evaluation": {"json": {"outcome": "completed", "path_summary": "Lead di esempio: profilo, categoria e formato raccolti, una domanda sul knowledgebase, preventivo richiesto.", "problem": "", "quote_requested": true}},
  "report_summary": {"json": {"friction_text": "Nessun attrito ricorrente nei dati di esempio.", "recommendations": ["Rivedere i prompt segnaposto prima del primo test con LLM reale.", "Verificare la copertura del knowledgebase sulle domande più frequenti."]}}
}
```

- [x] **Step 4: Scrivere `backend/services/llm_mock.py`**

```python
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
    return "it" if "italian" in system.lower() else "en"


def _record() -> None:
    _usage.record(dict(_USAGE), model=MODEL)


def _text(slug: str | None, lang: str, user: str, system: str) -> str:
    entry = _load().get(slug or "", {})
    text = (entry.get("text") or {}).get(lang) or (entry.get("text") or {}).get("en")
    if text is None:
        return f"[mock:{slug}] {user[:80]}"
    if slug == "qa_answer":
        titles = ", ".join(_TITLE_RE.findall(user)) or "none"
        return text.replace("{titles}", titles)
    if slug == "qa_intro":
        m = re.search(r"\{project_description\}", text)
        desc = _between(system, "# Input", None) or ""
        return text.replace("{project_description}", desc.strip()) if m else text
    if slug == "confirm_lead":
        bullets = _lead_bullets(system)
        return text.replace("{lead_bullets}", bullets)
    return text


def _between(text: str, start: str, end: str | None) -> str | None:
    i = text.find(start)
    if i < 0:
        return None
    j = text.find(end, i + len(start)) if end else -1
    return text[i + len(start): j if j > 0 else None]


def _lead_bullets(system: str) -> str:
    """Il prompt confirm_lead riceve il lead come JSON dopo `# Input`; lo
    restituiamo come bullet così la conferma mostra dati reali."""
    raw = _between(system, "# Input", None) or ""
    try:
        data = json.loads(raw.strip().split("\n", 1)[-1] if raw.strip().startswith("Lead") else raw.strip())
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group(0)) if m else {}
    lines = []
    for k, v in data.items():
        if isinstance(v, dict):
            v = ", ".join(f"{a}: {b}" for a, b in v.items() if b)
        if isinstance(v, list):
            v = ", ".join(map(str, v))
        if v not in (None, "", [], {}):
            lines.append(f"• **{k}**: {v}")
    return "\n".join(lines) or "• (empty)"


def _json(slug: str | None, user: str) -> dict:
    entry = _load().get(slug or "", {})
    base = dict(entry.get("json") or {})
    if slug == "validate_project":
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
```

> Nota per `qa_intro`/`confirm_lead`: i prompt `qa_intro.txt` e `confirm_lead.txt` devono avere una sezione finale `# Input` seguita dal placeholder (`{project_description}` / `{lead_json}`), così il mock lo ritrova nel system prompt già riempito. I test degli handler (Task 8) coprono il caso.

- [x] **Step 5: Scrivere `backend/services/llm.py`**

```python
"""Unico punto d'ingresso LLM per gli agent. Sceglie il provider da
settings.llm_provider a ogni chiamata (così i test possono cambiarlo)."""
from __future__ import annotations
from typing import AsyncIterator
from config import settings
from services import openrouter, llm_mock

DEFAULT_MODEL = openrouter.DEFAULT_MODEL


def _backend():
    return llm_mock if settings.llm_provider == "mock" else openrouter


async def stream(system: str, user: str, history: list[dict] | None = None,
                 model: str | None = None) -> AsyncIterator[str]:
    async for token in _backend().stream(system, user, history=history, model=model or DEFAULT_MODEL):
        yield token


async def complete(system: str, user: str, model: str | None = None) -> str:
    return await _backend().complete(system, user, model=model or DEFAULT_MODEL)


async def complete_structured(system: str, user: str, model: str | None = None) -> dict:
    return await _backend().complete_structured(system, user, model=model or DEFAULT_MODEL)


async def web_complete(system: str, user: str, model: str = "") -> str:
    return await _backend().web_complete(system, user, model=model)
```

- [x] **Step 6: Test** — Run: `python -m pytest tests/test_llm_mock.py tests/test_llm_dispatch.py -q` — Expected: verdi.

- [x] **Step 7: Commit** — `git add backend/services/llm.py backend/services/llm_mock.py backend/data/mock_llm.json backend/tests/test_llm_*.py && git commit -m "Provider LLM mock deterministico e dispatcher services.llm"`

---

### Task 5: Retrieval sul knowledgebase (keyword in memoria + adapter Qdrant)

**Files:**
- Create: `backend/services/retrieval.py`, `backend/services/retrieval_keyword.py`, `backend/services/qdrant.py` (copiato e adattato), `backend/scripts/migrate_kb.py`
- Test: `backend/tests/test_retrieval_keyword.py`, `backend/tests/test_services_qdrant.py` (copiato e adattato)

**Interfaces:**
- Produces: `retrieval.search(query, limit=3, exclude_docs=None) -> list[dict]` con chiavi `id, doc, kind, page_title, section, url, text, score`; `retrieval.doc_card(doc) -> dict | None` (prima sezione non vuota di un doc: `{title, description, url}`), usato dal carosello di categoria.
- Produces: `retrieval.CATEGORY_DOC = {"proteins": "protein-powders", "performance_and_training": "performance-training", "health_and_wellness": "health-wellness", "weight_management_and_meal_solutions": "weight-management", "drinks_shots_gels": "drinks-shots-gels", "stick_packs_and_single_servings": "stick-packs", "skincare_and_cosmetics": "skincare-cosmetics"}` (slug del form → `doc` del jsonl).
- Produces: `retrieval.format_context(chunks) -> str` nel formato `[n] Title (url)\n<text>` letto anche dal mock.

- [x] **Step 1: Test**

```python
# backend/tests/test_retrieval_keyword.py
import json
from services import retrieval_keyword as rk

ROWS = [
    {"id": "quality#0", "doc": "quality", "kind": "page", "page_title": "Quality", "section": "Standards",
     "url": "https://x/quality", "text": "Our plants follow internationally recognized standards and certification.", "status": "publish"},
    {"id": "home#0", "doc": "home", "kind": "page", "page_title": "home", "section": "Hero",
     "url": "https://x/", "text": "Manufacturing excellence for supplement brands.", "status": "publish"},
    {"id": "insights#0", "doc": "insights", "kind": "page", "page_title": "Insights", "section": "x",
     "url": "https://x/insights", "text": "certified certified certified", "status": "draft"},
]


def _index(tmp_path):
    p = tmp_path / "kb.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in ROWS))
    return rk.Index.from_jsonl(p)


def test_search_ranks_by_keyword_and_skips_drafts(tmp_path):
    idx = _index(tmp_path)
    out = idx.search("are you certified", limit=3)
    assert out[0]["doc"] == "quality"
    assert all(r["doc"] != "insights" for r in out)
    assert out[0]["score"] > 0


def test_search_exclude_and_empty(tmp_path):
    idx = _index(tmp_path)
    assert idx.search("certification", exclude_docs=["quality"]) == [] or \
        all(r["doc"] != "quality" for r in idx.search("certification", exclude_docs=["quality"]))
    assert idx.search("zzzz qqqq") == []


def test_doc_card(tmp_path):
    idx = _index(tmp_path)
    card = idx.doc_card("quality")
    assert card["title"] == "Quality" and card["url"] == "https://x/quality"
    assert idx.doc_card("nope") is None


def test_format_context():
    text = rk.format_context([ROWS[0]])
    assert text.startswith("[1] Quality (https://x/quality)\n")
```

- [x] **Step 2: Eseguire** — Expected: FAIL.

- [x] **Step 3: Scrivere `backend/services/retrieval_keyword.py`**

```python
"""Retrieval a parole chiave in memoria su knowledgebase.jsonl. Nessuna
dipendenza, nessun embedding: basta per verificare il cablaggio della chat
(spec D3). Punteggio = somma dei termini della query presenti in
page_title (x3), section (x2), text (x1). Le righe `status: draft` sono
escluse: non sono contenuto live."""
from __future__ import annotations
import json
import re
from pathlib import Path

_TOKEN_RE = re.compile(r"[a-zà-ÿ0-9]+")
_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "you",
         "your", "we", "our", "do", "does", "with", "at", "by", "it", "be", "can", "i",
         "il", "la", "lo", "le", "gli", "di", "da", "che", "e", "un", "una", "per", "con", "siete"}


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOP and len(t) > 1]


def format_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[{i}] {c.get('page_title', '')} ({c.get('url', '')})\n{c.get('text', '')}")
    return "\n\n".join(parts)


class Index:
    def __init__(self, rows: list[dict]):
        self.rows = [r for r in rows if r.get("status", "publish") != "draft"]
        self._prepared = [
            (set(tokens(r.get("page_title"))), set(tokens(r.get("section"))), set(tokens(r.get("text"))))
            for r in self.rows
        ]

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "Index":
        rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
        return cls(rows)

    def search(self, query: str, limit: int = 3, exclude_docs: list[str] | None = None) -> list[dict]:
        q = set(tokens(query))
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
                first = next((l for l in row["text"].splitlines() if l.strip() and not l.startswith("![")), "")
                return {"title": row.get("page_title", doc), "description": first.strip("#* ").strip()[:200],
                        "url": row.get("url", "")}
        return None
```

- [x] **Step 4: Scrivere `backend/services/retrieval.py`**

```python
"""Facciata del retrieval: keyword (default) o qdrant, scelto da settings."""
from __future__ import annotations
from pathlib import Path
from config import settings
from services import retrieval_keyword

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
```

- [x] **Step 5: Adattare `qdrant.py` e `migrate_kb.py`**

`cp $SRC/backend/services/qdrant.py $DST/backend/services/` e: `COLLECTION = settings.qdrant_collection`; il filtro `must_not` usa `key: "doc"`; `search(query, limit, exclude_docs)`; il fallback su errore diventa `retrieval_keyword` (log exception, poi `index().search`). `migrate_kb.py` = `migrate_essences.py` copiato, che legge il jsonl da `settings.kb_path` e indicizza `page_title + section + text` con il chunk come payload. Copiare `test_services_qdrant.py` e adattare i nomi. Non è verificabile qui contro un Qdrant reale: i test mockano httpx come nella sorgente.

- [x] **Step 6: Test** — Run: `python -m pytest tests/test_retrieval_keyword.py tests/test_services_qdrant.py -q` — Expected: verdi. Inoltre: `python -c "from services import retrieval; print(retrieval.search.__name__, len(retrieval.index().rows))"` da `backend/` deve stampare `search 171` (173 chunk meno i 2 draft).

- [x] **Step 7: Commit** — `git add backend/services/retrieval*.py backend/services/qdrant.py backend/scripts/migrate_kb.py backend/tests/test_retrieval_keyword.py backend/tests/test_services_qdrant.py && git commit -m "Retrieval sul knowledgebase: indice keyword in memoria e adapter Qdrant"`

---

### Task 6: `lib/labels.py` — bottoni con slug del form

**Files:**
- Create: `backend/lib/__init__.py`, `backend/lib/labels.py`
- Test: `backend/tests/test_labels.py`

- [x] **Step 1: Test**

```python
from lib import labels


def test_profile_buttons_en_it():
    en = labels.buttons("profile", "en"); it = labels.buttons("profile", "it")
    assert [b["value"] for b in en] == ["product_idea", "new_brand", "supplement_brand", "manufacturing_partner"]
    assert en[0]["label"] == "I have a product idea" and it[0]["label"] == "Ho un'idea di prodotto"


def test_category_and_format_include_not_sure():
    assert labels.buttons("category", "en")[-1]["value"] == labels.NOT_SURE
    assert len(labels.buttons("format", "en")) == 8


def test_values_and_label_for():
    assert "proteins" in labels.values("category")
    assert labels.label_for("category", "proteins", "it") == "Proteine"
    assert labels.label_for("category", "unknown", "en") == "unknown"
```

- [x] **Step 2: Scrivere `backend/lib/labels.py`**

```python
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
```

- [x] **Step 3: Test e commit** — `python -m pytest tests/test_labels.py -q` verde; `git add backend/lib backend/tests/test_labels.py && git commit -m "Etichette dei bottoni con gli slug del form del sito"`

---

### Task 7: Agent (wrapper sottili sui prompt)

**Files:**
- Create: `backend/agents/lead_agents.py`, `backend/agents/qa_agents.py`, `backend/agents/contact_agents.py`
- Test: `backend/tests/test_agents_lead.py`, `test_agents_qa.py`, `test_agents_contact.py`

**Interfaces:**
- `lead_agents`: `introduction(lang) -> AsyncIterator[str]`, `ask_category(profile, lang)`, `ask_format(category, lang)`, `ask_project(category, format, lang)`, `validate_project(project_raw, lang) -> tuple[bool, str]`, `summarize_project(project_raw, lang) -> str`, `confirm_lead(lead: dict, lang) -> AsyncIterator[str]`.
- `qa_agents`: `qa_intro(project_description, lang) -> AsyncIterator[str]`, `qa_answer(question, chunks, lang) -> AsyncIterator[str]` (user message = `Question: ...\n\nContext:\n` + `retrieval.format_context(chunks)`).
- `contact_agents`: `ask_contact(lang) -> AsyncIterator[str]`, `extract_contact(message, lang) -> dict`.
- Tutti passano `default_language=_LANG_NAME[lang]` e usano **solo** `services.llm`.

- [x] **Step 1: Test** (stile `test_agents_intro.py` della sorgente: monkeypatch di `llm.stream`/`complete_structured` con finti async generator, assert sul system prompt che contiene `# Prompt: <slug>` e i placeholder riempiti). Almeno: `introduction` produce token; `validate_project` mappa `{"enough": true}` → `(True, "")`; `qa_answer` costruisce il messaggio utente con `[1] Title (url)`; `extract_contact` restituisce il dict così com'è; `confirm_lead` serializza il lead con `ensure_ascii=False`.

- [x] **Step 2: Implementare** i tre moduli (~30 righe ciascuno), sul modello di `intro_agents.py`/`validator.py` della sorgente ma con `from services import llm`.

- [x] **Step 3: Test e commit** — `python -m pytest tests/test_agents_*.py -q` verde; commit `"Agent del flusso lead, domande libere e contatto"`.

---

### Task 8: Handler della state machine e router

**Files:**
- Create: `backend/handlers/__init__.py`, `backend/handlers/intro.py`, `backend/handlers/project.py`, `backend/handlers/qa.py`, `backend/handlers/contact.py`, `backend/router.py`
- Test: `backend/tests/handlers/test_intro.py`, `test_project.py`, `test_qa.py`, `test_contact.py`, `backend/tests/test_router.py`

**Interfaces:**
- Ogni handler: `async def handle_x(state: SessionState, message: str) -> AsyncIterator[Event]`.
- `router.HANDLERS: dict[Step, Handler]`, `router.dispatch(step)`.

- [x] **Step 1: Test per handler** (stile `tests/handlers/test_intro.py` della sorgente: gli agent sono monkeypatchati con generatori finti, `retrieval.search`/`doc_card` con `AsyncMock`/lambda). Coprire almeno:
  - `intro.handle`: `TextEvent` poi `ButtonsEvent(profile)`, `DoneEvent(input_enabled=False)`, step `PROFILE_SELECT`.
  - `intro.handle_profile` con valore non valido: rimanda i bottoni e resta su `PROFILE_SELECT`.
  - `intro.handle_category` con `proteins`: `CarouselEvent` con una card dal `doc_card`; con `not_sure_yet`: nessun carosello.
  - `project.handle`: primo messaggio → `enough:false` → `TextEvent(question)`, `followup_count == 1`, step `PROJECT_INPUT`, input abilitato; secondo → `project_description` valorizzata, `MessageBreakEvent`, bottoni `quote`, step `QA`; terzo giro con `enough:false` e `followup_count == 2` → procede comunque.
  - `qa.handle` con domanda: chiama `retrieval.search`, `questions_asked` e `topics_cited` aggiornati (dedup), bottoni `quote`, resta `QA`; con `request_quote`: `quote_requested True` e step `CONTACT_INPUT`.
  - `contact.handle_input` con `valid:false`: re-ask e resta; con `valid:true`: `state.contact`, bottoni `confirm`, step `CONTACT_CONFIRM`.
  - `contact.handle_confirm` con `edit`: torna a `CONTACT_INPUT`; con `confirm`: `LeadInfoEvent`, `DoneEvent(step="completed", input_enabled=False)`, `state.lead_info` valorizzato.
  - `router`: ogni `Step` tranne nessuno ha un handler; `dispatch(Step.INTRO) is intro.handle`.

- [x] **Step 2: Implementare `handlers/intro.py`**

```python
from __future__ import annotations
from typing import AsyncIterator
from models import SessionState, Step, Event, TextEvent, ButtonsEvent, CarouselEvent, DoneEvent
from agents import lead_agents
from services import retrieval
from lib import labels


async def _reask(state: SessionState, group: str, step: Step) -> AsyncIterator[Event]:
    """Valore non riconosciuto: rimanda gli stessi bottoni senza costo LLM."""
    yield ButtonsEvent(buttons=labels.buttons(group, state.default_language))
    state.current_step = step
    yield DoneEvent(step=step.value, input_enabled=False)


async def handle(state: SessionState, message: str) -> AsyncIterator[Event]:
    lang = state.default_language
    async for token in lead_agents.introduction(lang):
        yield TextEvent(token)
    yield ButtonsEvent(buttons=labels.buttons("profile", lang))
    state.current_step = Step.PROFILE_SELECT
    yield DoneEvent(step=state.current_step.value, input_enabled=False)


async def handle_profile(state: SessionState, message: str) -> AsyncIterator[Event]:
    if message not in labels.values("profile"):
        async for e in _reask(state, "profile", Step.PROFILE_SELECT):
            yield e
        return
    lang = state.default_language
    state.profile = message
    async for token in lead_agents.ask_category(labels.label_for("profile", message, "en"), lang):
        yield TextEvent(token)
    yield ButtonsEvent(buttons=labels.buttons("category", lang))
    state.current_step = Step.CATEGORY_SELECT
    yield DoneEvent(step=state.current_step.value, input_enabled=False)


async def handle_category(state: SessionState, message: str) -> AsyncIterator[Event]:
    if message not in labels.values("category"):
        async for e in _reask(state, "category", Step.CATEGORY_SELECT):
            yield e
        return
    lang = state.default_language
    state.category = message
    doc = retrieval.CATEGORY_DOC.get(message)
    card = retrieval.doc_card(doc) if doc else None
    async for token in lead_agents.ask_format(labels.label_for("category", message, "en"), lang):
        yield TextEvent(token)
    if card:
        yield CarouselEvent(cards=[{"title": card["title"], "image": "",
                                    "description": card["description"], "value": f"doc:{doc}"}])
    yield ButtonsEvent(buttons=labels.buttons("format", lang))
    state.current_step = Step.FORMAT_SELECT
    yield DoneEvent(step=state.current_step.value, input_enabled=False)


async def handle_format(state: SessionState, message: str) -> AsyncIterator[Event]:
    if message not in labels.values("format"):
        async for e in _reask(state, "format", Step.FORMAT_SELECT):
            yield e
        return
    lang = state.default_language
    state.format = message
    async for token in lead_agents.ask_project(
            labels.label_for("category", state.category or "", "en"),
            labels.label_for("format", message, "en"), lang):
        yield TextEvent(token)
    state.current_step = Step.PROJECT_INPUT
    yield DoneEvent(step=state.current_step.value, input_enabled=True)
```

- [x] **Step 3: Implementare `handlers/project.py`**

```python
from __future__ import annotations
from typing import AsyncIterator
from models import SessionState, Step, Event, TextEvent, ButtonsEvent, DoneEvent, MessageBreakEvent
from agents import lead_agents, qa_agents
from lib import labels

MAX_FOLLOWUPS = 2


async def handle(state: SessionState, message: str) -> AsyncIterator[Event]:
    lang = state.default_language
    if message:
        state.project_raw = f"{state.project_raw}\nU: {message}".strip()
    enough, question = await lead_agents.validate_project(state.project_raw, lang)
    if not enough and state.followup_count < MAX_FOLLOWUPS and question:
        state.followup_count += 1
        state.project_raw = f"{state.project_raw}\nA: {question}".strip()
        yield TextEvent(question)
        state.current_step = Step.PROJECT_INPUT
        yield DoneEvent(step=state.current_step.value, input_enabled=True)
        return
    state.project_description = await lead_agents.summarize_project(state.project_raw, lang)
    async for e in start_qa(state):
        yield e


async def start_qa(state: SessionState) -> AsyncIterator[Event]:
    lang = state.default_language
    async for token in qa_agents.qa_intro(state.project_description or "", lang):
        yield TextEvent(token)
    yield ButtonsEvent(buttons=labels.buttons("quote", lang))
    state.current_step = Step.QA
    yield DoneEvent(step=state.current_step.value, input_enabled=True)
```

- [x] **Step 4: Implementare `handlers/qa.py`**

```python
from __future__ import annotations
from typing import AsyncIterator
from models import SessionState, Step, Event, TextEvent, ButtonsEvent, DoneEvent
from agents import qa_agents
from services import retrieval
from handlers import contact
from lib import labels


async def handle(state: SessionState, message: str) -> AsyncIterator[Event]:
    lang = state.default_language
    if message == labels.REQUEST_QUOTE:
        state.quote_requested = True
        async for e in contact.start(state):
            yield e
        return
    chunks = await retrieval.search(message, limit=3)
    state.questions_asked.append(message)
    for c in chunks:
        if c.get("doc") and c["doc"] not in state.topics_cited:
            state.topics_cited.append(c["doc"])
    async for token in qa_agents.qa_answer(message, chunks, lang):
        yield TextEvent(token)
    yield ButtonsEvent(buttons=labels.buttons("quote", lang))
    state.current_step = Step.QA
    yield DoneEvent(step=state.current_step.value, input_enabled=True)
```

- [x] **Step 5: Implementare `handlers/contact.py`**

```python
from __future__ import annotations
from typing import AsyncIterator
from models import SessionState, Step, Event, TextEvent, ButtonsEvent, LeadInfoEvent, DoneEvent
from agents import contact_agents, lead_agents
from lib import labels

COMPLETED_MSG = {
    "en": "Thank you. Your request has been sent to the 13 Protein team.",
    "it": "Grazie. La sua richiesta è stata inviata al team di 13 Protein.",
}


async def start(state: SessionState) -> AsyncIterator[Event]:
    lang = state.default_language
    async for token in contact_agents.ask_contact(lang):
        yield TextEvent(token)
    state.current_step = Step.CONTACT_INPUT
    yield DoneEvent(step=state.current_step.value, input_enabled=True)


async def handle_input(state: SessionState, message: str) -> AsyncIterator[Event]:
    lang = state.default_language
    data = await contact_agents.extract_contact(message, lang)
    if not data.get("valid"):
        async for e in start(state):
            yield e
        return
    state.contact = {"name": data.get("name"), "company": data.get("company"), "email": data.get("email")}
    async for token in lead_agents.confirm_lead(state.to_lead_info(), lang):
        yield TextEvent(token)
    yield ButtonsEvent(buttons=labels.buttons("confirm", lang))
    state.current_step = Step.CONTACT_CONFIRM
    yield DoneEvent(step=state.current_step.value, input_enabled=False)


async def handle_confirm(state: SessionState, message: str) -> AsyncIterator[Event]:
    if message == labels.EDIT:
        state.contact = None
        async for e in start(state):
            yield e
        return
    if message != labels.CONFIRM:
        yield ButtonsEvent(buttons=labels.buttons("confirm", state.default_language))
        yield DoneEvent(step=Step.CONTACT_CONFIRM.value, input_enabled=False)
        return
    state.lead_info = state.to_lead_info()
    yield LeadInfoEvent(state.lead_info)
    state.current_step = Step.COMPLETED
    yield DoneEvent(step="completed", input_enabled=False)


async def handle_completed(state: SessionState, message: str) -> AsyncIterator[Event]:
    yield TextEvent(COMPLETED_MSG.get(state.default_language, COMPLETED_MSG["en"]))
    yield DoneEvent(step="completed", input_enabled=False)
```

- [x] **Step 6: `router.py`**

```python
from typing import Callable
from models import Step
from handlers import intro, project, qa, contact

Handler = Callable

HANDLERS: dict[Step, Handler] = {
    Step.INTRO:           intro.handle,
    Step.PROFILE_SELECT:  intro.handle_profile,
    Step.CATEGORY_SELECT: intro.handle_category,
    Step.FORMAT_SELECT:   intro.handle_format,
    Step.PROJECT_INPUT:   project.handle,
    Step.QA:              qa.handle,
    Step.CONTACT_INPUT:   contact.handle_input,
    Step.CONTACT_CONFIRM: contact.handle_confirm,
    Step.COMPLETED:       contact.handle_completed,
}


def dispatch(step: Step) -> Handler:
    handler = HANDLERS.get(step)
    if handler is None:
        raise ValueError(f"No handler registered for step: {step!r}")
    return handler
```

- [x] **Step 7: Test e commit** — `python -m pytest tests/handlers tests/test_router.py -q` verde; commit `"Handler della state machine lead e router"`.

---

### Task 9: `main.py`, valutazione in background, `init_db.sql`

**Files:**
- Create: `backend/main.py` (copiato e adattato), `backend/agents/evaluation.py` (copiato e adattato), `backend/scripts/init_db.sql` (riscritto), `backend/testing_env.py` + `backend/data/testing_facsimiles.json`, `backend/retention.py` (copiato), `backend/scripts/purge_expired.py` (copiato)
- Test: `backend/tests/test_main_completion.py`, `test_main_error_stream.py`, `test_main_skip.py`, `test_main_testing_flag.py`, `test_main_usage_carry.py`, `test_evaluation.py`, `test_retention.py`, `test_testing_env.py` (copiati e adattati)

- [x] **Step 1: Copiare** `main.py`, `agents/evaluation.py`, `retention.py`, `testing_env.py`, `scripts/purge_expired.py` e i test elencati.

- [x] **Step 2: Adattare `main.py`**

- Import: `from models import Step, ButtonsEvent, CarouselEvent, ErrorEvent, MessageBreakEvent, MESSAGE_BREAK`; `app = FastAPI(title="13 Protein Agent")`.
- `_STREAM_ERROR_MESSAGE`: chiavi `en` (default) e `it`; `lang = req.default_language or "en"`.
- Sostituire `new_essence_names(before, state)` con:

```python
def new_topics(before: set[str], state) -> list[str]:
    """Doc del KB citati in questo turno e non prima (ordine di citazione)."""
    return [d for d in state.topics_cited if d not in before]
```

e in `chat()`: `before_topics = set(state.topics_cited)` prima del dispatch; dopo, `INSERT INTO session_topics (session_id, doc) VALUES ($1, $2)`.
- `_abandon_sweep_loop` e `chats_list`: `for sid, profile in ids: if profile is not None: _fire_eval(sid)`.
- `/chat/{session_id}/skip`: `state.to_lead_info()`, `testing_env.load_facsimile(state.profile)`, risposta `SkipResponse(lead_info=merged)`.
- `/report`: invariato (usa `reporting.build_report` del Task 10).
- Tutto il resto (transazioni brevi, carry-forward, `collect_payload`, retention loop) invariato.

- [x] **Step 3: Adattare `agents/evaluation.py`**: `from services import llm` al posto di `openrouter`; campi upsert `outcome`, `summary=path_summary`, `friction_note=problem`, `quote_requested=bool(...)`, `model=llm.DEFAULT_MODEL if settings.llm_provider != "mock" else "mock"`.

- [x] **Step 4: Scrivere `backend/scripts/init_db.sql`** (schema pulito)

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id                TEXT PRIMARY KEY,
    state             JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now(),
    completed_at      TIMESTAMPTZ,
    abandoned_at      TIMESTAMPTZ,
    is_testing        BOOLEAN NOT NULL DEFAULT false,
    total_cost        NUMERIC DEFAULT 0,
    prompt_tokens     BIGINT  DEFAULT 0,
    completion_tokens BIGINT  DEFAULT 0,
    -- colonne di reporting, riscritte a ogni save da SessionState (session.py)
    profile           TEXT,
    category          TEXT,
    format            TEXT,
    quote_requested   BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions (updated_at);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions (created_at);

CREATE TABLE IF NOT EXISTS transcripts (
    id                SERIAL PRIMARY KEY,
    session_id        TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    role              TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content           TEXT NOT NULL,
    step              TEXT,
    payload           JSONB,
    cost              NUMERIC,
    prompt_tokens     BIGINT,
    completion_tokens BIGINT,
    model             TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_transcripts_session ON transcripts (session_id);

CREATE TABLE IF NOT EXISTS evaluations (
    session_id        TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    status            TEXT NOT NULL DEFAULT 'pending',
    outcome           TEXT,
    summary           TEXT,
    friction_note     TEXT,
    quote_requested   BOOLEAN,
    model             TEXT,
    cost              NUMERIC,
    prompt_tokens     BIGINT,
    completion_tokens BIGINT,
    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now()
);

-- Un doc del knowledgebase citato in una risposta della sessione (main.py::new_topics).
CREATE TABLE IF NOT EXISTS session_topics (
    id         SERIAL PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    doc        TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_session_topics_session ON session_topics (session_id);
CREATE INDEX IF NOT EXISTS idx_session_topics_doc ON session_topics (doc);

CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

- [x] **Step 5: `testing_env.py`**: `FIELD_SENTINELS` = i valori vuoti di `to_lead_info()` (`profile: None`, `category: None`, `format: None`, `projectDescription: None`, `questionsAsked: []`, `topicsCited: []`, `quoteRequested: False`, `contact: {"name": None, "company": None, "email": None}`); `DEFAULT_PATH = "product_idea"`; `data/testing_facsimiles.json` con una voce per profilo (4) contenente un `lead_info` di esempio completo.

- [x] **Step 6: Adattare i test** ai nuovi nomi (`new_topics`, `lead_info`, `profile`), poi eseguire: `python -m pytest tests/test_main_*.py tests/test_evaluation.py tests/test_retention.py tests/test_testing_env.py -q` — Expected: verdi.

- [x] **Step 7: Commit** — `"Ciclo del turno, valutazione in background, schema Postgres e ambiente di test"`

---

### Task 10: Reporting e narrativa del Resoconto

**Files:**
- Create: `backend/reporting.py`, `backend/report_agents.py`, `backend/scripts/preview_prompts.py` (registry nuovo)
- Test: `backend/tests/test_reporting.py`, `test_report_agents.py`, `test_main_report.py` (copiati e adattati)

**Interfaces:**
- `reporting.build_report(conn, date_from, date_to) -> dict` con chiavi `period`, `total_sessions`, `outcomes` (invariato, `initialized` = abbandonate con `profile IS NULL`), `by_profile`, `by_category`, `by_format` (ognuna `[{value, total, completed, completion_rate}]`), `quote` (`{requested, decided_total, rate}`), `duration`, `friction` (invariato), `top_topics` (`[{doc, count}]` da `session_topics`), `by_weekday`.
- `report_agents.generate_narrative(stats) -> dict` (`friction_text`, `recommendations`) via `llm.complete_structured`.

- [x] **Step 1: Copiare e riscrivere** le funzioni sul modello della sorgente: `path_performance` → `_breakdown(conn, column, ...)` parametrica su `profile|category|format`; `delegate_rate` → `quote_rate` (`count(*) FILTER (WHERE quote_requested)` sulle sessioni decise); `essence_swap_rate` rimosso; `top_essences` → `top_topics`.
- [x] **Step 2: Test**: i test della sorgente mockano `conn.fetch`/`fetchrow`; adattarli alle nuove chiavi e aggiungere `test_build_report_keys`.
- [x] **Step 3: `preview_prompts.py`**: registry con i prompt conversazionali del Task 3 e fixture di esempio (profilo, categoria, formato, progetto, chunk KB).
- [x] **Step 4: Test e commit** — `python -m pytest -q` (tutta la suite backend) verde; commit `"Reporting del Resoconto per profilo, categoria, formato e topic"`.

---

### Task 11: Server Node (proxy, admin, analytics, retention)

**Files:**
- Create: `server/index.js`, `server/routes/{chat,chats,chat-settings,chat-skip,track,report,admin-users}.js`, `server/lib/{admin-auth,admin-users,rate-limit,analytics,segments,retention}.js`, `server/scripts/{create-admin,purge-expired}.js`
- Test: `server/lib/{admin-auth,admin-users,rate-limit,segments,retention}.test.js`, `server/routes/{chat-settings,report}.test.js`

- [x] **Step 1: Copiare** i file elencati dalla sorgente (`server/lib/legacy-*`, `recipe*`, `purchase`, `essence-numbers`, `shop/`, `perfume*`, `create-cart`, `get-recipe`, `update-recipe`, `recipe-transcript`, `id.js` **non** si copiano).
- [x] **Step 2: Adattare `server/index.js`**: togliere import e route di ricette/perfume/cart/shop, `getShopAdapter().validateConfig()` e il log e-commerce; togliere il perm `ricette`; tenere `chat`, `resoconto`, `user-management`; route rimanenti: `/api/track`, `/api/chat`, `/api/admin/login`, `/api/admin/users*`, `/api/chats*`, `/api/chat-settings`, `/api/report/stats`, `/api/report`, `/api/chat/skip`, `/admin*`, statici, fallback SPA.
- [x] **Step 3: Adattare `routes/chats.js`**: semplice proxy, senza `enrichPurchases`.
- [x] **Step 4: Adattare `routes/track.js` e `routes/report.js`**: `ALLOWED_EVENTS = page_view, cta_click, chat_complete, quote_request`; `computeFunnel` conta `quote_requests` al posto di `add_to_carts` (niente taglie).
- [x] **Step 5: Adattare `lib/admin-users.js`**: `ALL_PERMS = ['chat', 'resoconto', 'user-management']`.
- [x] **Step 6: Adattare `lib/retention.js`**: tenere solo `pruneAnalyticsLines`, `retentionConfig`, `purgeCycle`, `startRetentionLoop` (analytics JSONL); rimuovere record profumo e transcript legacy; adattare il test.
- [x] **Step 7: Test** — Run: `npm test` — Expected: verde (i test copiati: auth, users, rate-limit, segments, retention ridotto, chat-settings, report adattato).
- [x] **Step 8: Commit** — `"Server Node: proxy SSE, admin, analytics e retention senza e-commerce"`

---

### Task 12: Frontend cliente (chat, landing minima, riepilogo lead)

**Files:**
- Create: `src/main.jsx`, `src/App.jsx`, `src/globals.css`, `src/index.css`, `src/App.css`, `src/contexts/{ConversationContext,LanguageContext}.jsx`, `src/i18n/translations.js`, `src/utils/{route,track,clientEnv}.js` (+ test), `src/api/Retrieve.jsx`, `src/components/{Conversation,Chat,Message,UserInput,TestingGate,PrivacyPolicy}/*`, `src/components/LandingPage/LandingPage.jsx` (+ css, minima), `src/components/Journey/Journey.jsx`, `src/components/LeadSummary/{LeadSummary.jsx,LeadSummary.css}`
- Create: `public/favicon.svg` (segnaposto), `public/robots.txt`

- [x] **Step 1: Copiare** `src/main.jsx`, `App.jsx`, `globals.css`, `index.css`, `App.css`, contexts, `i18n/translations.js`, `utils/*`, `api/Retrieve.jsx`, `components/{Conversation,Chat,Message,UserInput,TestingGate,PrivacyPolicy}`.
- [x] **Step 2: `Retrieve.jsx`**: caso `general_info` → `lead_info`, handler `onLeadInfo`, flag `isLeadInfoSet`.
- [x] **Step 3: `Conversation.jsx`**: prop `updateLeadInfo`; `onLeadInfo`; titolo `t.chat.title`; `sessionStorage` key `agent13_skipLanding`; il `session_id` resta `<env>_<random>_<ts>`.
- [x] **Step 4: `LanguageContext.jsx`**: `getLanguageFromURL` → `it` se il path inizia con `/it`, altrimenti `en`; `toggleLanguage` naviga a `/it` o `/`; `localePath` prefissa `/it`. `utils/route.js::normalizePath` toglie il prefisso `/it`. Aggiornare i test copiati.
- [x] **Step 5: `translations.js`**: riscrivere solo le chiavi usate (`chat.*`, `landing.*`, `leadSummary.*`, `privacy.*`, `testing.*`), EN e IT, senza brand Alchimista; `typingVariants` es. "The assistant is checking the knowledge base…".
- [x] **Step 6: `LandingPage.jsx`** minima: titolo "13 Protein · Project assistant", una riga, toggle EN/IT, bottone Start (`trackEvent('cta_click')`, `setHasBegun(true)`), riga di disclosure AI + link privacy.
- [x] **Step 7: `Journey.jsx`** (ex `Ritual`): `Conversation` + `LeadSummary` quando la chat finisce; nessun POST (il lead è già in Postgres nello stato); `trackEvent('quote_request')` se `leadInfo.quoteRequested`.
- [x] **Step 8: `LeadSummary.jsx`**: tabella a due colonne dei campi di `lead_info` (label da `t.leadSummary.fields`), contatto e topic citati come lista.
- [x] **Step 9: `App.jsx`**: route `/privacy-policy`, `/testing`, altrimenti landing ↔ `Journey`.
- [x] **Step 10: Verifica** — Run: `npm run lint && npm run build && npm test` — Expected: build ok, nessun errore lint nuovo, test verdi.
- [x] **Step 11: Commit** — `"Frontend cliente: chat riusata, landing minima e riepilogo del lead"`

---

### Task 13: Admin (Chat, Resoconto, Utenti)

**Files:**
- Create: `src/admin/{main.jsx,AdminShell.jsx,AdminShell.css,auth.js}`, `src/admin/charts/*`, `src/admin/modules/UtentiModule.*`, `src/admin/modules/chat/{ChatList,ChatDetail,PathFilter→ProfileFilter,filters,format}.*` (+ test), `src/admin/modules/resoconto/{ResocontoModule.*,format.js,reportText.js,sections/*}` (+ test)

- [x] **Step 1: Copiare** tutto `src/admin/` tranne `modules/RicetteModule.*` e `modules/recipeView.*`.
- [x] **Step 2: `AdminShell.jsx`**: `PERM_TO_PATH` e `MODULE_LABEL` senza `ricette`; logo testuale "13 Protein · Admin"; route senza `/ricette`.
- [x] **Step 3: Chat**: `filters.js` → `matchesProfiles` sui 4 profili; `PathFilter` → `ProfileFilter`; `format.js` → `profileLabel`, `STATUS_LABEL` invariato; `ChatDetail` mostra `profile/category/format/quote_requested` e l'evaluation con "Preventivo richiesto: sì/no"; togliere il bottone "Vai alla ricetta" e la fetch `perfume-by-session`; colonna "Acquistate" del select → rimuovere (resta Tutte/Completate).
- [x] **Step 4: Resoconto**: sezioni `FunnelSection` (page_view → cta → chat_complete → quote_request), `DispositiviSection`, `EsitiSection`, `ProfiliSection` (barre per profile/category/format da `stats.by_*`), `TopicSection` (tabella `top_topics`), `SettimanaSection`; rimuovere `EssenzeSection`/`PercorsiSection`; `reportText.js` riscritto sulle nuove chiavi (test aggiornato).
- [x] **Step 5: Verifica** — `npm run lint && npm run build && npm test` — Expected: ok.
- [x] **Step 6: Commit** — `"Admin: moduli Chat, Resoconto e Utenti sul dominio lead"`

---

### Task 14: Docker, compose e script di avvio

**Files:**
- Create: `Dockerfile`, `backend/Dockerfile`, `docker-compose.local.yml`, `docker-compose.prod.yml`, `start.local.sh`, `start.prod.sh`

- [x] **Step 1: Copiare** `Dockerfile` (root, togliere `RUN mkdir -p /data/recipes` e `RECIPES_DIR`), `backend/Dockerfile`, `docker-compose.local.yml` e `docker-compose.atelier.yml` → `docker-compose.prod.yml`, `start.local.sh`, `start.prod.sh`.
- [x] **Step 2: Adattare**: `name: agent13_*`; servizio `app` senza `PS_*`/`SHOPIFY_*`/`RECIPES_DIR`/`RETENTION_RECIPE_DAYS`/`RETENTION_PURCHASED_RECIPE_DAYS`; servizio `backend` con `LLM_PROVIDER`, `RETRIEVAL_PROVIDER`, `KB_PATH=/app/knowledgebase/knowledgebase.jsonl` e un volume `./knowledgebase:/app/knowledgebase:ro`; Postgres `POSTGRES_DB: agent13`; Qdrant resta ma è opzionale (profilo compose `qdrant`).
- [x] **Step 3: Verifica** — `docker compose -f docker-compose.local.yml config >/dev/null` (valida la sintassi anche senza daemon) — Expected: exit 0. Nota: l'esecuzione reale non è possibile in questa sessione (nessun daemon).
- [x] **Step 4: Commit** — `"Docker e compose dell'harness (non eseguiti in questa sessione)"`

---

### Task 15: Verifica end-to-end in locale (Postgres da apt, mock LLM, UI)

**Files:**
- Create: `scripts/e2e-mock.sh`, `scripts/e2e-ui.mjs`, `scripts/dev-local.sh`

- [x] **Step 1: Postgres locale**

```bash
sudo apt-get install -y postgresql   # 16, già in cache apt
sudo service postgresql start
sudo -u postgres psql -c "CREATE USER agent13 WITH PASSWORD 'changeme';" -c "CREATE DATABASE agent13 OWNER agent13;"
psql postgresql://agent13:changeme@localhost/agent13 < backend/scripts/init_db.sql
```

- [x] **Step 2: `scripts/dev-local.sh`** (avvia backend e Node in background su porte 8000/3000 con env mock, `ANALYTICS_LOG=./data/analytics/events.jsonl`, `ADMIN_USERS_FILE=./data/admin/users.json`; crea l'admin `tester`/`tester` con `CREATE_ADMIN_PASSWORD`; `npm run build` prima di avviare Node).

- [x] **Step 3: `scripts/e2e-mock.sh`**: con `curl -N`, invia la sequenza fissa delle Global Constraints a `POST http://localhost:3000/api/chat` (stesso `session_id`), salva ogni stream, e verifica con `grep`:
  - ogni risposta contiene `event: done`;
  - la 2ª contiene `event: buttons` con `product_idea`; la 4ª contiene `event: carousel`;
  - la 6ª (progetto, secondo giro) contiene `event: message_break` e `request_quote`;
  - la 7ª (domanda KB) contiene `Quality` (il mock cita i titoli dei chunk trovati);
  - la 10ª contiene `event: lead_info` con `"quoteRequested": true` e `"email": "mario@example.com"`, e `"step": "completed"`;
  - poi `curl` con token admin su `/api/chats/<id>`: `status: completata`, `eval_status: done` (attendere fino a 5 s), `total_cost > 0`, `messages` non vuoto;
  - `/api/report/stats?from=<oggi>&to=<oggi>`: `stats.total_sessions >= 1`, `stats.top_topics` contiene `quality`, `funnel.quote_requests >= 1` se l'evento è stato inviato (la UI lo invia; da curl si invia a mano con `POST /api/track`).
  Exit non-zero al primo check fallito.

- [x] **Step 4: `scripts/e2e-ui.mjs`** (Playwright con Chromium preinstallato, `executablePath: '/opt/pw-browsers/chromium'` se serve): apre `http://localhost:3000`, clicca Start, esegue la stessa sequenza cliccando i bottoni per label e scrivendo i testi, attende `LeadSummary`, screenshot in `docs/superpowers/evidence/2026-09-09/01-lead-summary.png`; poi `/admin`, login `tester`, apre la chat appena creata (screenshot `02-admin-chat.png`) e `/admin/resoconto` (screenshot `03-resoconto.png`). Asserzioni: zero errori console, `LeadSummary` mostra `mario@example.com`.

- [x] **Step 5: Eseguire** — `scripts/dev-local.sh && scripts/e2e-mock.sh && node scripts/e2e-ui.mjs` — Expected: tutti i check passano; screenshot prodotti.
- [x] **Step 6: Anche con lingua `it`**: ripetere `e2e-mock.sh` con `default_language=it` sul launch e verificare che il primo `text` contenga "Benvenuto".
- [x] **Step 7: Commit** — `git add scripts docs/superpowers/evidence && git commit -m "Verifica end-to-end del mock: script curl, Playwright e screenshot"`

---

### Task 16: `CLAUDE.md` e README dell'harness

**Files:**
- Modify: `CLAUDE.md` (fondere: sezione knowledgebase esistente + nuova sezione "Agente (harness mock)": architettura, ciclo del turno, contratto SSE, flusso e step, prompt e mock, retrieval, analytics, admin, come girare in locale, test, cosa è segnaposto)
- Create: `README.md` (breve: cos'è, come si avvia in locale, come si passa a `LLM_PROVIDER=openrouter`)
- Modify: `docs/analisi-alchimista.md` (una riga in testa: "Implementato come harness mock: vedi spec/plan del 2026-09-09")

- [x] **Step 1: Scrivere**, seguendo lo stile del `CLAUDE.md` esistente (italiano, gotcha espliciti). Elencare i punti **segnaposto** in un'unica lista: prompt, `mock_llm.json`, facsimili di test, traduzioni, landing, privacy, termini di retention.
- [x] **Step 2: Commit e push** — `git add CLAUDE.md README.md docs && git commit -m "Documentazione dell'harness mock" && git push -u origin claude/13protein-ai-agent-setup-kkti3l`

---

## Esecuzione

Eseguito il 2026-09-10 su `claude/13protein-ai-agent-setup-kkti3l`, un commit per
task. Scostamenti dal piano, tutti annotati nei commit:

- **`qa_intro` non ripete il riassunto**: il riassunto è una bolla propria emessa
  dall'handler, poi `message_break`, poi l'invito. Il piano lo faceva ripetere
  dentro `qa_intro`, cioè due volte di seguito nella stessa schermata.
- **`retrieval_keyword` confronta le radici troncate a 5 caratteri**: con il
  confronto esatto "are you certified" non trovava la pagina Quality, che scrive
  "certification".
- **`llm_mock.lang_of` legge solo la sezione `# Language`**: cercare "italian"
  in tutto il system prompt rendeva italiana ogni risposta, perché ogni prompt
  conversazionale ha una sezione `## Italian` fra gli esempi.
- **`vite.config.js` non usa `__dirname`**: con `"type": "module"` il file è ESM
  e quella variabile non esiste, il lint la segnalava.
- **Qdrant sta in un profilo compose**: con il retrieval a parole chiave di
  default nessuno lo interroga.
- **Playwright non è una dipendenza del progetto**: il suo postinstall
  scaricherebbe un browser dentro l'immagine Docker.
- **L'informativa privacy è un segnaposto dichiarato**, non il testo
  dell'Alchimista con il marchio cambiato.
- **Le evidenze stanno in `docs/superpowers/evidence/2026-09-10/`** (la data di
  esecuzione, non quella del piano).

## Ordine ed esecuzione

I task 1-10 (backend) sono sequenziali. Il Task 11 (Node) dipende solo dal Task 0 e può andare in parallelo al backend. I task 12-13 (frontend) dipendono dal contratto SSE (Task 2) e dalle route Node (Task 11). Il Task 15 richiede tutto. Stima: ~120 file, di cui ~70 copiati con modifiche puntuali e ~25 nuovi.
