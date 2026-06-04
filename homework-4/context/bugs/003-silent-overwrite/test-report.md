# Test Report — Bug 003: Silent Overwrite of Existing Holocron

## Summary

**Overall Status:** ✅ PASS

| Metric | Value |
|--------|-------|
| Tests Run | 2 |
| Tests Passed | 2 |
| Tests Failed | 0 |
| Exit Code | 0 |

All tests passed successfully.

```
2 passed, 1 warning in 0.03s
```

## FIRST Compliance

- **F — Fast**: Tests run in 0.03s using FastAPI TestClient (in-process, no network I/O). ✅
- **I — Independent**: Each test uses a fresh `tmp_path` vault via the `client` fixture. No shared state between tests. ✅
- **R — Repeatable**: Tests use isolated temporary directories via pytest `tmp_path`. Outcome is deterministic and does not depend on filesystem state or execution order. ✅
- **S — Self-validating**: Every test explicitly asserts both HTTP `status_code` and response body content. ✅
- **T — Timely**: Tests target the exact code changed by the Bug Fixer: existence check in `store()` function and duplicate-name rejection. ✅

## Test Cases

| Test Name | Covers | Result |
|-----------|--------|--------|
| `test_store_first_holocron_returns_201` | Happy path: First `POST /holocron` with unique name returns 201 Created | PASS |
| `test_store_duplicate_holocron_returns_409` | Error path: Second `POST /holocron` with same name returns 409 Conflict | PASS |

### Test Details

#### 1. test_store_first_holocron_returns_201
- **Purpose**: Verify that a fresh holocron can be stored successfully on first attempt.
- **Scenario**: Send `POST /holocron` with `name="wisdom-holocron"` and `body="Ancient Force wisdom"`.
- **Expected Response**: HTTP 201 with `{"name": "wisdom-holocron", "status": "stored"}`.
- **Result**: ✅ PASS

#### 2. test_store_duplicate_holocron_returns_409
- **Purpose**: Verify that attempting to store a holocron with an already-used name is rejected.
- **Scenario**: Store a holocron, then attempt to store another with the same name and different body.
- **Expected Response**: First POST returns 201; second POST returns HTTP 409 with detail message containing "already exists" and "Force does not allow overwriting".
- **Result**: ✅ PASS

## Failures

No failures to report. All tests passed.

## References

- **Fix Summary**: `context/bugs/003-silent-overwrite/fix-summary.md`
- **Test File**: `tests/test_003_silent_overwrite.py`
- **Source Files Tested**:
  - `src/app/main.py` — `store()` function (lines 16–39)
  - `src/app/storage.py` — `holocron_exists()` function (lines 19–23)
