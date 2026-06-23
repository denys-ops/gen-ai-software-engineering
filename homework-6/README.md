# Homework 6 — AI-Powered Multi-Agent Banking Pipeline

**Created by Denys Kondratiuk** · Reviewer: @Alexey-Popov

---

## What this is

This capstone has two layers. **Four meta-agents** (AI/automation workflows built with Claude Code)
*produce* a runtime **transaction-processing pipeline**, and both are deliverables:

- **Agent 1 — Specification** → `/write-spec` slash command + [`specification.md`](./specification.md) + [`agents.md`](./agents.md)
- **Agent 2 — Code generation** → the pipeline below, built while using **MCP context7** ([`research-notes.md`](./research-notes.md))
- **Agent 3 — Unit tests** → `/run-pipeline` & `/validate-transactions` commands + a **coverage-gate hook** that blocks `git push` under 80%
- **Agent 4 — Documentation** → this README + [`HOWTORUN.md`](./HOWTORUN.md)

The **runtime pipeline** ingests raw transactions from `sample-transactions.json` and runs each one
through three cooperating agents that communicate by passing JSON message files through `shared/`
directories. Each transaction ends as **approve / hold / reject** (or **rejected** at validation),
with a per-run summary and an append-only, PII-safe audit log. All monetary values use
`decimal.Decimal` (never `float`); currencies are validated against an ISO 4217 allowlist.

## Pipeline agents (runtime)

- **Transaction Validator** _(always-on)_ — checks required fields, ISO 4217 currency, `ACC-####`
  account format, parseable ISO-8601 timestamp, and amount rules (`> 0`, max 2 decimals; negative
  allowed only for `refund`). Invalid transactions are rejected with a structured `reason` and never
  advance.
- **Fraud Detector** _(toggleable)_ — assigns an additive, **configurable** risk score from three
  rules — high-value (`> 10,000`), off-hours (00:00–05:00 UTC), and cross-border (vs.
  `HOME_COUNTRY`) — and flags the transaction when the score exceeds the threshold.
- **Compliance Checker** _(toggleable)_ — makes the terminal decision `approve` / `hold` / `reject`,
  holding fraud-flagged, sanctioned-country, and high-value wire transactions.
- **Notification Agent** _(toggleable)_ — runs the **configurable rule engine** (`rules.json`)
  against the compliance output and appends a `notifications` list to every result. Behaviour is
  changed by editing `rules.json` — no code edits required.
- **Integrator** (orchestrator) — sets up `shared/`, wraps each record in a message envelope, runs the
  agents in order, isolates per-transaction failures (a bad record becomes an `error` result instead
  of aborting the run), rejects duplicate ids, and writes `shared/results/summary.json`.

## Architecture

```
                       sample-transactions.json          ┌──────────────┐
                                  │                       │  REST API    │
                                  │             POST /transactions        │
                                  │          ◀──────────── api/main.py   │
                                  ▼                       └──────────────┘
                          ┌───────────────┐
                          │  integrator   │  (orchestrator: envelopes, ordering,
                          └──────┬────────┘   per-txn isolation, summary)
                                 │ message envelope {message_id, timestamp,
                                 │   source_agent, target_agent, type, data}
       shared/input ─▶ shared/processing ─▶ shared/output ─▶ shared/results
                                 │
        ┌────────────────────────┼────────────────────────────────┐
        ▼                        ▼                                 ▼
┌─────────────────┐     ┌─────────────────┐    ┌───────────────────────────────────────┐
│   Transaction   │     │     Fraud       │    │  ← toggleable stages ─────────────── │
│    Validator    │────▶│    Detector     │──▶ │  Compliance   ──▶  Notification       │──▶ shared/results/
│ always-on gate  │     │ additive risk   │    │  Checker           Agent (rules.json) │     TXN*.json
│ fields/ccy/amt  │     │ (toggleable)    │    │  approve/hold/     notifications list │     summary.json
└────────┬────────┘     └─────────────────┘    │  reject            (toggleable)       │     audit.log
         │ reject                               └───────────────────────────────────────┘
         └───────────────────────────────────────────────────────────────────▶ (short-circuit)

   Custom MCP server (mcp/server.py) reads shared/results/ and exposes:
     • tool get_transaction_status(transaction_id)   • tool list_pipeline_results()
     • resource pipeline://summary
```

