#!/usr/bin/env bash
# One-command demo of the multi-agent banking pipeline.
set -euo pipefail

HW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HW_DIR"

echo "############################################################"
echo "# 1) Validate transactions (dry-run, no pipeline)"
echo "############################################################"
uv run python agents/transaction_validator.py --dry-run

echo
echo "############################################################"
echo "# 2) Run the full pipeline"
echo "############################################################"
uv run python integrator.py

echo
echo "############################################################"
echo "# 3) Results summary (shared/results/summary.json)"
echo "############################################################"
uv run python -c "import json; print(json.dumps(json.load(open('shared/results/summary.json'))['counts'], indent=2))"

echo
echo "############################################################"
echo "# 4) Sample custom-MCP query: get_transaction_status(TXN002)"
echo "############################################################"
uv run python -c "
import importlib.util, json
spec = importlib.util.spec_from_file_location('m', 'mcp/server.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(json.dumps(m.get_transaction_status('TXN002'), indent=2))
"
