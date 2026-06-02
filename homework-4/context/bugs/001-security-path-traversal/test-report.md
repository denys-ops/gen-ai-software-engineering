# Test Report — 001-security-path-traversal

## Summary

**Overall Result**: ✅ **PASS**

- **Tests Run**: 5
- **Tests Passed**: 5
- **Tests Failed**: 0
- **Exit Code**: 0

All tests for the path traversal security fix passed successfully.

---

## FIRST Compliance

- **F (Fast)**: ✅ All tests run in-process using FastAPI TestClient. No real network I/O, no `time.sleep()`. Total execution time: 0.05s.
- **I (Independent)**: ✅ Each test gets a fresh vault via the `client` fixture with `tmp_path` isolation. No test depends on state created by another test.
- **R (Repeatable)**: ✅ The `conftest.py` fixture overrides `storage.BASE_DIR` with a fresh temporary directory for each test and restores the original afterward. Results are consistent across runs.
- **S (Self-validating)**: ✅ Every test has explicit assertions on both `status_code` and response body. No tests print without asserting.
- **T (Timely)**: ✅ Tests are written immediately after the fix, targeting the specific changes in `fix-summary.md`: the path traversal guard in `write_holocron()` and error handling in the `store()` endpoint.

---

## Test Cases

| Test Name | Coverage | Result |
|-----------|----------|--------|
| `test_store_clean_name_returns_201` | Happy path: valid name `"skywalker"` → 201 response with `"status": "stored"` | ✅ PASS |
| `test_store_traversal_parent_dir_returns_400` | Error path: name `"../evil.txt"` → 400 with error detail `"Path escapes vault"` | ✅ PASS |
| `test_store_traversal_multiple_dirs_returns_400` | Error path: name `"../../etc/passwd"` → 400 with error detail `"Path escapes vault"` | ✅ PASS |
| `test_store_valid_nested_path_returns_201` | Happy path: valid nested name `"jedi/luke.txt"` → 201 response with `"status": "stored"` | ✅ PASS |
| `test_store_absolute_path_returns_400` | Error path: absolute path `"/etc/passwd"` → 400 with error detail `"Path escapes vault"` | ✅ PASS |

---

## Failures

None. All tests passed.

---

## References

- **Fix Summary**: `context/bugs/001-security-path-traversal/fix-summary.md`
- **Test File**: `tests/test_001_security_path_traversal.py`
- **Fixture Configuration**: `tests/conftest.py`
- **Source Files Tested**:
  - `src/app/storage.py` — `write_holocron()` function with path traversal guard
  - `src/app/main.py` — `store()` endpoint with error handling for `ValueError`

---

## Test Execution Output

```
============================= test session starts ==============================
platform darwin -- Python 3.11.4, pytest-9.0.3, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: /Users/almin/PycharmProjects/gen-ai-software-engineering/homework-4
configfile: pyproject.toml
plugins: cov-7.1.0, anyio-4.13.0
collecting ... collected 5 items

tests/test_001_security_path_traversal.py::TestPathTraversalSecurity::test_store_clean_name_returns_201 PASSED [ 20%]
tests/test_001_security_path_traversal.py::TestPathTraversalSecurity::test_store_traversal_parent_dir_returns_400 PASSED [ 40%]
tests/test_001_security_path_traversal.py::TestPathTraversalSecurity::test_store_traversal_multiple_dirs_returns_400 PASSED [ 60%]
tests/test_001_security_path_traversal.py::TestPathTraversalSecurity::test_store_valid_nested_path_returns_201 PASSED [ 80%]
tests/test_001_security_path_traversal.py::TestPathTraversalSecurity::test_store_absolute_path_returns_400 PASSED [100%]

=============================== warnings summary ===============================
.../site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: ...

-- Docs: https://pytest.org/en/stable/how-out-pytest.out
======================== 5 passed, 1 warning in 0.05s =========================
```

---

## Security Fix Validation

The test suite validates the complete fix for the path traversal vulnerability:

1. **Path Confinement** — `write_holocron()` now resolves paths and checks they remain within `BASE_DIR` using `is_relative_to()`. Tests verify rejection of `../`, `../../`, and absolute paths.

2. **Error Handling** — The `store()` endpoint catches `ValueError` raised by the guard and returns HTTP 400 with a descriptive error message. Tests confirm the error detail is returned to the client.

3. **Clean Functionality** — Valid names (including nested paths like `jedi/luke.txt`) continue to work and return 201. Tests confirm normal operation is preserved.
