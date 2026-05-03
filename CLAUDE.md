# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a student homework repository for the **GenAI and Agentic AI for Software Engineering** course. Each homework lives in its own `homework-N/` directory. The repo will grow to include up to 6 homeworks. Technology stack per homework is the student's choice (Node.js, Python, etc.).

## Homework Structure

Each `homework-N/` directory must contain:

```
homework-N/
├── README.md          # Solution overview, features, architecture decisions, AI tools used
├── HOWTORUN.md        # Step-by-step instructions to run the application
├── src/               # Source code
├── docs/screenshots/  # Screenshots of AI interactions, running app, test results
└── demo/
    ├── run.sh (or run.bat)
    ├── sample-requests.http (or .sh)
    └── sample-data.json
```

## Submission Workflow

Homework is submitted as a PR on the **student's own fork** (never into the upstream repo):

```bash
git checkout -b homework-N-submission
# implement, commit
git push origin homework-N-submission
# open PR: base = main on your fork, compare = homework-N-submission
```

PRs must include a thorough description (summary, AI tools used, challenges, screenshots). Bare PRs are rejected. Reviewer to add: `Alexey-Popov`.

## Homework 1 — Banking Transactions API

**Goal:** REST API with in-memory storage (no database).

**Required endpoints:**
| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/transactions` | Create transaction |
| `GET` | `/transactions` | List all; supports `?accountId=`, `?type=`, `?from=`, `?to=` filters |
| `GET` | `/transactions/:id` | Get by ID |
| `GET` | `/accounts/:accountId/balance` | Account balance |

**Transaction model fields:** `id` (auto), `fromAccount`, `toAccount`, `amount`, `currency` (ISO 4217), `type` (deposit/withdrawal/transfer), `timestamp` (ISO 8601), `status` (pending/completed/failed).

**Validation rules:** amount > 0, max 2 decimal places; account format `ACC-XXXXX`; valid ISO 4217 currency codes.

**Error response shape:**
```json
{ "error": "Validation failed", "details": [{"field": "amount", "message": "..."}] }
```

**HTTP status codes:** 200, 201, 400, 404 (and 429 if rate limiting is implemented).

**Optional features (pick ≥1):** `GET /accounts/:accountId/summary`, interest calculation endpoint, CSV export (`GET /transactions/export?format=csv`), or rate limiting (100 req/min/IP).

## Running / Testing (per homework)

Each homework defines its own run commands in `HOWTORUN.md`. Until source code exists, refer to that file. Typical patterns once implemented:

```bash
# Node.js
cd homework-1/src && npm install && npm start

# Python
cd homework-1/src && pip install -r requirements.txt && python app.py
```

Test with curl or the provided `demo/sample-requests.http`.
