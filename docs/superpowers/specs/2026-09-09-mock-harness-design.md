# Harness mock dell'agente 13protein — Design

**Data:** 2026-09-09 · **Stato:** proposta, da confermare prima dell'implementazione
**Base:** `Mactywd/alchimista_ndc` @ `12ffcac` (analisi in `docs/analisi-alchimista.md`)
**Nota di metodo:** la skill `superpowers` non è installata in questa sessione; spec e piano
seguono il formato e il flusso di `docs/superpowers/` dell'Alchimista (brainstorm → spec →
piano a task con test e commit per task).

## Obiettivo

Portare in questa repo la parte **generica e già funzionante** dell'Alchimista (ciclo del
turno, SSE, prompt loader, servizi LLM, persistenza, analytics a tre strati, admin, retention,
UI chat) e sostituire tutto ciò che è profumo con una versione **mock** per 13protein:

- un flusso di qualificazione lead ricalcato sul form del sito (`knowledgebase/site/forms.md`)
  più uno step di domande libere con retrieval sul knowledgebase;
- **prompt segnaposto** ("sei un venditore di un produttore B2B di integratori, rispondi con
  dati di esempio"), già nel formato di `LINEEGUIDA.md`, da riscrivere una volta definiti i
  task veri;
- un **provider LLM mock** deterministico, così l'intero stack gira, si testa e si dimostra
  **senza chiave OpenRouter** e senza Qdrant.

Il risultato è un harness su cui, nel passo successivo, si progettano prompt, flussi e
l'infrastruttura custom. Non è il prodotto: è il banco di prova.

## Non-obiettivi

- Nessun prompt definitivo, nessuna decisione sul tono/persona dell'agente.
- Nessun e-commerce, checkout, email, integrazione CRM.
- Nessuna landing editoriale: una pagina minima con titolo, toggle lingua e "Start".
- Nessuna traduzione approvata: `en` default, `it` come seconda lingua per verificare che il
  meccanismo a più lingue funzioni. Le altre due lingue WPML (es, sv) restano fuori.
- Nessun deploy: compose e Dockerfile vengono portati e adattati, ma la verifica qui è su
  host (Postgres da apt, backend con uvicorn, Node, browser Chromium).

## Decisioni prese (da confermare)

| # | Decisione | Alternativa scartata e perché |
|---|---|---|
| D1 | L'app vive **in root** della repo (`backend/`, `server/`, `src/`, `public/`, `package.json`, compose) accanto a `tools/` e `knowledgebase/` | Una sottocartella `agent/` terrebbe la pipeline KB separata, ma romperebbe ogni percorso relativo dei compose, degli script e di `CLAUDE.md` dell'Alchimista, che è la fonte da cui si copia |
| D2 | `LLM_PROVIDER=mock` (default) \| `openrouter`. Il mock risponde per **slug del prompt**, che il loader inserisce come prima riga `# Prompt: <slug>` in ogni prompt | Un mock che rispondesse "sempre la stessa cosa" non permetterebbe di far avanzare la state machine (i validatori si aspettano JSON o parole chiave) |
| D3 | `RETRIEVAL_PROVIDER=keyword` (default, in memoria su `knowledgebase/knowledgebase.jsonl`) \| `qdrant` | Qdrant non è disponibile qui e richiede embedding a pagamento; il ranking per parole chiave basta per verificare il cablaggio |
| D4 | Lingua di default **`en`**, seconda `it`; i valori canonici dei bottoni sono **slug inglesi** (`product_idea`, `proteins`, …) presi dal form del sito | L'Alchimista usa valori canonici italiani; qui il sito è inglese e gli slug sono già definiti nel form |
| D5 | L'oggetto finale si chiama **`lead_info`** e sostituisce `general_info` (evento SSE `lead_info`) | Tenere il nome `general_info` avrebbe confuso il contratto |
| D6 | Le colonne di reporting su `sessions` sono `profile`, `category`, `format`, `quote_requested` (bool); la tabella `session_essences` diventa `session_topics` (una riga per doc del KB citato in una risposta) | Non tracciare i topic toglierebbe al Resoconto la "top 5" che oggi è il pezzo più utile |
| D7 | `requires-python = ">=3.11"` (il codice compila senza modifiche); Docker resta su 3.12 | Il container 3.12 è già validato in produzione |
| D8 | `/testing` con "Salta conversazione" resta, con facsimili di `lead_info` | Toglierlo risparmia poco e perde uno strumento di test utile |
| D9 | Il modulo admin Ricette **non** viene portato; restano Chat, Resoconto, Utenti | Non c'è un artefatto post-chat da modificare a mano, per ora |

## Architettura (invariata rispetto all'Alchimista)

```
Browser (React/Vite, src/)  ──POST /api/chat (SSE)──▶  Express (server/, :3000)
                                                            │ POST $BACKEND_URL/chat
                                                            ▼
                                            FastAPI (backend/, :8000)
                                              ├─ Postgres  sessions / transcripts / evaluations /
                                              │            session_topics / app_settings
                                              ├─ retrieval  keyword (jsonl in memoria) | qdrant
                                              └─ llm        mock | openrouter
```

Contratto SSE identico (`text`, `buttons`, `carousel`, `message_break`, `error`, `done`),
con `general_info` rinominato in **`lead_info`**. Il carosello resta nel contratto e nella UI
(servirà per mostrare card di categoria/prodotto), ma il flusso mock lo usa in un solo punto.

## Flusso conversazionale mock

Ricalca i tre step del form del sito, poi apre alle domande libere, poi raccoglie il contatto.

| Step | Cosa succede | Input |
|---|---|---|
| `intro` | saluto + "Which option best describes you?" | bottoni: I have a product idea / I'm launching a new brand / I already have a supplement brand / I'm looking for a manufacturing partner |
| `profile_select` | salva `profile`; "What are you looking to create?" | bottoni: 7 categorie + Not sure yet |
| `category_select` | salva `category`; mostra un **carosello** con la card della categoria scelta (titolo + prima riga della pagina KB) e chiede il formato preferito | bottoni: 8 formati + Not sure yet |
| `format_select` | salva `format`; "Tell us about your product idea…" | testo libero |
| `project_input` | validatore LLM → `{"enough": bool, "question": str}`; se non basta, una domanda di follow-up (max 2 giri, poi si procede comunque); se basta, `project_description` sintetizzata e recap | testo libero |
| `qa` | "Any questions about 13 Protein? Ask me, or request a quote." Ogni domanda: retrieval top-3 sul KB → risposta LLM con i chunk come contesto e citazione della pagina; i `doc` citati vanno in `session_topics` | testo libero + bottone Request a quote |
| `contact_input` | "Leave your name, company and e-mail" → LLM estrae `{"name","company","email","valid"}`; se `valid:false` richiede | testo libero |
| `contact_confirm` | recap del lead + Confirm / Edit | bottoni |
| `completed` | emette `lead_info`, chiude l'input | — |

Buchi noti del KB (prezzi, MOQ, lead time, certificati solo in footer): il prompt di `qa`
istruisce a **non inventare** e a rimandare al preventivo. Nel mock la risposta è fissa.

### `lead_info` (contratto camelCase, come `general_info`)

```json
{
  "profile": "product_idea",
  "category": "proteins",
  "format": "powders",
  "projectDescription": "…",
  "questionsAsked": ["…"],
  "topicsCited": ["private-label", "quality"],
  "quoteRequested": true,
  "contact": {"name": "…", "company": "…", "email": "…"},
  "language": "en"
}
```

### `SessionState` (campi principali)

`current_step`, `default_language`, `profile`, `category`, `format`, `project_raw` (transcript
U:/A: dello step progetto), `project_description`, `followup_count`, `questions_asked`,
`topics_cited`, `quote_requested`, `contact` (dict), `lead_info`, più i campi `pending_*` per il
carry-forward dei costi (invariati).

## Prompt segnaposto

Un file per chiamata LLM, tutti già nel formato di `LINEEGUIDA.md` (sezioni, bullet, esempi
`en`/`it`, placeholder invariati), con il testo del ruolo ridotto al segnaposto concordato:

> *You are a placeholder sales assistant for 13 Protein, a European B2B contract manufacturer
> of supplements. Answer with plausible example data; this prompt will be rewritten.*

| slug | tipo | placeholder |
|---|---|---|
| `introduction` | conversazionale | `default_language` |
| `ask_category` | conversazionale | `default_language`, `profile` |
| `ask_format` | conversazionale | `default_language`, `category` |
| `ask_project` | conversazionale | `default_language`, `category`, `format` |
| `validate_project` | JSON `{enough, question}` | `default_language`, `project_raw` |
| `summarize_project` | testo breve | `default_language`, `project_raw` |
| `qa_intro` | conversazionale | `default_language`, `project_description` |
| `qa_answer` | conversazionale con contesto | `default_language`, `question`, `context` |
| `ask_contact` | conversazionale | `default_language` |
| `extract_contact` | JSON `{name, company, email, valid}` | `default_language`, `message` |
| `confirm_lead` | conversazionale | `default_language`, `lead_json` |
| `evaluation` | JSON `{outcome, path_summary, problem, quote_requested}` | `transcript` |
| `report_summary` | JSON `{friction_text, recommendations}` | `stats_json` |

`_HEADER` condiviso: brand "13 Protein", pubblico B2B (aziende che cercano un produttore),
tono professionale, niente em dash, regola "non inventare prezzi/MOQ/lead time/certificazioni".

## Provider LLM mock

`backend/services/llm.py` espone `stream`, `complete`, `complete_structured`, `web_complete`
con la stessa firma di `openrouter.py` e sceglie il backend da `settings.llm_provider`.
`backend/services/llm_mock.py`:

- legge lo slug dalla prima riga `# Prompt: <slug>` del system prompt;
- tabella `backend/data/mock_llm.json` → per slug una risposta `text` (per `stream`, emessa a
  pezzi di 3-4 parole con `await asyncio.sleep(0)`), oppure `json` (per `complete_structured`);
- regole minime per far avanzare il flusso: `validate_project` risponde `enough:false` al primo
  giro e `enough:true` dal secondo (o subito se il messaggio supera 80 caratteri);
  `extract_contact` estrae l'email con regex e `valid` di conseguenza; `qa_answer` cita i titoli
  dei chunk passati nel contesto;
- registra su `usage` un costo fisso di 0.0001 $ e 100/50 token, così la contabilità e il
  Resoconto hanno numeri non nulli.

## Retrieval

`backend/services/retrieval.py`: `search(query, limit=3, exclude_docs=None) -> list[dict]` con
payload `{id, doc, kind, page_title, section, url, text}` (le chiavi del jsonl).
- `keyword`: carica `knowledgebase/knowledgebase.jsonl` all'avvio (percorso `KB_PATH`),
  tokenizza, punteggio = somma dei termini della query presenti in `page_title`, `section`,
  `text` con peso 3/2/1, esclude `status: draft`; nessuna dipendenza.
- `qdrant`: adattamento di `qdrant.py` (collection `kb13`, payload = chunk) + script
  `migrate_kb.py` al posto di `migrate_essences.py`. Non verificato in questa sessione.

## Analytics e reporting

Invariati nel meccanismo. Cambiano i campi:
- `evaluations`: `outcome`, `summary`, `friction_note`, `quote_requested` (bool).
- `reporting.py`: `total_sessions`, `outcomes`, `by_profile`, `by_category`, `by_format`,
  `quote_rate`, `duration`, `friction`, `top_topics` (da `session_topics`), `by_weekday`.
- Resoconto admin: sezioni Funnel, Dispositivi, Esiti, Profili/Categorie/Formati (barre),
  Topic, Settimana; testo esportabile con narrativa LLM limitata a `friction_text` e
  `recommendations`.
- Funnel JSONL: eventi `page_view`, `cta_click`, `chat_complete`, `quote_request`
  (sostituisce `add_to_cart`, senza taglie).

## Frontend

- `src/App.jsx`: route `/`, `/en`, `/testing`, `/privacy-policy` (testo segnaposto).
- `LandingPage` minima (titolo, una riga, toggle lingua, bottone Start).
- `Ritual` → **`Journey`**: `Conversation` + `LeadSummary` (sostituisce `Overview`: tabella
  dei campi di `lead_info`, nessun checkout).
- `Conversation`, `Chat`, `Message`, `UserInput`, `Retrieve` copiati; `general_info` →
  `lead_info`; stringhe brand in `translations.js` sostituite (chiavi identiche).
- Admin: `AdminShell` con Chat, Resoconto, Utenti; `ChatDetail` mostra l'evaluation con
  `quote_requested` al posto di `essence_modified`; `ChatList` filtra per stato e per profilo.
- Chiavi storage: `agent13_*`.

## Persistenza

`init_db.sql` riscritto pulito (niente storia di `ALTER TABLE`): `sessions` con
`profile`/`category`/`format`/`quote_requested`, `transcripts`, `evaluations` con
`quote_requested`, `session_topics (session_id, doc, created_at)`, `app_settings`.
Retention: `retention.py`/`retention.js` invariati salvo i nomi delle tabelle e l'assenza dei
record profumo (lato Node resta solo il JSONL analytics).

## Verifica end-to-end (in questa sessione)

1. `pip install -e backend[dev]`, `npm ci`.
2. Postgres 16 da apt, `init_db.sql` applicato.
3. `LLM_PROVIDER=mock RETRIEVAL_PROVIDER=keyword uvicorn main:app` + `node server/index.js`
   con `BACKEND_URL`, `ANALYTICS_LOG`, `ADMIN_USERS_FILE` su percorsi scrivibili.
4. Script `scripts/e2e-mock.sh`: guida con `curl` una conversazione completa (launch →
   profilo → categoria → formato → progetto → follow-up → domanda KB → richiesta preventivo →
   contatto → conferma) e verifica che l'ultimo `done` abbia `step=completed` e che
   `GET /chats/{id}` mostri transcript, costi e valutazione `done`.
5. Playwright (Chromium preinstallato) apre `/`, clicca Start, completa la stessa conversazione
   dalla UI e screenshotta la `LeadSummary`; login admin, apertura chat e Resoconto.
6. `cd backend && python -m pytest -q` e `npm test` verdi; `npm run build` ok.

## Rischi e punti aperti

- **Python 3.11 in locale, 3.12 in Docker**: il codice compila in 3.11; se in futuro entra
  sintassi 3.12 va alzata anche la baseline locale.
- **Docker non disponibile qui**: i compose vengono portati ma non eseguiti; da verificare sul
  VPS o in locale dal proprietario.
- **Il mock "supera" ogni validazione**: dimostra il cablaggio, non la qualità della
  conversazione. Prima verifica reale = `LLM_PROVIDER=openrouter` con i prompt segnaposto.
- **Lingue**: `_LANG_NAME` e `labels.py` restano a due colonne; estendere a es/sv è un lavoro
  separato (e senza copy approvato).
- **Compliance**: la disclosure AI Act in chat viene portata; l'informativa privacy è
  segnaposto e `docs/compliance*` non viene copiato: da rifare per il titolare 13 Protein.
