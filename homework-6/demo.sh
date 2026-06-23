#!/usr/bin/env bash
# One-command demo of the multi-agent banking pipeline with REST API.
# Starts the API, submits transactions, and shows results. Zero manual steps.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

PORT="${PORT:-8000}"
BASE="http://127.0.0.1:${PORT}"

############################################################
# Helpers
############################################################

print_banner() {
  echo
  echo "############################################################"
  echo "# $*"
  echo "############################################################"
}

############################################################
# 0) Preflight
############################################################

print_banner "0) Preflight — sync deps + reset shared/"

uv sync --quiet

rm -rf shared

# Check the port is free before we try to bind.
if lsof -ti "tcp:${PORT}" >/dev/null 2>&1; then
  echo "ERROR: port ${PORT} is already in use."
  echo "       Run with a different port:  PORT=8001 ./demo.sh"
  exit 1
fi

############################################################
# Start the API in the background
############################################################

uv run uvicorn api.main:app --port "${PORT}" --log-level warning &
PID=$!
trap 'kill "${PID}" 2>/dev/null || true' EXIT

# Wait until the health endpoint responds (up to 30 × 0.5 s = 15 s).
echo "Waiting for API on port ${PORT} ..."
TRIES=0
until curl -sf "${BASE}/health" >/dev/null 2>&1; do
  TRIES=$(( TRIES + 1 ))
  if [ "${TRIES}" -ge 30 ]; then
    echo "ERROR: API did not come up after 15 s."
    exit 1
  fi
  sleep 0.5
done
echo "API is ready."

############################################################
# 1) Active configuration
############################################################

print_banner "1) GET /config — active pipeline stages and thresholds"
curl -sf "${BASE}/config" | python3 -m json.tool

############################################################
# 2) Submit the sample batch
############################################################

print_banner "2) POST /transactions — submit sample-transactions.json"
curl -sf -X POST "${BASE}/transactions" \
  -H 'Content-Type: application/json' \
  --data @sample-transactions.json \
  | python3 -m json.tool

############################################################
# 3) Summary counts
############################################################

print_banner "3) GET /summary — aggregate counts"
curl -sf "${BASE}/summary" | python3 -m json.tool

############################################################
# 4) Inspect TXN002 (flagged + held, carries notifications)
############################################################

print_banner "4) GET /transactions/TXN002 — flagged wire transfer with notifications"
curl -sf "${BASE}/transactions/TXN002" | python3 -m json.tool

############################################################
# 5) Active rule set
############################################################

print_banner "5) GET /rules — active configurable rule engine"
curl -sf "${BASE}/rules" | python3 -m json.tool

############################################################
# 6) Stage-toggle showcase — fraud_detector only
############################################################

print_banner "6) POST /transactions?stages=fraud_detector — run ONE stage only"
echo "   (compliance and notification stages are skipped)"
curl -sf -X POST "${BASE}/transactions?stages=fraud_detector" \
  -H 'Content-Type: application/json' \
  -d '{
    "transaction_id": "TXN_DEMO",
    "timestamp": "2026-03-16T03:00:00Z",
    "source_account": "ACC-9001",
    "destination_account": "ACC-9002",
    "amount": "50000.00",
    "currency": "USD",
    "transaction_type": "wire_transfer",
    "description": "Stage-toggle demo",
    "metadata": {"channel": "online", "country": "US"}
  }' | python3 -m json.tool
echo "   ^ notice: no 'decision', no 'notifications' — compliance/notification stages were skipped"

############################################################
# Done
############################################################

print_banner "Demo complete — all steps passed"
echo "  Swagger UI:  ${BASE}/docs"
echo "  Results dir: shared/results/"
echo "  (API server will stop when this script exits)"
