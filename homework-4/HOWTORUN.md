# How to Run — Homework 4

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`pip install uv` or `brew install uv`)
- [Claude Code CLI](https://claude.ai/code) (`npm install -g @anthropic-ai/claude-code`)
- A valid Anthropic API key in your environment (`ANTHROPIC_API_KEY`)

---

## 1. Install dependencies

```bash
cd homework-4
uv sync
```

---

## 2. Run the application (before-state — bugs present)

```bash
uv run uvicorn app.main:app --app-dir src --reload
```

Verify the seeded bugs:

```bash
# Bug 001 — path traversal (writes outside vault/)
curl -X POST http://localhost:8000/holocron \
  -H 'Content-Type: application/json' \
  -d '{"name": "../pwned.txt", "body": "I escaped!"}'
ls -la pwned.txt   # file exists outside vault/

# Bug 002 — missing holocron → 500 instead of 404
curl -i http://localhost:8000/holocron/does-not-exist

# Bug 003 — silent overwrite instead of 409
curl -X POST http://localhost:8000/holocron \
  -H 'Content-Type: application/json' \
  -d '{"name": "test", "body": "first"}'
curl -X POST http://localhost:8000/holocron \
  -H 'Content-Type: application/json' \
  -d '{"name": "test", "body": "second"}'  # should be 409, returns 201
```

---

## 3. Run the pipeline

Run all three bugs end-to-end:

```bash
./run-pipeline.sh
```

Run a single bug:

```bash
./run-pipeline.sh 001-security-path-traversal
./run-pipeline.sh 002-missing-404
./run-pipeline.sh 003-silent-overwrite
```

The pipeline runs 6 agents in order for each bug and writes artifacts to
`context/bugs/<bug-id>/`. Logs are saved to `context/bugs/<bug-id>/pipeline-log/`.

---

## 4. Run the application (after-state — bugs fixed)

After the pipeline completes, restart the server and verify the fixes:

```bash
uv run uvicorn app.main:app --app-dir src --reload
```

```bash
# 001 fixed — traversal rejected with 400
curl -i -X POST http://localhost:8000/holocron \
  -H 'Content-Type: application/json' \
  -d '{"name": "../pwned.txt", "body": "I escaped!"}'
# HTTP/1.1 400 Bad Request

# 002 fixed — missing holocron → 404
curl -i http://localhost:8000/holocron/does-not-exist
# HTTP/1.1 404 Not Found

# 003 fixed — duplicate → 409
curl -X POST http://localhost:8000/holocron \
  -H 'Content-Type: application/json' \
  -d '{"name": "test", "body": "first"}'   # 201
curl -i -X POST http://localhost:8000/holocron \
  -H 'Content-Type: application/json' \
  -d '{"name": "test", "body": "second"}'  # 409 Conflict
```

---

## 5. Run the generated tests

```bash
PYTHONPATH=src uv run pytest tests/ -v
```

Expected: all tests pass.

---

## Re-running the pipeline from scratch

The pipeline is not idempotent — re-running on already-fixed source will fail at the
bug-fixer stage. To reset to the before-state:

```bash
# Restore buggy source
git restore src/app/main.py src/app/storage.py

# Remove pipeline artifacts
rm -rf context/bugs/*/research \
       context/bugs/*/implementation-plan.md \
       context/bugs/*/fix-summary.md \
       context/bugs/*/security-report.md \
       context/bugs/*/test-report.md \
       context/bugs/*/pipeline-log \
       tests/conftest.py \
       tests/test_001_* tests/test_002_* tests/test_003_* \
       vault/

# Re-run
./run-pipeline.sh
```
