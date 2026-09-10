# Analisi di `Mactywd/alchimista_ndc` come base per l'agente 13protein

> Implementato come harness mock: vedi la spec del 2026-09-09 in
> `docs/superpowers/specs/` e il piano in `docs/superpowers/plans/`.

Data: 2026-09-09 · Commit analizzato: `12ffcac` (branch `master`) · Repo clonata in sola lettura, nessuna modifica.

Scopo: capire come è fatto l'Alchimista (agente conversazionale di Note del Chianti che compone
profumi) per usarlo come **harness** dell'agente 13protein, de-brandizzandolo. Questo documento è
la fotografia; la decisione su cosa tenere / scartare / riscrivere è il passo successivo.

---

## 1. Cos'è, in breve

Chat a step guidati (bottoni + testo libero) che porta l'utente dalla scelta di un percorso
(Memoria / Essenza / Fragranza) alla selezione di 4-5 essenze da un catalogo vettoriale, fino a
nome del profumo e checkout. Nato su Voiceflow, **riscritto nativo** (FastAPI + Postgres + Qdrant)
tra giugno e luglio 2026. In produzione su `atelier.notedelchianti.com`.

Numeri utili:

| Cosa | Quanto |
|---|---|
| Backend Python (senza test) | ~4.300 righe, 8 handler, 11 moduli agent |
| Prompt `.txt` | 52 file, ~19.300 parole totali |
| Step della state machine | 32 valori enum, 26 con handler |
| Test backend (pytest) | 275 funzioni di test in 47 file |
| Test Node/frontend (vitest) | 25 file |
| Documentazione di design | 30 spec + 30 piani in `docs/superpowers/` |

---

## 2. Architettura a tre livelli, singola origine

```
Browser (React/Vite SPA, src/)
   │  POST /api/chat  {session_id, message, default_language, is_testing}   ← SSE
   ▼
Node/Express (server/, :3000)         serve dist/, proxy /api/*, rate limit, admin auth,
   │  POST $BACKEND_URL/chat            recipe store JSON, analytics JSONL, adattatore shop
   ▼
Python FastAPI (backend/, :8000)      state machine per step, agenti LLM, SSE nativo
   ├─ Postgres   sessions / transcripts / evaluations / session_essences / app_settings
   ├─ Qdrant     collection `essenze` (embedding text-embedding-3-small via OpenRouter)
   └─ OpenRouter LLM (default google/gemma-4-26b-a4b-it:nitro) + perplexity/sonar per web search
```

Deploy: `docker-compose.atelier.yml` (app + backend + postgres + qdrant) dietro Traefik; due VPS
(staging / prod) distinti solo per `DOMAIN`. `docker-compose.yml` e `docker-compose.prod.yml` in
root sono **residui Voiceflow**, non usati da nessuno script.

---

## 3. Mappa delle cartelle

