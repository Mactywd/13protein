# 13protein — agente AI

Agente conversazionale per **13protein.com**. Il knowledgebase è già stato estratto;
l'agente stesso non è ancora stato costruito.

## Cos'è davvero 13 Protein

Non vende integratori a consumatori né a palestre. È un **contract manufacturer B2B
europeo**: produce integratori per conto di altri brand. L'interlocutore dell'agente è
un'azienda che cerca un produttore, non chi compra proteine per allenarsi.

- Ragione sociale: 13 e Protein Import AB (Svezia) · attiva dal 1997
- Sede/stabilimento: Speditionsvägen 45, 142 50 Skogås · contatto pubblico: info@13protein.com
- Tre linee commerciali: **Private Label** (formula su misura), **White Label**
  (prodotti pronti a scaffale), **Rebranding** (formula e packaging pronti, spedizione 48-72h)
- 7 categorie prodotto: Protein Powders · Performance & Training · Health & Wellness ·
  Weight Management & Meal Solutions · Drinks, Shots & Gels · Stick Packs & Single Servings ·
  Skincare & Cosmetics
- Numeri dichiarati: la home e la About Us ne espongono **due set diversi**, non riconciliati.
  Home: 800+ materie prime a stock, 150+ formule custom, 10M+ unità/anno, 30+ paesi.
  About Us: 5 stabilimenti, 55K sqm di produzione, 4K+ prodotti sviluppati/anno, 400+ clienti
  B2B. Se l'agente cita numeri, deve dire da quale pagina vengono.

Il form contatti in `knowledgebase/site/forms.md` è di fatto il **flusso di qualificazione
lead** che il sito usa oggi (chi sei → cosa vuoi creare → formato preferito → descrizione
progetto). È il riferimento più utile per progettare la conversazione dell'agente.

## Struttura

```
proteitobu6d54as_bovu1.sql   sorgente, 1 GB — dump MySQL completo, NON committare
tools/sqldump.py             lettore streaming del dump .sql
tools/extract_raw.py         stage 1 — whitelist delle tabelle
tools/build_kb.py            stage 2 — markdown + bundle
knowledgebase/               output generato, 312 KB — NON modificare a mano
.cache/raw.json              intermedio, 5 MB — rigenerabile

backend/                     FastAPI: state machine, agent, prompt, servizi
server/                      Express: proxy SSE, admin, analytics, retention
src/                         React/Vite: chat cliente (src/) e admin (src/admin/)
scripts/                     avvio locale e verifiche end-to-end
docs/superpowers/            spec, piani ed evidenze delle verifiche
```

## Rigenerare il knowledgebase

```bash
python3 tools/extract_raw.py && python3 tools/build_kb.py
```

Stage 1 legge il dump da 1 GB (~2 min) e scrive `.cache/raw.json`. Stage 2 lavora solo sulla
cache ed è istantaneo: durante l'iterazione sull'estrattore serve rilanciare solo il secondo.
Nessuna dipendenza esterna, solo stdlib.

Stage 2 **svuota `pages/`, `products/`, `site/` prima di riscriverli**: senza questo, una
pagina che passa a bozza resterebbe come file orfano (è successo con `insights`).

