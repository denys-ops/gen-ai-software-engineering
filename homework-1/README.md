# Homework 1: Banking Transactions API

**Student:** Denys Kondraiuk  
**AI Tools Used:** Claude Code (claude.ai/code) with claude-sonnet-4-6 + Codex as second opinion (review only)

---

## Project Overview

A REST API for banking transactions built with **FastAPI** and **Pydantic v2**, using in-memory storage. All four required tasks and the CSV export optional feature (Task 4C) are implemented.

## Features Implemented

| Task | Description | Status |
|------|-------------|--------|
| Task 1 | Core CRUD endpoints (POST/GET transactions, GET by ID, GET balance) | ✅ |
| Task 2 | Full input validation (amount, account format, currency, type-account consistency) | ✅ |
| Task 3 | Transaction filtering by accountId, type, and date range (combinable) | ✅ |
| Task 3b | Per-currency balance calculation using `decimal.Decimal` for precision | ✅ |
| Task 4C | CSV export endpoint with filter support | ✅ |

## Architecture

```
src/app/
├── main.py              # FastAPI app + RequestValidationError → 400 handler
├── api/
│   ├── transactions.py  # POST/GET /transactions, GET /transactions/export
│   └── accounts.py      # GET /accounts/:id/balance
├── domain/
│   ├── enums.py         # TransactionType, TransactionStatus (StrEnum)
│   ├── models.py        # TransactionCreate (input+validation), Transaction (stored)
│   └── currencies.py    # ISO 4217 allowlist (frozenset)
└── services/
    ├── store.py         # InMemoryTransactionStore with filter() method
    ├── balances.py      # compute_balances() — per-currency Decimal arithmetic
    └── csv_export.py    # transactions_to_csv() using stdlib csv module
```

**Key design decisions:**
- `TransactionCreate` uses Pydantic v2 field validators + model-level validator for type/account-field consistency. All validation errors aggregate into `details[]` rather than short-circuiting.
- Balances are tracked **per currency** (multi-currency accounts supported).
- `InMemoryTransactionStore` is a module-level singleton; tests inject a fresh instance via FastAPI's `dependency_overrides` — no global state leaks between tests.
- All money uses `decimal.Decimal` end-to-end to avoid float precision drift.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/transactions` | Create transaction |
| `GET` | `/transactions` | List all (with optional filters) |
| `GET` | `/transactions/{id}` | Get by ID |
| `GET` | `/transactions/export?format=csv` | Download as CSV |
| `GET` | `/accounts/{id}/balance` | Per-currency balance |

**Query filters for GET /transactions and export:**
- `?accountId=ACC-XXXXX` — match fromAccount or toAccount
- `?type=deposit|withdrawal|transfer`
- `?from=YYYY-MM-DD&to=YYYY-MM-DD` — inclusive date range

**Validation rules:**
- Amount: positive, max 2 decimal places
- Account: `ACC-XXXXX` format (5+ alphanumeric chars after the dash)
- Currency: ISO 4217 subset (USD, EUR, GBP, JPY, CHF, CAD, AUD, NZD, SEK, NOK, ...)
- Type consistency: `deposit` requires `toAccount` only; `withdrawal` requires `fromAccount` only; `transfer` requires both

**Error response shape (400):**
```json
{
  "error": "Validation failed",
  "details": [
    {"field": "amount", "message": "Input should be greater than 0"},
    {"field": "currency", "message": "Invalid ISO 4217 currency code: 'XYZ'"}
  ]
}
```

## How AI Assisted This Project

Claude Code was used to plan and implement the entire project. The AI:
- Proposed the layered architecture (domain / services / api) and explained the trade-offs
- Wrote tests first (TDD), caught a Pydantic v2 Decimal serialization issue before implementation ran
- Identified that FastAPI wraps Pydantic `ValidationError` in its own `RequestValidationError` and that the exception handler needed to target the wrapper
- Suggested `decimal.Decimal` for all money arithmetic and noted why float would fail the `300.30` precision test

## Test Results

```
97 passed in 1.08s   (99% coverage)
tests/unit/        — validators, store, balances, csv_export
tests/integration/ — all HTTP endpoints, validation, filters, export
```