| Percorso | Ruolo | Brand-specifico? |
|---|---|---|
| `backend/main.py` | App FastAPI: `/chat` (SSE), `/chats`, `/settings`, `/report`, `/reset`, `/chat/{id}/skip`, `/health`; loop di sweep abbandoni e purge retention | in parte (session_essences, general_info) |
| `backend/models.py` | `Step` enum, `SessionState` (pydantic, serializzato JSONB), dataclass degli eventi SSE, `to_general_info()` | **sì**: quasi tutti i campi sono profumo |
| `backend/router.py` | `HANDLERS: dict[Step, handler]` + `dispatch(step)` | no (pattern), sì (tabella) |
| `backend/handlers/*.py` | Un modulo per fase del flusso; ogni handler è `async gen(state, message) -> Event` | **sì**, tutti |
| `backend/agents/*.py` | Wrapper sottili: carica prompt, chiama OpenRouter, parsa output | sì, ma il pattern è generico |
| `backend/agents/prompts/` | 52 prompt `.txt` + `__init__.py` (loader) + `LINEEGUIDA.md` | testi sì, **loader e linee guida no** |
| `backend/services/openrouter.py` | `stream`, `complete`, `complete_structured`, `web_complete`; chiave di fallback; retry | no (solo `HTTP-Referer` e modello default) |
| `backend/services/usage.py` | Accumulatore costi/token per richiesta via `contextvars` | no |
| `backend/services/qdrant.py` | `embed` + `search` con filtro `must_not` e fallback su catalogo statico | no, salvo nome collection e chiavi payload |
| `backend/services/exposure.py` | Re-rank per esposizione (essenze poco mostrate salgono) | sì |
| `backend/services/db.py` | Pool asyncpg + context manager `transaction()` | no |
| `backend/session.py`, `transcripts.py` | Load/save stato JSONB; append di coppia user/assistant con payload e costi | quasi no (colonne path/subpath/delegate) |
| `backend/chats.py` | Query per l'admin chat: lista, dettaglio, sweep abbandoni, `messages_from_row` | no, salvo le etichette di stato |
| `backend/reporting.py`, `report_agents.py` | Aggregazioni SQL del Resoconto + narrativa LLM sui numeri già calcolati | metà: pattern generico, metriche di dominio |
| `backend/agents/evaluation.py` | Valutazione post-chat in background (JSON strutturato) | prompt sì, meccanismo no |
| `backend/retention.py` | Purge GDPR a due termini (contenuto / riga sessione), dry run | no |
| `backend/testing_env.py` + `data/testing_facsimiles.json` | "Salta conversazione" per i tester | sì |
| `backend/lib/labels.py` | Bottoni canonici (valore IT) + etichette IT/EN | sì |
| `backend/scripts/` | `init_db.sql`, `migrate_essences` (ingest Qdrant), `check_prompt_placeholders`, `preview_prompts`, `purge_expired`, `extract_prompts` (congelato) | misto |
| `backend/tests/` | 275 test, tutto mockato (nessun DB/LLM reale) | seguono i moduli |
| `server/index.js` | Express: header sicurezza, CORS, rate limit, route, SPA fallback, error handler | no |
| `server/routes/chat.js` | Proxy SSE con watchdog idle 120 s e heartbeat | no |
| `server/routes/track.js` + `lib/analytics.js` + `lib/segments.js` | Eventi funnel su JSONL append-only, whitelist device/browser, niente IP/UA | no (solo la lista eventi) |
| `server/routes/report.js` | `computeFunnel` da JSONL + merge con `/report` del backend | metà |
| `server/lib/admin-auth.js`, `admin-users.js`, `routes/admin-users.js` | Login HMAC, token 12h, utenti su JSON con scrypt, permessi per modulo | no |
| `server/lib/rate-limit.js`, `lib/id.js`, `lib/retention.js` | Sliding window in memoria; id casuali; purge dei file su disco | no |
| `server/lib/recipe-store.js`, `recipe.js`, `purchase.js`, `essence-numbers.js`, `shop/*`, `routes/perfume*.js`, `create-cart.js` | Record profumo, foglio dosi, PrestaShop/Shopify | **sì**, tutto e-commerce |
| `src/api/Retrieve.jsx` | Client SSE: traduce gli eventi nel contratto `eventHandlers` | no |
| `src/components/{Conversation,Chat,Message,UserInput}` | UI chat: streaming token con rAF, bottoni, carosello, typing indicator, gating input | no (CSS e copy sì) |
| `src/components/{LandingPage,Overview,Checkout,Ritual,PurchasePage,EmailPopup,PrivacyPolicy}` | Landing editoriale, riepilogo profumo, checkout | **sì** |
| `src/admin/*` | Shell admin con router, moduli Ricette / Chat / Resoconto / Utenti, grafici Recharts | Chat, Utenti, shell: no · Ricette: sì · Resoconto: metà |
| `src/contexts/LanguageContext.jsx`, `src/i18n/translations.js` | Lingua dal prefisso URL `/en`, dizionario IT/EN | pattern no, contenuto sì |
| `docs/superpowers/` | Spec + piani per ogni feature (metodo spec → plan → implement) | storico |
| `docs/compliance*` | Checklist GDPR/AI Act (692 righe) + tre ricerche | in gran parte riusabile |
| `backend/docs/` (`agents/`, `diagrams/`, `functions/`, `variables.md`) | Documentazione **dell'export Voiceflow**, era pre-riscrittura | storico, solo consultazione |
| `alchimista.json` (1,5 MB), `kb.json`, `log.txt`, `netlify.toml`, `deno.lock`, `*.png` in root | Export Voiceflow, catalogo essenze, log, residui Netlify | da non portare |
| `README.md`, `HANDOFF.md`, `NETLIFY_SETUP.md` | **Obsoleti**: descrivono ancora Voiceflow + Netlify | da non portare; l'unica fonte aggiornata è `CLAUDE.md` |