Output: `knowledgebase/pages/*.md`, `products/*.md`, `site/*.md`, più due bundle —
`knowledgebase.md` (tutto in un file) e `knowledgebase.jsonl` (173 chunk a livello di
sezione, pronti per l'ingest).

## Com'è fatto il sorgente

Dump phpMyAdmin dell'intero database (76 tabelle, prefisso `uytw_`), con extended INSERT.
`sqldump.py` lo legge in streaming con una finestra scorrevole: **non** si può splittare su
`),(` né caricare uno statement intero in memoria — un solo `_elementor_data` arriva a 300 KB
e contiene sia `),(` sia `\n` dentro stringhe quotate.

Il prefisso `uytw_` è di questo export e cambia a ogni nuova installazione: sta in `PFX` in
cima a `extract_raw.py`, è l'unica cosa da toccare se arriva un dump da un altro sito.

6.608 dei 7.059 post sono revisioni. **Testo utile: ~300 KB su 1 GB.** Se un numero sembra
grande, quasi certamente stai contando revisioni.

I contenuti delle pagine stanno in `_elementor_data`; quelli delle 7 categorie prodotto **no**
— stanno in campi ripetitore ACF (`customization_options_list_N_testo`,
`list_format_and_packaging_N_testo`). Sono due percorsi di estrazione distinti in `build_kb.py`.

Elementor scrive anche `copied_media_ids` / `referenced_media_ids` su ogni pagina: sono liste
di ID, non contenuto — `ACF_SKIP` le scarta, altrimenti finiscono in coda a ogni pagina.

L'HTML dentro Elementor è CRLF e ha tag `<strong>` non chiusi: `html2md()` normalizza i line
ending e riequilibra gli asterischi per riga. Se aggiungi widget, aggiungi un handler in
`widget_md()` — il walk cattura le eccezioni per widget, quindi un widget rotto lascia una
nota `<widget ... non estratto>` invece di svuotare la pagina. Dopo ogni modifica:

```bash
grep -rn "non estratto\|errore parsing" knowledgebase/
```

## Dati personali

Il dump contiene submission di form con nomi/email/telefoni/IP (`uytw_e_submissions*`),
utenti WP con **hash delle password** (`uytw_users`, `uytw_usermeta`), log Wordfence con IP
e secret 2FA (`uytw_wf*`, `uytw_wfls_*`). Stage 1 lavora per **whitelist**, non per
esclusione: entra solo `posts`, `postmeta`, `options`, le tabelle di tassonomia e
`icl_languages`/`icl_translations`. Tutto il resto non viene nemmeno letto. Le email
non-`@13protein.com` vengono mascherate anche quando compaiono nella configurazione dei form.

`options` è a sua volta filtrato per nome (`OPT_KEEP` / `OPT_PREFIX` in `extract_raw.py`):
la tabella è il deposito di stato di tutti i plugin, compresi Wordfence e i login limiter.

Il knowledgebase generato è pulito — verificabile con:

```bash
grep -rhoE '[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}' knowledgebase/ | sort -u
```

Deve restituire solo `info@13protein.com`. Se estendi la pipeline ad altre tabelle, ricontrolla.

## Buchi noti nel contenuto

Da non colmare inventando: se l'agente deve rispondere su questi temi, servono informazioni
dal cliente.

- **Nessun prezzo, MOQ o lead time** in tutto il sito, tranne le 48-72h del Rebranding:
  ogni percorso finisce su un CTA "Get a Quote"
- **Certificazioni: solo nel footer, mai nel testo.** La pagina Quality parla genericamente di
  "internationally recognized standards"; i certificati veri sono linkati nel footer
  (`site/navigation.md`) — FSSC 22000 per i due stabilimenti (SKRUV e Skogås/Stockholm) e
  produzione biologica (Ekologisk Produktion). Esistono anche le Condizioni Generali
  White Label B2B in PDF.
- **I PDF non sono nel dump.** È un dump del database: `wp-content/uploads/` non c'è.
  Certificati, cataloghi e condizioni generali sono solo riferimenti in `site/media.csv`. Per
  metterne il contenuto nel knowledgebase servono i file veri dal cliente.
- **Blog ancora vuoto, ma ora pianificato**: i 10 post sono sempre la stessa copia placeholder
  Lorem ipsum "Our culture, our values". Sono però stati categorizzati (Product & formulation
  insights ×8, Market & brand strategy, Manufacturing & compliance, più i tag Brand building
  tips / Top in the community). Le tassonomie dicono su quali temi il cliente *vuole* parlare;
  non sono contenuto che l'agente possa citare.
- **Insights è tornato bozza** ed è sparito dal menu header/footer. Il file
  `pages/insights.md` è marcato `status: draft` — non è contenuto live.
- **WPML installato, contenuti non tradotti.** Sono attive 4 lingue (en, es, it, sv) ma
  esistono solo traduzioni dei nomi di categoria: pagine, prodotti e post stanno solo in `en`.
  Il sito è di fatto monolingua. Se l'agente deve rispondere in italiano o spagnolo, traduce
  lui — non c'è copy approvato dal cliente in quelle lingue.
- **Una sola scheda prodotto reale** (Vitamin C Effervescent Stick, con tabella nutrizionale);
  le 7 "categorie prodotto" sono pagine di capability, non SKU
- Il dump viene dallo staging `ai.13protein.tobugroup.com` (non più `13protein.tobugroup.com`):
  gli URL interni e quelli dei PDF puntano lì, non a `13protein.com`
- Su staging restano pubblicate o in bozza 7 copie superate della home (`home-500`,
  `home-old`, `home-old-1..5`). La pipeline le esclude (`LEGACY` in `build_kb.py`): sono
  duplicati del copy della home e sporcherebbero l'indice di retrieval.

---

# Agente: harness mock

L'agente **esiste ma è tutto segnaposto**: gira end-to-end senza chiavi né
servizi esterni, così che i prompt e i flussi veri si possano scrivere sopra
qualcosa che già funziona. Spec e piano stanno in `docs/superpowers/`
(`specs/2026-09-09-mock-harness-design.md`, `plans/2026-09-09-mock-harness.md`);
`docs/analisi-alchimista.md` spiega da dove viene ogni pezzo.

La base è la repo `Mactywd/alchimista_ndc`, de-brandizzata. Da lì viene tutta
l'infrastruttura generica; il dominio (profumi) è stato riscritto.

## Architettura

Tre livelli su singola origine, così il browser parla con un host solo:

```
src/     React 19 + Vite      chat, landing, riepilogo lead, pannello admin
server/  Express :3000        proxy SSE, login admin, analytics JSONL, retention su disco
backend/ FastAPI :8000        state machine, agent, prompt, retrieval, Postgres
```

Il client non parla mai col backend Python: passa sempre da `/api/*` sul Node.

## Ciclo di un turno

`POST /api/chat` → `POST /chat` → `main.chat()`:

1. **Prima transazione breve**: carica `SessionState` da `sessions.state`.
2. `router.dispatch(state.current_step)` sceglie l'handler. L'handler è un
   `async def handle(state, message) -> AsyncIterator[Event]`: muta lo stato e
   produce eventi, che vengono serializzati in SSE mentre escono.
3. **Seconda transazione breve**: salva stato, transcript, costi, `session_topics`.

Le due transazioni sono brevi **apposta**: le chiamate LLM possono durare
decine di secondi e una connessione tenuta aperta per tutto il turno esaurisce
il pool sotto carico. Gli handler non toccano mai la connessione.

**La state machine è esplicita**: il modello scrive il testo, non decide mai la
transizione. Chi decide è l'handler, e il passo successivo arriva al client
nell'evento `done`.

## Flusso della conversazione

Ricalca il form contatti del sito (`knowledgebase/site/forms.md`), che è il
flusso di qualificazione lead che 13 Protein usa oggi:

| Step | Cosa fa | Input |
|---|---|---|
| `intro` | saluto e bottoni dei profili | bottoni |
| `profile_select` | salva il profilo, mostra le categorie | bottoni |
| `category_select` | card della categoria dal knowledgebase, mostra i formati | bottoni |
| `format_select` | apre la descrizione del progetto | testo |
| `project_input` | valida, al massimo 2 rilanci, poi riassume | testo |
| `qa` | domande libere con retrieval, o richiesta preventivo | testo + bottone |
| `contact_input` | nome, azienda, e-mail | testo |
| `contact_confirm` | riepilogo e conferma | bottoni |
| `completed` | emette `lead_info` | — |

I **valori** dei bottoni sono gli slug inglesi del form del sito
(`product_idea`, `proteins`, `powders`, …): le etichette IT/EN vivono solo in
`backend/lib/labels.py`. Il backend salva sempre il valore.

## Contratto SSE

| evento | dati | significato |
|---|---|---|
| `text` | `{token}` | un pezzo di testo in streaming |
| `buttons` | `{buttons: [{label, value}]}` | scelte cliccabili |
| `carousel` | `{cards: [{title, image, description, value}]}` | card della categoria |
| `message_break` | `{}` | chiude la bolla senza chiudere il turno |
| `error` | `{message}` | il turno è fallito, testo già localizzato |
| `lead_info` | `{info}` | l'oggetto finale del lead |
| `done` | `{step, input_enabled}` | fine turno, passo corrente, input abilitato |

`lead_info` (l'oggetto che arriva al team):

```json
{"profile":"product_idea","category":"proteins","format":"powders",
 "projectDescription":"…","questionsAsked":["…"],"topicsCited":["quality"],
 "quoteRequested":true,"contact":{"name":"…","company":"…","email":"…"},
 "language":"en"}
```

## Prompt

`backend/agents/prompts/<slug>.txt`, caricati **solo** da
`agents.prompts.load(slug, **placeholder)`, che prepende un header condiviso
(brand, pubblico B2B, tono, divieto di inventare prezzi/MOQ/certificazioni) e
riempie i `{placeholder}` con `str.replace` — non `str.format`, così una graffa
spuria nel testo non rompe niente.

La prima riga del prompt caricato è sempre `# Prompt: <slug>`: innocua per un
LLM vero, **indispensabile** per il provider mock, che sceglie da lì la
risposta. Regole di scrittura in `agents/prompts/LINEEGUIDA.md`; i placeholder
si verificano con `python -m scripts.check_prompt_placeholders <slug> '{a},{b}'`
(le graffe vanno passate, il confronto è sulla stringa intera).

## Provider LLM e retrieval

Due seam, entrambi con default che non richiedono credenziali:

- `services/llm.py` → `mock` (default) o `openrouter`. Il mock
  (`services/llm_mock.py` + `data/mock_llm.json`) risponde per slug, con tre
  regole dinamiche che servono solo a far avanzare la macchina a stati:
  `validate_project` (insufficiente al primo giro), `extract_contact` (regex
  sull'e-mail), `qa_answer` (cita i titoli dei chunk ricevuti).
- `services/retrieval.py` → `keyword` (default) o `qdrant`. L'indice keyword sta
  in memoria sui **171 chunk live** di `knowledgebase.jsonl` (173 meno le 2
  bozze di `insights`). Confronta le parole per **radice troncata a 5
  caratteri**: senza, "are you certified" non trova la pagina Quality, che
  scrive "certification".

**Gotcha già inciampato**: il mock leggeva la lingua cercando `italian` in tutto
il system prompt, e ogni prompt conversazionale ha una sezione `## Italian` fra
gli esempi. Risultato: ogni conversazione in inglese rispondeva in italiano. Ora
`lang_of` guarda solo la sezione `# Language`.

## Analytics

Tre livelli, separati apposta:

1. **Per turno**: costo e token accumulati in un contextvar
   (`services/usage.py`) e scritti sulla riga di transcript. Un turno senza
   bolle visibili non può attaccare il costo a una riga invisibile: lo parcheggia
   in `state.pending_*` e lo attribuisce al primo turno visibile successivo.
2. **Per conversazione**: `agents/evaluation.py` gira in background alla
   chiusura e scrive un JSON strutturato (esito, riassunto, attrito, preventivo).
   Il prompt impone la minimizzazione: niente nomi, aziende o e-mail nel riassunto.
3. **Per periodo**: `reporting.py` calcola **ogni numero in SQL**; l'LLM
   (`report_agents.py`) scrive solo i giudizi e ha il divieto esplicito di
   produrre cifre. Il testo esportabile si compone in JS
   (`src/admin/modules/resoconto/reportText.js`).

Il funnel (page_view, cta_click, chat_complete, quote_request) è un JSONL su
disco letto dal Node: nessun IP, nessuno user-agent, solo un id casuale di
visitatore e due etichette grossolane di dispositivo e browser.

## Admin

`/admin`, token HMAC in `sessionStorage` (12h), permessi per modulo:
`chat`, `resoconto`, `user-management`. Gli utenti stanno in un file JSON con
password in scrypt; si creano da CLI, non da variabili d'ambiente:

```bash
node server/scripts/create-admin.js <username>   # password minimo 8 caratteri
```

`/testing` è la stessa chat dietro login, con le sessioni marcate
`is_testing` (escluse da ogni statistica) e un pulsante "Salta conversazione"
che completa il lead con i facsimili di `backend/data/testing_facsimiles.json`.

## Girare in locale

Senza Docker (è quello che usa la verifica end-to-end):

```bash
service postgresql start
sudo -u postgres psql -c "CREATE USER agent13 WITH PASSWORD 'changeme';" \
                     -c "CREATE DATABASE agent13 OWNER agent13;"
psql postgresql://agent13:changeme@127.0.0.1/agent13 -f backend/scripts/init_db.sql
scripts/dev-local.sh          # backend :8000, node :3000, admin tester/tester-13protein
scripts/dev-local.sh --stop
```

Con Docker: `./start.local.sh` (Qdrant è nel profilo `qdrant`, spento di
default). **I compose non sono mai stati eseguiti**: in questa sessione non
c'era un daemon Docker, sono stati solo validati con `docker compose config`.

## Test

```bash
cd backend && python -m pytest -q     # 191 test, tutto mockato: niente DB, niente LLM
npm test                              # vitest: solo lib e route pure, nessun test di componenti
npm run lint
scripts/e2e-mock.sh [it]              # sequenza fissa via HTTP, controlla gli eventi SSE
npm i --no-save playwright && node scripts/e2e-ui.mjs   # stessa sequenza cliccando, + screenshot
```

Playwright **non** è una dipendenza del progetto: il suo postinstall
scaricherebbe un browser dentro l'immagine Docker. Lo script usa il Chromium
già presente in `/opt/pw-browsers`.

Convenzioni: i test del backend fanno monkeypatch su `main.db.transaction`,
`main.session.load/save` e sugli agent; non esiste un Postgres nei test. Lato
Node niente jsdom, quindi la logica che merita un test sta in funzioni pure
fuori dai componenti (`filters.js`, `reportText.js`, `retention.js`).

## Cos'è segnaposto

Da riscrivere quando saranno definiti i compiti veri dell'agente:

- **I 13 prompt** in `backend/agents/prompts/`: dicono esplicitamente di
  rispondere con dati di esempio.
- **`backend/data/mock_llm.json`**: le risposte deterministiche del mock.
- **`backend/data/testing_facsimiles.json`**: i lead di esempio del pulsante Salta.
- **La landing** (`src/components/LandingPage/`): una schermata sola, il minimo
  per entrare in chat.
- **L'informativa privacy** (`src/components/PrivacyPolicy/`): è un'ossatura, non
  un'informativa. Va redatta con il titolare **prima** di rendere l'assistente
  raggiungibile da chiunque. `public/robots.txt` blocca tutti i crawler finché
  è così.
- **I termini di retention** (24 mesi ovunque): non decisi, quindi il purge gira
  in **dry run** su entrambe le metà (Postgres e JSONL). Accenderlo richiede sia
  i termini sia la sezione corrispondente nell'informativa.
- **Le traduzioni italiane** (`src/i18n/translations.js`): il sito è di fatto
  monolingua inglese, l'italiano lo scriviamo noi.
- **Il tema grafico**: colori e spaziature vengono dall'Alchimista, mai ridisegnati.
