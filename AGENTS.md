# Repository Guidelines

## Project Structure & Module Organization

This repository currently contains one implementation project in `homework-1`: a Python 3.11+ FastAPI banking transactions API. Application code lives in `homework-1/src/app`. Use `api/` for FastAPI routers, `domain/` for Pydantic models, enums, and currency constants, `services/` for business logic, in-memory storage, and CSV export, and `validators/` for validation helpers. Tests live under `homework-1/tests`, split into `unit/` for service/domain behavior and `integration/` for API behavior. Documentation images belong in `homework-1/docs/screenshots`.

## Build, Test, and Development Commands

Run project commands from `homework-1`.

- `uv sync`: install runtime and development dependencies from `pyproject.toml` and `uv.lock`.
- `uv run uvicorn app.main:app --reload --app-dir src`: start the local FastAPI server with reload enabled.
- `uv run pytest`: run the full test suite.
- `uv run pytest tests/unit`: run unit tests only.
- `uv run pytest tests/integration`: run API integration tests only.
- `uv run pytest --cov=app`: run tests with coverage reporting.

## Coding Style & Naming Conventions

Use 4-space indentation, type hints, and clear Python module boundaries. Existing modules use `from __future__ import annotations`; keep that pattern in new application files. Use `snake_case` for modules, functions, variables, and pytest fixtures. Use `PascalCase` for Pydantic models and test classes. Preserve public JSON field aliases such as `fromAccount` and `toAccount` when extending request or response models.

## Testing Guidelines

The project uses pytest, FastAPI `TestClient`, and fixture-based isolated in-memory stores. Add unit tests for new service, domain, or validation behavior. Add integration tests when changing routes, status codes, response shapes, filtering, or validation errors. Name test files `test_*.py`, test classes `Test*`, and test methods `test_*`. Keep tests deterministic and avoid sharing mutable store state between cases.

## Commit & Pull Request Guidelines

The current git history has one broad initial commit, so use clear imperative commit messages going forward, such as `Add transaction filter tests` or `Fix account validation error response`. Pull requests should include a short behavior summary, tests run, linked issue or task when available, and screenshots only for documentation or UI-visible changes.
