#!/bin/bash
# Stack completo in locale (senza Traefik) → http://localhost:3000
#
#   ./start.local.sh            # build + avvio app, backend, postgres
#   ./start.local.sh backend    # ricostruisce e riavvia solo il backend
set -euo pipefail
cd "$(dirname "$0")"

docker compose -f docker-compose.local.yml up -d --build "$@"

cat <<'EOF'

  App       http://localhost:3000
  Backend   http://localhost:8000
  Postgres  localhost:5432

Utente admin (una tantum):
  docker compose -f docker-compose.local.yml exec app \
      node server/scripts/create-admin.js <username>

Solo con RETRIEVAL_PROVIDER=qdrant, e spende crediti OpenRouter:
  docker compose -f docker-compose.local.yml --profile qdrant up -d
  docker compose -f docker-compose.local.yml exec backend \
      python -m scripts.migrate_kb --recreate

Log:    docker compose -f docker-compose.local.yml logs -f
Stop:   docker compose -f docker-compose.local.yml down
EOF
