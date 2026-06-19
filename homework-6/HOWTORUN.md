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

## 8. One-command demo
```bash
bash demo/run.sh
```
Runs the validator dry-run, the full pipeline, and prints the results summary + a sample MCP query.
