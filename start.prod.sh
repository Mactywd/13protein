#!/bin/bash
# Deploy dietro il Traefik condiviso sulla rete esterna `web`.
#
#   ./start.prod.sh            # build + (ri)avvio di tutti i servizi
#   ./start.prod.sh backend    # ricostruisce e riavvia solo il backend
#
# ⚠️ Mai eseguito: l'agente è ancora un harness mock. Prima di pubblicarlo
# servono l'informativa privacy (oggi segnaposto) e i termini di retention.
# Il dominio si passa dalla ./.env di root (DOMAIN=...).
set -euo pipefail
cd "$(dirname "$0")"

docker compose -f docker-compose.prod.yml up -d --build "$@"
