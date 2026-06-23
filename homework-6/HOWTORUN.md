# HOWTORUN — Homework 6 Multi-Agent Banking Pipeline

Author: Denys Kondratiuk

## Prerequisites
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (package/env manager)
- Node.js (only for the context7 MCP server, run via `npx`)

All commands below are run from the `homework-6/` directory unless noted.

---

## 1. Install dependencies
```bash
cd homework-6
uv sync
```

## 2. Run the pipeline end-to-end
```bash
uv run python integrator.py
```
Expected: a summary line (`total=8 validated=7 rejected=1 flagged=3 approved=4 held=3 errors=0`) and
a per-transaction table. Results are written to `shared/results/` (one `TXN*.json` per transaction,
plus `summary.json` and an append-only `audit.log`).

## 3. Validate transactions only (dry-run, no pipeline)
```bash
uv run python agents/transaction_validator.py --dry-run
```
Reports total / valid / invalid counts and the reason for each rejection (e.g. TXN006 →
`unsupported_currency`).

## 4. Run the tests with coverage
```bash
uv run pytest --cov --cov-report=term-missing
```
Expected: 69 passing tests, ~99% total coverage (gate is 80%, target ≥ 90%).

---

## 5. Claude Code slash commands (Agent 1 & Agent 3)
These live in the repo root `.claude/commands/` and operate on `homework-6/`:

| Command | What it does |
|---|---|
| `/write-spec [feature]` | Generates a `specification.md` from the template (Agent 1) |
| `/run-pipeline` | Runs the pipeline and summarizes results |
| `/validate-transactions` | Runs the validator dry-run and tabulates results |

> New commands/hooks are loaded by Claude Code at startup. If they don't appear, **restart the
> session** or run `/hooks` to review and load them.

## 6. Coverage-gate hook (blocks push under 80%)
Two layers share one script (`scripts/coverage-gate.sh`):

**a) Real git hook (enforces for everyone, any terminal):**
```bash
bash scripts/install-hooks.sh        # sets core.hooksPath=homework-6/.githooks (run once per clone)
```
After this, any `git push` that includes `homework-6/` changes runs the coverage gate and is
**blocked if coverage < 80%**.

**b) Claude Code hook** (`.claude/settings.json`): a `PreToolUse` hook that blocks Claude-issued
`git push` calls the same way. It loads on session start (restart or `/hooks` to activate).

Demo the gate manually:
```bash
bash scripts/coverage-gate.sh                       # PASS at 99%
COVERAGE_THRESHOLD=100 bash scripts/coverage-gate.sh # FAIL → exit non-zero (simulates a block)
```

---

## 7. MCP servers (Task 4)
Configuration: [`mcp.json`](./mcp.json) declares two servers — `context7` and the custom
`pipeline-status`.

**Run the custom FastMCP server standalone:**
```bash
uv run python mcp/server.py          # STDIO transport
```
It exposes: tool `get_transaction_status(transaction_id)`, tool `list_pipeline_results()`, and
resource `pipeline://summary` — all reading `shared/results/` (run the pipeline first).

**Register it with Claude Code** (so you can call the tools in a session for the screenshot):
```bash
claude mcp add pipeline-status -- uv run --directory homework-6 python mcp/server.py
```
Then ask Claude, e.g., "use get_transaction_status for TXN002" and "look up FastMCP with context7".

---

## 8. One-command demo (CLI pipeline)
```bash
bash demo/run.sh
```
Runs the validator dry-run, the full pipeline, and prints the results summary + a sample MCP query.

---

## 9. REST API gateway

Start the API (single-worker is mandatory — do **not** pass `--workers > 1`):

```bash
cd homework-6
uv sync
uv run uvicorn api.main:app --port 8000
```

Then open **`http://localhost:8000/docs`** for the interactive Swagger UI.

### Example curl calls

```bash
# Liveness probe
curl http://localhost:8000/health

# Submit the sample batch
curl -s -X POST http://localhost:8000/transactions \
  -H 'Content-Type: application/json' \
  --data @sample-transactions.json | python3 -m json.tool

# Retrieve a single result (flagged + held, carries notifications)
curl http://localhost:8000/transactions/TXN002 | python3 -m json.tool

# Aggregate counts (includes 'notified' field)
curl http://localhost:8000/summary | python3 -m json.tool

# Active notification rules
curl http://localhost:8000/rules | python3 -m json.tool

# Active pipeline config and thresholds
curl http://localhost:8000/config | python3 -m json.tool

# Per-request stage override — run fraud_detector only
curl -s -X POST "http://localhost:8000/transactions?stages=fraud_detector" \
  -H 'Content-Type: application/json' \
  --data @sample-transactions.json | python3 -m json.tool
```

---

## 10. One-command API demo

Starts the API automatically, submits all transactions, prints results, and tears down the server:

```bash
./demo.sh            # uses port 8000 by default
PORT=8001 ./demo.sh  # override the port if 8000 is busy
```

---

## 11. Flexible pipeline — toggling stages

The `transaction_validator` is always-on. The three downstream stages are optional:

```bash
# Run only fraud detection (skip compliance + notifications):
ENABLED_STAGES="fraud_detector" uv run python integrator.py

# Run fraud + compliance (skip notifications):
ENABLED_STAGES="fraud_detector,compliance_checker" uv run python integrator.py

# Full pipeline (default — all three stages):
uv run python integrator.py
```

Per-request override via the REST API: append `?stages=fraud_detector` (or any CSV combination)
to `POST /transactions`. Unknown stage names return HTTP 400.

---

## 12. Configurable notification rules

Edit `rules.json` to change which channels are notified and under what conditions — no Python
edits required. Supported operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `contains`,
`exists`. Dotted field paths (e.g. `metadata.country`) are resolved against the transaction data.

To use a completely different rules file:
```bash
RULES_PATH=/path/to/other-rules.json uv run python integrator.py
# or, for the API:
RULES_PATH=/path/to/other-rules.json uv run uvicorn api.main:app --port 8000
```