## Tech stack

| Layer | Choice |
|---|---|
| Language / runtime | Python 3.11 |
| Package / env manager | `uv` |
| REST API gateway | FastAPI + uvicorn |
| Custom MCP server | FastMCP 3.x (STDIO) |
| Testing | pytest + pytest-cov (187 tests, ~98% coverage) |
| MCP docs lookup | context7 (`@upstash/context7-mcp`) — see `research-notes.md` |
| Money | `decimal.Decimal`, `ROUND_HALF_UP`, ISO 4217 allowlist |
| Messaging | file-based JSON envelopes through `shared/` |

## Quick start

```bash
cd homework-6
uv sync
uv run python integrator.py        # run the pipeline (CLI)
uv run pytest --cov                 # tests + coverage
./demo.sh                           # one-command API demo (starts server, submits txns, tears down)
```

Full instructions, the slash commands, the coverage-gate hook, the REST API, and the MCP server are
in [`HOWTORUN.md`](./HOWTORUN.md).

## Configurable rule engine

Transaction notifications are driven by `rules.json` — a list of condition→action rules evaluated
after compliance. Each rule has:

- `id` — unique name shown in the `notifications` list.
- `match` — `"all"` (every condition must be true) or `"any"`.
- `when` — list of `{ field, op, value }` conditions. Field paths are dotted (e.g.
  `"metadata.country"`). Operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `contains`,
  `exists`.
- `action` — `{ channel, priority, message }` appended to the transaction's `notifications` list
  when the rule matches.

**To change behaviour without touching Python:** edit `rules.json` and re-run (or restart the API).
To use a different file entirely: `RULES_PATH=/path/to/other.json uv run python integrator.py`.

## Flexible pipeline (toggleable stages)

The three downstream stages (`fraud_detector`, `compliance_checker`, `notification_agent`) are all
optional. The `transaction_validator` is always-on. Control which stages run:

```bash
# Run only fraud detection (skip compliance + notifications):
ENABLED_STAGES="fraud_detector" uv run python integrator.py

# Run fraud + compliance (skip notifications):
ENABLED_STAGES="fraud_detector,compliance_checker" uv run python integrator.py

# Per-request override via the REST API:
curl -X POST "http://localhost:8000/transactions?stages=fraud_detector" \
     -H 'Content-Type: application/json' --data @sample-transactions.json
```

## REST API gateway

The pipeline is exposed as an HTTP API via FastAPI. Start it with:

```bash
cd homework-6
uv sync
uv run uvicorn api.main:app --port 8000
```

Swagger/OpenAPI docs: `http://localhost:8000/docs`

> **Single-worker only** — the file-based pipeline is single-writer by design. Run uvicorn with its
> default one worker; do **not** pass `--workers > 1`.

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness probe → `{"status":"ok"}` |
| `POST` | `/transactions` | Submit one transaction or a JSON array; optional `?stages=` CSV override. Returns PII-safe result(s). |
| `GET`  | `/transactions` | List all processed transactions. |
| `GET`  | `/transactions/{id}` | Single result (404 if not found). |
| `GET`  | `/summary` | Aggregate counts + per-transaction summary (includes `notified` count). |
| `GET`  | `/rules` | Active rule set — shows the configurable engine. |
| `GET`  | `/config` | Active `enabled_stages` + thresholds — shows the flexible pipeline. |

**One-command demo** (starts the API, submits all transactions, tears down cleanly):

```bash
./demo.sh            # uses port 8000 by default
PORT=8001 ./demo.sh  # override the port
```

## Repository layout

```
homework-6/
├── specification.md / agents.md / research-notes.md   # Agent 1 + research
├── integrator.py                                       # orchestrator
├── config.py                                           # env-overridable thresholds + stage registry
├── rules.json                                          # configurable notification rule engine
├── agents/{transaction_validator,fraud_detector,
│           compliance_checker,notification_agent,
│           rule_engine}.py
├── api/main.py                                         # FastAPI REST gateway
├── mcp/server.py            mcp.json                   # custom FastMCP server + config
├── scripts/                 .githooks/pre-push         # coverage gate
├── tests/                                              # 187 tests
├── demo.sh                                             # one-command API demo
├── demo/                                               # original CLI demo
└── docs/screenshots/                                   # submission screenshots
```
