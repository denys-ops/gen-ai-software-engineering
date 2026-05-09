# Unit Tests and Coverage Details

## Sample Test Data Locations

| File | Format | Rows | Purpose |
|------|--------|------|---------|
| `tests/fixtures/valid_tickets.csv` | CSV | 2 | Verify valid CSV rows parse correctly with field mapping and type coercion |
| `tests/fixtures/invalid_tickets.csv` | CSV | 2 | Row-level errors (invalid email, missing required field) collected in errors list |
| `tests/fixtures/valid_tickets.json` | JSON | 2 | Valid JSON array with correct field types parses without error |
| `tests/fixtures/invalid_tickets.json` | JSON | 2 | Invalid rows (bad email, missing field) reported in errors list |
| `tests/fixtures/valid_tickets.xml` | XML | 2 | Valid XML document with `<tickets>` root and `<ticket>` elements parses correctly |
| `tests/fixtures/malformed.xml` | XML | — | Malformed XML (e.g., unclosed tag) raises meaningful parse error |
| `demo/sample_tickets.csv` | CSV | 50 | Demo script and bulk import testing with realistic volume |
| `demo/sample_tickets.json` | JSON | 20 | Demo script and interactive testing of JSON import path |
| `demo/sample_tickets.xml` | XML | 30 | Demo script and XML import testing across full ticket lifecycle |

---

## Coverage Report — Module Breakdown

**Current coverage: 98% line coverage** (460 statements, 11 missed)

Measured by `pytest-cov` against the `app/` package. HTML report: `docs/screenshots/test_coverage.png`.

| Module | Coverage | Gaps |
|--------|----------|------|
| `app/__init__.py` | 100% | — |
| `app/api/__init__.py` | 100% | — |
| `app/api/tickets.py` | 100% | — |
| `app/api/imports.py` | 86% | Lines 63–70 (format-detection error branches) |
| `app/domain/__init__.py` | 100% | — |
| `app/domain/enums.py` | 100% | — |
| `app/domain/models.py` | 100% | — |
| `app/main.py` | 95% | Line 23 (alternate validation-error handler path) |
| `app/services/__init__.py` | 100% | — |
| `app/services/classifier.py` | 100% | — |
| `app/services/classification_log.py` | 93% | Line 34 (defensive sentinel check) |
| `app/services/importers/csv.py` | 98% | Line 62 (rare CSV dialect error) |
| `app/services/importers/json.py` | 100% | — |
| `app/services/importers/xml.py` | 100% | — |
| `app/services/store.py` | 97% | Line 59 (empty filter edge case) |

**Uncovered lines are acceptable:** they guard against extremely rare encoding/dialect errors, handle defensive null-checks, or represent error paths exercised by integration tests but not isolated unit tests.

To view detailed coverage:

```bash
uv run pytest --cov=app --cov-report=html
open htmlcov/index.html
```
