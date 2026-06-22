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

- **Transaction Validator** — checks required fields, ISO 4217 currency, `ACC-####` account format,
  parseable ISO-8601 timestamp, and amount rules (`> 0`, max 2 decimals; negative allowed only for
  `refund`). Invalid transactions are rejected with a structured `reason` and never advance.
- **Fraud Detector** — assigns an additive, **configurable** risk score from three rules — high-value
  (`> 10,000`), off-hours (00:00–05:00 UTC), and cross-border (vs. `HOME_COUNTRY`) — and flags the
  transaction when the score exceeds the threshold.
- **Compliance Checker** — makes the terminal decision `approve` / `hold` / `reject`, holding
  fraud-flagged, sanctioned-country, and high-value wire transactions.
- **Integrator** (orchestrator) — sets up `shared/`, wraps each record in a message envelope, runs the
  agents in order, isolates per-transaction failures (a bad record becomes an `error` result instead
  of aborting the run), rejects duplicate ids, and writes `shared/results/summary.json`.

## Architecture

```
                       sample-transactions.json
                                  │
                                  ▼
                          ┌───────────────┐
                          │  integrator   │  (orchestrator: envelopes, ordering,
                          └──────┬────────┘   per-txn isolation, summary)
                                 │ message envelope {message_id, timestamp,
                                 │   source_agent, target_agent, type, data}
          shared/input ─▶ shared/processing ─▶ shared/output ─▶ shared/results
                                 │
        ┌────────────────────────┼─────────────────────────┐
        ▼                        ▼                          ▼
┌─────────────────┐     ┌─────────────────┐       ┌─────────────────────┐
│   Transaction   │     │     Fraud       │       │     Compliance      │
│    Validator    │────▶│    Detector     │─────▶ │      Checker        │──▶ shared/results/
│ fields/ccy/amt  │     │ additive risk   │       │ approve/hold/reject │     TXN*.json
└────────┬────────┘     └─────────────────┘       └─────────────────────┘     summary.json
         │ reject                                                              audit.log
         └────────────────────────────────────────────────────────────────▶ (short-circuit)

   Custom MCP server (mcp/server.py) reads shared/results/ and exposes:
     • tool get_transaction_status(transaction_id)   • tool list_pipeline_results()
     • resource pipeline://summary
```

## Tech stack

| Layer | Choice |
|---|---|
| Language / runtime | Python 3.11 |
| Package / env manager | `uv` |
| Custom MCP server | FastMCP 3.x (STDIO) |
| Testing | pytest + pytest-cov (69 tests, ~99% coverage) |
| MCP docs lookup | context7 (`@upstash/context7-mcp`) — see `research-notes.md` |
| Money | `decimal.Decimal`, `ROUND_HALF_UP`, ISO 4217 allowlist |
| Messaging | file-based JSON envelopes through `shared/` |

## Quick start

```bash
cd homework-6
uv sync
uv run python integrator.py        # run the pipeline
uv run pytest --cov                 # tests + coverage
```

Full instructions, the slash commands, the coverage-gate hook, and the MCP server are in
[`HOWTORUN.md`](./HOWTORUN.md).

## Repository layout

```
homework-6/
├── specification.md / agents.md / research-notes.md   # Agent 1 + research
├── integrator.py                                       # orchestrator
├── config.py                                           # env-overridable thresholds
├── agents/{transaction_validator,fraud_detector,compliance_checker}.py
├── mcp/server.py            mcp.json                    # custom FastMCP server + config
├── scripts/                 .githooks/pre-push          # coverage gate
├── tests/                                               # 69 tests
├── demo/                                                # one-command demo
└── docs/screenshots/                                    # submission screenshots
```
