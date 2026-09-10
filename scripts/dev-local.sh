#!/bin/bash
# Avvia lo stack in locale senza Docker: backend FastAPI su :8000 e server Node
# su :3000, con provider mock e retrieval a parole chiave. Serve alla verifica
# end-to-end (scripts/e2e-mock.sh, scripts/e2e-ui.mjs).
#
#   scripts/dev-local.sh          # build del frontend, avvio, attesa dell'health
#   scripts/dev-local.sh --stop   # ferma quello che ha avviato
#
# Presuppone un Postgres raggiungibile su 127.0.0.1:5432 con utente/database
# agent13 e lo schema già applicato:
#   psql -h 127.0.0.1 -U agent13 -d agent13 -f backend/scripts/init_db.sql
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
RUN_DIR="$ROOT/.dev"
mkdir -p "$RUN_DIR" data/analytics data/admin

stop() {
  for name in backend node; do
    pidfile="$RUN_DIR/$name.pid"
    if [ -f "$pidfile" ]; then
      kill "$(cat "$pidfile")" 2>/dev/null || true
      rm -f "$pidfile"
    fi
  done
  echo "Fermati."
}

if [ "${1:-}" = "--stop" ]; then stop; exit 0; fi
stop >/dev/null 2>&1 || true

export LLM_PROVIDER=mock
export RETRIEVAL_PROVIDER=keyword
export KB_PATH="$ROOT/knowledgebase/knowledgebase.jsonl"
export DATABASE_URL="postgresql://agent13:changeme@127.0.0.1:5432/agent13"
export ENV=development

echo "→ backend su :8000"
( cd backend && exec python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 ) \
  > "$RUN_DIR/backend.log" 2>&1 &
echo $! > "$RUN_DIR/backend.pid"

echo "→ build del frontend"
npm run build > "$RUN_DIR/build.log" 2>&1

export PORT=3000
export BACKEND_URL=http://127.0.0.1:8000
export ANALYTICS_LOG="$ROOT/data/analytics/events.jsonl"
export ADMIN_USERS_FILE="$ROOT/data/admin/users.json"
# I termini di retention sono segnaposto: in locale il purge non deve cancellare.
export RETENTION_DRY_RUN=true

echo "→ utente admin tester"
CREATE_ADMIN_PASSWORD=tester-13protein node server/scripts/create-admin.js tester \
  > "$RUN_DIR/admin.log" 2>&1 || true

echo "→ node su :3000"
node server/index.js > "$RUN_DIR/node.log" 2>&1 &
echo $! > "$RUN_DIR/node.pid"

echo -n "→ attesa dei servizi"
for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null && curl -sf http://127.0.0.1:3000/ >/dev/null; then
    echo " pronti."
    echo
    echo "  App      http://localhost:3000"
    echo "  Admin    http://localhost:3000/admin   (tester / tester-13protein)"
    echo "  Log      $RUN_DIR/{backend,node}.log"
    exit 0
  fi
  echo -n "."
  sleep 1
done
echo
echo "I servizi non sono partiti. Ultime righe dei log:"
tail -20 "$RUN_DIR/backend.log" "$RUN_DIR/node.log"
exit 1