---

## 4. Il ciclo di un turno (ricezione domanda → invio risposta)

1. **Browser** — `Conversation.jsx` genera un `session_id` (`<env>_<random>_<timestamp>`), chiama
   `Retrieve.conversationInit(lang)` al mount (messaggio vuoto = launch) e
   `sendTextRequest(text)` a ogni invio. Un click su bottone/carta invia `payload.sendValue`
   (valore canonico backend) mostrando la label localizzata.
2. **Node** — `server/routes/chat.js` valida `session_id`, inoltra a `$BACKEND_URL/chat`, ricopia
   i byte SSE così come arrivano. Watchdog **idle** (abortisce solo dopo 120 s di silenzio, mai
   a metà di un turno lungo), heartbeat `: heartbeat` ogni 5 s per i proxy, `reader.cancel()` se
   il client chiude.
3. **FastAPI** — `main.py::chat()`:
   - tronca il messaggio a 2.000 caratteri;
   - apre una **transazione breve** solo per `session.load()`, poi la rilascia (mai una
     connessione tenuta aperta durante lo streaming LLM);
   - `router.dispatch(state.current_step)` → handler; l'handler è un async generator che
     **muta `state` e produce eventi**; `stream.format_sse(event)` li serializza;
   - accumula il testo (`TextEvent.token`) e il sentinel `\x1e` per `MessageBreakEvent`, raccoglie
     l'ultimo carosello/bottoni con `collect_payload`;
   - a fine stream: seconda transazione per `session.save`, `transcripts.append` (una riga user +
     una assistant con payload, costo, token, modello), `chats.add_usage`, `mark_completed`;
   - **usage carry-forward**: se il turno non ha prodotto bolle visibili, il costo è parcheggiato
     su `state.pending_*` e attribuito al primo turno visibile successivo;
   - qualunque eccezione → evento `error` localizzato; la transazione di scrittura non parte,
     quindi nessun turno "a metà" viene persistito e il client può reinviare in sicurezza;
   - se lo step diventa `COMPLETED`, `asyncio.create_task(run_evaluation(session_id))`.
4. **Contratto SSE** (`backend/stream.py` ↔ `src/api/Retrieve.jsx`):

   | evento | payload | effetto lato client |
   |---|---|---|
   | `text` | `{token}` | apre/accoda alla bolla corrente |
   | `buttons` | `{buttons:[{label,value}]}` | chiude la bolla, mostra scelte |
   | `carousel` | `{cards:[{title,image,description,value}]}` | chiude la bolla, mostra carte |
   | `message_break` | `{}` | chiude la bolla e rimostra il typing indicator |
   | `error` | `{message}` | testo statico |
   | `general_info` | `{info}` | oggetto finale strutturato (una sola volta) |
   | `done` | `{step, input_enabled}` | fine turno; **gating della textbox**; `step=completed` chiude la chat |

5. **Handler tipo** (`handlers/intro.py`): stream del prompt → `TextEvent` per token →
   `ButtonsEvent(labels.buttons("gender", lang))` → `state.current_step = Step.GENDER_SELECT` →
   `DoneEvent(step, input_enabled=False)`. Tutto il flusso è **esplicito e deterministico**: il
   LLM genera il testo, non decide la transizione (le uniche decisioni LLM sono validatori e
   classificatori con output JSON o parola singola).

---

## 5. Cartella dei prompt

- `backend/agents/prompts/<slug>.txt`, uno per chiamata LLM; caricati da
  `agents.prompts.load(slug, **placeholders)`:
  - `_HEADER` (~90 token) **prepeso a ogni prompt**: brand, audience, tono, divieto di em dash,
    regola sui temi sensibili (mitigazione GDPR art. 9). Unico chokepoint per regole globali.
  - placeholder `{nome}` riempiti con `str.replace` (non `str.format`), quindi graffe spurie nel
    testo non rompono nulla; `lru_cache` sul file.
