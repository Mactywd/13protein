# 13 Protein · agente AI

Agente conversazionale B2B per [13protein.com](https://13protein.com): qualifica
il progetto di chi cerca un produttore di integratori, risponde alle domande
usando il knowledgebase estratto dal sito e raccoglie la richiesta di preventivo.

**Stato: harness mock.** Lo stack gira end-to-end senza chiavi API e senza
servizi esterni, ma prompt, landing e informativa privacy sono segnaposto
dichiarati. Serve a costruirci sopra i flussi veri, non a essere pubblicato.

## Come gira

```
src/     React + Vite     chat, riepilogo del lead, pannello admin
server/  Express :3000    proxy SSE, login admin, analytics, retention su disco
backend/ FastAPI :8000    state machine, agent, prompt, retrieval, Postgres
```

Il knowledgebase (`knowledgebase/`) è generato dalla pipeline in `tools/` a
partire da un dump del sito. L'agente lo interroga in sola lettura.

## Avvio in locale

Serve Postgres 16, Node 22 e Python 3.11+.

```bash
psql postgresql://agent13:changeme@127.0.0.1/agent13 -f backend/scripts/init_db.sql
cd backend && pip install -e ".[dev]" && cd ..
npm ci
scripts/dev-local.sh
```

App su http://localhost:3000, admin su `/admin`. Con Docker: `./start.local.sh`.

## Verificare che funzioni

```bash
cd backend && python -m pytest -q     # test del backend
npm test && npm run lint              # test e lint lato Node
scripts/e2e-mock.sh                   # conversazione completa via HTTP
```

## Passare a un LLM vero

I due provider si scelgono da `backend/.env`, senza toccare il codice:

```
LLM_PROVIDER=openrouter          # invece di mock
OPENROUTER_API_KEY=...
RETRIEVAL_PROVIDER=qdrant        # invece di keyword
QDRANT_URL=http://localhost:6333
```

Con `RETRIEVAL_PROVIDER=qdrant` va popolato l'indice una volta sola
(`cd backend && python -m scripts.migrate_kb --recreate`): spende crediti
OpenRouter per gli embedding.

Prima di alzare il provider vero conviene riscrivere i 13 prompt in
`backend/agents/prompts/`: oggi chiedono esplicitamente risposte di esempio.

Il resto della documentazione, gotcha compresi, sta in `CLAUDE.md`.
