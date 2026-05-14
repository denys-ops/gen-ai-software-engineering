# Test Isolation, CI Configuration, and Summary

## Test Isolation Pattern

Every test runs against a **fresh, isolated instance** of the store and classifier log via FastAPI's `dependency_overrides`.

### Fixture Design (`tests/conftest.py`)

```python
@pytest.fixture
def fresh_store() -> InMemoryTicketStore:
    return InMemoryTicketStore()

@pytest.fixture
def fresh_log() -> ClassificationLog:
    return ClassificationLog()

@pytest.fixture
def client(fresh_store: InMemoryTicketStore, fresh_log: ClassificationLog) -> TestClient:
    app.dependency_overrides[get_store] = lambda: fresh_store
    app.dependency_overrides[get_log] = lambda: fresh_log
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

**Benefits:**
- Tests are deterministic and repeatable
- Parallel test execution supported (each test has its own store)
- No database teardown/setup overhead
- Trivial to transition to a real DB later (swap `get_store` implementation)

---

## Continuous Integration

```bash
# Full suite with coverage gate (exits 0 if all pass and coverage >= 85%)
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=85

# JSON report for metrics collection
uv run pytest --json-report --json-report-file=report.json

# XML report for Jenkins/GitLab
uv run pytest --junit-xml=test-results.xml
```

These commands are pre-configured in `pyproject.toml` under `[tool.pytest.ini_options]`.

---

## Test Naming Conventions

- **File names:** `test_<component>.py` (e.g., `test_ticket_model.py`, `test_import_csv.py`)
- **Function names:** `test_<scenario>` (e.g., `test_create_and_retrieve_ticket`)
- **Fixtures:** prefixed with `fresh_` to signal new instances

---

## Summary

1. **100 tests** in unit, integration, and performance layers — **98% line coverage**
2. **Test pyramid** balances speed (unit: < 1 s) with confidence (integration: full API)
3. **Fresh fixtures per test** via `dependency_overrides` — total isolation and reproducibility
4. **Multi-format data** (CSV, JSON, XML) with valid and invalid fixtures cover happy-path and error-case paths
5. **All performance benchmarks pass** with 11–52× margins over thresholds

**Quick command reference:**

```bash
uv run pytest -v                                     # All tests
uv run pytest tests/unit/ -v                         # Unit tests only
uv run pytest tests/integration/ -v                  # Integration tests only
uv run pytest --cov=app --cov-report=term-missing   # With coverage
uv run pytest -k "csv" -v                            # Tests matching keyword
uv run pytest -x                                     # Stop at first failure
```