- `LINEEGUIDA.md`: struttura del file (sezioni `# Role / ## Task / ## Requirements / ## Examples /
  # Language / # Input`, bullet con keyword in grassetto, esempi per lingua) e struttura
  dell'output conversazionale (scansionabile, bullet `•`, grassetti, una CTA). I prompt di
  estrazione (`extract_*`, `parse_*`, `filter_*`, validator) restano dati strutturati.
- Convenzione di lingua: `default_language` passa come nome esteso (`italian` / `english`),
  mappato in ogni modulo agent da `_LANG_NAME`.
- Tooling: `check_prompt_placeholders.py` (set di placeholder atteso + conteggio parole),
  `preview_prompts.py` (esegue i wrapper reali con fixture e segnala paragrafi lunghi / assenza
  di grassetto), `extract_prompts.py` (**congelato**: rilanciarlo sovrascriverebbe i prompt
  ottimizzati con l'export Voiceflow).
- Pattern di chiamata (`agents/*.py`): `stream(system, user)` per il conversazionale,
  `complete()` per parola singola / JSON array parsato con regex, `complete_structured()` per
  JSON (`response_format: json_object`, strip dei fence, un retry).

---

## 6. Servizi LLM e retrieval

- `openrouter.py`: base URL fissa, `usage:{include:true}` su ogni chiamata (alimenta
  `usage.record`), chiave primaria + **fallback** su 401/402/429, retry singolo su 5xx/rete,
  timeout 60 s. `web_complete` usa un modello con ricerca web (`perplexity/sonar`) per la
  piramide olfattiva di profumi esterni. Nessun `provider`/`user` inviato (scelta di compliance).
- `usage.py`: `ContextVar` per richiesta; `record()` è no-op fuori da un contesto, quindi test e
  job non richiesti non sporcano nulla.
- `qdrant.py`: embedding via OpenRouter, ricerca REST su collection `essenze` con
  `must_not` sui nomi in blacklist; su errore **fallback loud** (log exception) al catalogo JSON.
- `exposure.py`: re-rank stabile per "esposizione storica" (dominio profumi, ma l'idea di
  bilanciare i risultati mostrati è generica).

---

## 7. Analytics, valutazione e reporting (tre strati)

1. **Per turno** (`main.py` + `transcripts` + `sessions`): costo, token, modello per ogni bolla
   assistente; totali per sessione; `payload` JSONB per riprodurre fedelmente bottoni/caroselli
   in admin (`chats.messages_from_row`).
2. **Per conversazione** (`agents/evaluation.py`): a `completed` o ad abbandono (sweep ogni 60 s
   con timeout configurabile in `app_settings`, saltato se `path IS NULL`), un LLM legge tutto il
   transcript e produce JSON `{outcome, path_summary, problem, essence_modified}` salvato in
   `evaluations`, costo incluso nel totale sessione. Il prompt impone la **minimizzazione**
   (niente nomi, luoghi, dati sensibili nel riassunto, che vive più a lungo del transcript).
3. **Per periodo** (`reporting.py` + `report_agents.py` + Node `report.js`): SQL puro per esiti,
   performance per percorso, durata mediana/media, frizioni (note libere, cap 100), top essenze,
   giorno della settimana; funnel da JSONL (page_view → cta_click → chat_complete → add_to_cart,
   per visitatore unico, segmenti device/browser). La narrativa LLM riceve le statistiche e
   scrive **solo giudizi e raccomandazioni**: ogni numero del report è stampato dal client
   (`buildReportText`), mai dal modello. `?narrative=false` dà la parte deterministica senza
   costi LLM per l'aggiornamento istantaneo.

Tracking client (`src/utils/track.js`): `visitor_id` in localStorage, flag `testing` dalla route,
`keepalive:true`; il server risponde 204 prima di scrivere. Nessun IP né user-agent grezzo.

---

## 8. Persistenza

- **Postgres** (`backend/scripts/init_db.sql`, idempotente, applicato solo su volume nuovo):
  `sessions` (stato JSONB + colonne di reporting denormalizzate ad ogni save), `transcripts`,
  `evaluations`, `session_essences`, `app_settings`.
- **File JSON** (Node): record profumo in `RECIPES_DIR` con indice in memoria per sessione;
  utenti admin con scrypt in `ADMIN_USERS_FILE`; segreto HMAC autogenerato.
- **JSONL** append-only per gli eventi analytics.
- **Qdrant** per il catalogo; **niente** dati personali nel payload.

---

## 9. Admin, sicurezza, compliance

- Admin unificato a `/admin` (secondo entry Vite): login → token HMAC-SHA256 firmato con
  scadenza 12 h in `sessionStorage`; `authFetch` inietta il bearer e su 401 torna al login;
  `requirePerm(perm)` lato Node (`ricette` / `chat` / `resoconto` / `user-management`).
  Primo superuser da CLI, gli altri dalla tab Utenti.
- Rate limit per IP su tutte le route pubbliche; header di sicurezza; CORS `*` (annotato come
  da restringere); `trust proxy`.
- `/testing`: stesso sito, dietro login admin, sessioni marcate `is_testing` (sticky) ed escluse
  da ogni statistica; bottone "Salta conversazione" che completa la sessione con un facsimile.
- Retention GDPR su entrambi i runtime (Python: transcript + scrub dello stato, poi riga
  sessione; Node: JSONL, record, transcript legacy), termini via env in una sola `.env` di root,
  dry run disponibile, log di soli conteggi.
- AI Act art. 50.1: disclosure "stai parlando con un'IA" persistente sotto l'input della chat.
- `docs/compliance-checklist.md` è il registro vivo delle decisioni (L*/C*/F*).

---

## 10. Test e metodo di lavoro

- `cd backend && python -m pytest -q`: tutto mockato (OpenRouter, DB), test per handler,
  agent, stream, router, reporting, retention, loader prompt.
- `npm test` (vitest): librerie Node (auth, users, rate-limit, retention, shop, recipe) e le
  poche logiche pure del frontend; nessun test di componente (niente jsdom).
- Ogni feature ha spec + piano in `docs/superpowers/` e `CLAUDE.md` viene aggiornato nello
  stesso commit: è il **documento di verità** del progetto (220 righe dense, incluse le
  "gotcha" CSS/mobile).

---

## 11. Dove il brand è cablato nel codice (da toccare per de-brandizzare)

- `agents/prompts/__init__.py::_HEADER` (nome brand, tono) e tutti i 52 prompt.
- `models.py` (`Step`, `SessionState`, `to_general_info`), `router.py`, `handlers/*`,
  `agents/*`, `lib/labels.py`, `services/exposure.py`, `testing_env.py` + facsimili.
- Stringhe statiche negli handler: `COMING_SOON`, `CAROUSEL_ERROR`, messaggio di
  `handle_completed`; `_STREAM_ERROR_MESSAGE` in `main.py` (solo IT/EN).
- `services/openrouter.py`: `HTTP-Referer: https://notechianti.it`, `DEFAULT_MODEL`.
- `services/qdrant.py`: `COLLECTION = "essenze"`, chiave payload `nome`, catalogo di fallback.
- `init_db.sql`: `session_essences`, colonne `path` / `fragrance_subpath` / `delegate_used`;
  `session.py::save` le scrive.
- `reporting.py` / `report_summary.txt` / `evaluation.txt`: metriche di dominio.
- Node: tutto `recipe*`, `perfume*`, `create-cart`, `shop/`, `essence-numbers`; nomi
  `alchimista_*` in sessionStorage/localStorage; loghi in `src/admin/AdminShell.jsx`.
- Frontend: landing, Overview, Checkout, Ritual, translations, CSS, `public/`.
- Infra: `nginx.conf`, nomi progetto nei compose, script `start.*.sh`, dominio.

---

## 12. Proposta preliminare di classificazione (da discutere insieme)

**Tenere così com'è (infrastruttura generica, testata):** `services/openrouter.py`,
`services/usage.py`, `services/db.py`, `stream.py` + eventi in `models.py`, il ciclo di
`main.py::chat()` (transazioni brevi, carry-forward, error event), `session.py`,
`transcripts.py`, `chats.py`, `retention.py`, `prompts/__init__.py` + `LINEEGUIDA.md` +
`check_prompt_placeholders.py` + `preview_prompts.py` (con registry nuovo), `server/index.js`,
`server/routes/chat.js`, `rate-limit.js`, `admin-auth.js`, `admin-users.js`, `analytics.js`,
`segments.js`, `track.js`, `id.js`, `Retrieve.jsx`, `Conversation/Chat/Message/UserInput`,
`AdminShell` + moduli Chat e Utenti, `LanguageContext`, compose atelier/local, Dockerfile,
`init_db.sql` (parte generica), suite di test corrispondenti.

**Tenere il pattern, riscrivere il contenuto:** `models.py::SessionState` e `Step`, `router.py`,
`handlers/`, `agents/`, `labels.py`, tutti i prompt, `_HEADER`, `evaluation.py` + prompt,
`reporting.py` + `report_summary.txt` + sezioni Resoconto, `qdrant.py` (collection e schema
payload sul knowledgebase 13protein), `migrate_essences.py` → ingest di
`knowledgebase.jsonl`, `translations.js` (e lingue: 13protein ne vuole 4), `testing_env.py`.

**Scartare:** tutto l'e-commerce Node (`recipe-store`, `recipe`, `purchase`, `essence-numbers`,
`shop/`, `perfume*`, `create-cart`, script di migrazione legacy), `Overview`, `Checkout`,
`Ritual`, `PurchasePage`, `EmailPopup`, la landing e i suoi asset, modulo admin Ricette,
`exposure.py`, `alchimista.json`, `kb.json`, `log.txt`, `netlify.toml`, `deno.lock`,
`README.md`/`HANDOFF.md`/`NETLIFY_SETUP.md` (obsoleti), `docker-compose.yml`/`.prod.yml` in
root, `nginx.conf`, `backend/docs/` (Voiceflow), `docs/superpowers/` (storico, magari solo
come riferimento di metodo), immagini in `public/`.

