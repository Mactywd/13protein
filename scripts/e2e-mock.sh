#!/bin/bash
# Verifica end-to-end dell'harness mock, via HTTP sul server Node.
#
#   scripts/dev-local.sh && scripts/e2e-mock.sh
#   scripts/e2e-mock.sh it        # ripete la stessa sequenza in italiano
#
# Manda la sequenza fissa di messaggi che porta una conversazione dall'apertura
# al lead confermato, e controlla sugli stream SSE che ogni passo produca gli
# eventi attesi. Esce al primo controllo fallito.
set -uo pipefail
cd "$(dirname "$0")/.."

LANG_CODE="${1:-en}"
BASE="http://127.0.0.1:3000"
SID="E2E_${LANG_CODE}_$(date +%s)_$RANDOM"
OUT="$(mktemp -d)"
FAILED=0

fail() { echo "  ✗ $1"; FAILED=1; }
ok()   { echo "  ✓ $1"; }

check() { # check <file> <pattern> <descrizione>
  if grep -qF -- "$2" "$1"; then ok "$3"; else fail "$3 (atteso: $2)"; fi
}

send() { # send <n> <messaggio> [extra json]
  local n="$1" msg="$2" extra="${3:-}"
  local body
  body=$(python3 -c '
import json, sys
payload = {"session_id": sys.argv[1], "message": sys.argv[2]}
if sys.argv[3]:
    payload.update(json.loads(sys.argv[3]))
print(json.dumps(payload))' "$SID" "$msg" "$extra")
  curl -sN --max-time 30 -X POST "$BASE/api/chat" \
    -H 'Content-Type: application/json' -d "$body" > "$OUT/$n.sse"
}

echo "Sessione $SID (lingua $LANG_CODE)"

echo "1. apertura"
send 1 "" "{\"default_language\": \"$LANG_CODE\"}"
check "$OUT/1.sse" 'event: text' "testo di benvenuto"
check "$OUT/1.sse" '"value": "product_idea"' "bottoni dei profili"
check "$OUT/1.sse" '"step": "profile_select"' "passa a profile_select"
if [ "$LANG_CODE" = "it" ]; then
  check "$OUT/1.sse" 'Benvenuto' "risposta in italiano"
else
  check "$OUT/1.sse" 'Welcome' "risposta in inglese"
fi

echo "2. profilo"
send 2 "product_idea"
check "$OUT/2.sse" '"value": "proteins"' "bottoni delle categorie"
check "$OUT/2.sse" '"step": "category_select"' "passa a category_select"

echo "3. categoria"
send 3 "proteins"
check "$OUT/3.sse" 'event: carousel' "card della categoria"
check "$OUT/3.sse" 'doc:protein-powders' "card presa dal knowledgebase"
check "$OUT/3.sse" '"value": "powders"' "bottoni dei formati"

echo "4. formato"
send 4 "powders"
check "$OUT/4.sse" '"step": "project_input", "input_enabled": true' "apre l'input libero"

echo "5. progetto, primo giro"
send 5 "A whey protein for gyms"
check "$OUT/5.sse" '"step": "project_input"' "resta sullo step progetto"
check "$OUT/5.sse" 'event: text' "domanda di approfondimento"

echo "6. progetto, secondo giro"
send 6 "Target market Italy, 2 kg tubs, chocolate and vanilla, launch in spring"
check "$OUT/6.sse" 'event: message_break' "riassunto e invito in due bolle"
check "$OUT/6.sse" '"value": "request_quote"' "bottone del preventivo"
check "$OUT/6.sse" '"step": "qa"' "passa alle domande libere"

echo "7. domanda sul knowledgebase"
send 7 "Are you certified?"
check "$OUT/7.sse" 'Quality' "cita la pagina Quality"
check "$OUT/7.sse" '"step": "qa"' "resta sulle domande libere"

echo "8. richiesta di preventivo"
send 8 "request_quote"
check "$OUT/8.sse" '"step": "contact_input", "input_enabled": true' "chiede i contatti"

echo "9. contatti"
send 9 "Mario Rossi, Rossi Nutrition, mario@example.com"
check "$OUT/9.sse" '"value": "confirm"' "bottoni di conferma"
check "$OUT/9.sse" 'mario@example.com' "riepiloga il contatto"
check "$OUT/9.sse" '"step": "contact_confirm"' "passa alla conferma"

echo "10. conferma"
send 10 "confirm"
check "$OUT/10.sse" 'event: lead_info' "emette lead_info"
check "$OUT/10.sse" '"quoteRequested": true' "preventivo richiesto"
check "$OUT/10.sse" '"email": "mario@example.com"' "email nel lead"
check "$OUT/10.sse" '"step": "completed"' "conversazione completata"

echo "11. evento di funnel"
curl -s -o /dev/null -X POST "$BASE/api/track" -H 'Content-Type: application/json' \
  -d '{"event":"quote_request","lang":"'"$LANG_CODE"'","visitor_id":"e2e"}'
ok "quote_request inviato"

echo "12. admin"
TOKEN=$(curl -s -X POST "$BASE/api/admin/login" -H 'Content-Type: application/json' \
  -d '{"user":"tester","password":"tester-13protein"}' | python3 -c 'import json,sys; print(json.load(sys.stdin).get("token",""))')
if [ -z "$TOKEN" ]; then fail "login admin"; else ok "login admin"; fi

# La valutazione parte in background alla chiusura della conversazione.
for _ in $(seq 1 10); do
  curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/chats/$SID" > "$OUT/chat.json"
  grep -q '"eval_status": *"done"' "$OUT/chat.json" && break
  sleep 1
done
python3 - "$OUT/chat.json" <<'PY' || FAILED=1
import json, sys
d = json.load(open(sys.argv[1]))
s, ev = d["session"], d["evaluation"]
checks = [
    (s["status"] == "completata", f'stato completata (era {s["status"]!r})'),
    (s["profile"] == "product_idea", f'profilo salvato (era {s["profile"]!r})'),
    (s["category"] == "proteins", f'categoria salvata (era {s["category"]!r})'),
    (s["format"] == "powders", f'formato salvato (era {s["format"]!r})'),
    (s["quote_requested"] is True, "preventivo salvato"),
    (s["total_cost"] > 0, f'costo attribuito (era {s["total_cost"]})'),
    (len(d["messages"]) > 10, f'transcript non vuoto ({len(d["messages"])} bolle)'),
    (ev and ev["status"] == "done", f'valutazione conclusa (era {ev and ev["status"]!r})'),
]
bad = [msg for okk, msg in checks if not okk]
for okk, msg in checks:
    print(("  ✓ " if okk else "  ✗ ") + msg)
sys.exit(1 if bad else 0)
PY

echo "13. resoconto"
TODAY=$(date +%F)
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/report/stats?from=$TODAY&to=$TODAY" > "$OUT/report.json"
python3 - "$OUT/report.json" <<'PY' || FAILED=1
import json, sys
d = json.load(open(sys.argv[1]))
stats, funnel = d["stats"], d["funnel"]
checks = [
    (stats["total_sessions"] >= 1, f'sessioni nel periodo ({stats["total_sessions"]})'),
    (any(t["doc"] == "quality" for t in stats["top_topics"]),
     f'quality fra i topic citati ({[t["doc"] for t in stats["top_topics"]]})'),
    (any(r["value"] == "product_idea" for r in stats["by_profile"]), "breakdown per profilo"),
    (any(r["value"] == "proteins" for r in stats["by_category"]), "breakdown per categoria"),
    (stats["quote"]["requested"] >= 1, "preventivi contati"),
    (funnel["quote_requests"] >= 1, f'quote_request nel funnel ({funnel["quote_requests"]})'),
]
for okk, msg in checks:
    print(("  ✓ " if okk else "  ✗ ") + msg)
sys.exit(1 if any(not okk for okk, _ in checks) else 0)
PY

echo
if [ "$FAILED" -eq 0 ]; then
  echo "Tutti i controlli passati. Stream in $OUT"
else
  echo "CONTROLLI FALLITI. Stream in $OUT"
fi
exit "$FAILED"
