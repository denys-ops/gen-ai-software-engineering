# How to Run the Application

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — install with:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
  After install, restart your shell or run `source ~/.zshrc` (or your shell's rc file) so `uv` is on `PATH`. Verify with `uv --version`.

## Quick Start

```bash
cd homework-1
bash demo/run.sh
```

The server starts at **http://localhost:3000**. Interactive API docs at **http://localhost:3000/docs**.

## Manual Start

```bash
cd homework-1
uv sync                   # install dependencies into .venv
PYTHONPATH=src uv run uvicorn app.main:app --port 3000 --reload
```

## Running Tests

```bash
cd homework-1
uv run pytest -v                              # all tests
uv run pytest tests/unit -v                   # unit only
uv run pytest tests/integration -v            # integration only
uv run pytest --cov=app --cov-report=term-missing   # with coverage
```

Expected: `97 passed in ~1s` with 99% coverage.

## Sample Requests

Keep the server running in the first terminal (Quick Start above), then open a **second terminal** for the requests below. The curl commands hit `http://localhost:3000` directly and work from any directory.

Open `demo/sample-requests.http` in VS Code (REST Client extension) or JetBrains IDE.

Or use curl:

```bash
# Create a deposit
curl -s -X POST http://localhost:3000/transactions \
  -H 'Content-Type: application/json' \
  -d '{"toAccount":"ACC-12345","amount":1000.00,"currency":"USD","type":"deposit"}' | python3 -m json.tool

# List all transactions
curl -s http://localhost:3000/transactions | python3 -m json.tool

# Filter by account
curl -s 'http://localhost:3000/transactions?accountId=ACC-12345' | python3 -m json.tool

# Get account balance
curl -s http://localhost:3000/accounts/ACC-12345/balance | python3 -m json.tool

# Export as CSV
curl -s 'http://localhost:3000/transactions/export?format=csv'
```

## Environment

No environment variables or external services required. Storage is in-memory and resets on server restart.