**Da valutare:** `PrivacyPolicy` e `docs/compliance*` (la struttura è riusabile, il contenuto è
da rifare per il titolare 13 Protein), la disclosure AI Act in chat (da tenere), `/testing` con
skip (utile, ma i facsimili vanno rifatti), il Resoconto (quali KPI ha senso misurare per un
agente B2B di qualificazione lead).

---

## 13. Spunti per l'infrastruttura custom sopra l'harness

Annotazioni per la discussione, non decisioni.

- La state machine è **rigida per costruzione** (uno step → un handler → transizione fissa).
  Per 13protein serve probabilmente un ibrido: un flusso guidato per la qualificazione lead
  (il form in `knowledgebase/site/forms.md` è già lo scheletro: chi sei → cosa vuoi creare →
  formato → descrizione) **più** uno step "libero" con retrieval sul knowledgebase per le
  domande aperte (categorie, linee Private/White Label/Rebranding, certificazioni, numeri con
  citazione della pagina). Il pattern handler/eventi regge entrambi.
- Qdrant + `qdrant.py` sono pronti per ospitare i 173 chunk di `knowledgebase.jsonl`; cambiano
  collection, schema payload e query. `exposure.py` non serve.
- `general_info` diventa un **oggetto lead** (azienda, ruolo, linea commerciale, categoria,
  formato, descrizione progetto, lingua, email se raccolta): la persistenza su `sessions.state`
  e le colonne denormalizzate per il reporting seguono lo stesso schema.
- Lingue: oggi IT/EN con `_LANG_NAME`, `labels.py` a due colonne e `translations.js`. 13protein
  è monolingua EN con WPML attivo su 4 lingue senza traduzioni: da decidere se l'agente
  risponde nella lingua dell'utente (traducendo lui) o solo in EN.
- Il layer di valutazione post-chat e il Resoconto sono il punto di forza da conservare:
  cambiano solo i campi (esito: lead qualificato / informativo / abbandonato; frizioni;
  categorie richieste; linea commerciale).
- Buchi noti del knowledgebase (prezzi, MOQ, lead time, certificati solo nel footer, PDF
  assenti) vanno codificati nel `_HEADER` o in un prompt di "cosa non inventare": è l'analogo
  della regola sui temi sensibili già presente.
