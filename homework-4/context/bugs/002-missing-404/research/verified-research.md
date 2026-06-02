# Verified Research: BUG-002 Missing Holocron Returns 500 Instead of 404

## Verification Summary

- **Verdict:** PASS
- **Research Quality:** EXCELLENT
- **Verifiable claims evaluated:** 7
- **Verified:** 7
- **Minor discrepancies:** 0
- **Critical discrepancies:** 0

Every `file:line` reference in `codebase-research.md` resolves correctly in the
source of truth. All code snippets reproduce the source verbatim, and the
documented cause→effect chain (missing file → `FileNotFoundError` → unhandled →
HTTP 500) is consistent with the actual code and with documented Python /
FastAPI semantics.

---

## Verified Claims

- **Symptom claim** — "`GET /holocron/{name}` returns HTTP 500 instead of HTTP 404 for a missing holocron."
  Confirmed by inspection: the read handler invokes `storage.read_holocron` with no exception handling, so an uncaught `FileNotFoundError` is converted to HTTP 500 by FastAPI's default error handler.
  Source: `src/app/main.py:27-30`, `src/app/storage.py:6-8`.

- **`src/app/storage.py:8` snippet** — `return path.read_text()         # BUG #1: FileNotFoundError propagates -> 500`
  Matches the source byte-for-byte at line 8.
  Source: `src/app/storage.py:8`.

- **`src/app/main.py:27` snippet** — `def read(name: str):`
  The function signature exists in the file; the exact line of the `def` statement is line 28 (line 27 holds the `@app.get("/holocron/{name}")` decorator). Off-by-one only — within the ≤2-line tolerance, so verified.
  Source: `src/app/main.py:28`.

- **Full context lines 27–30 of `main.py`** —
  ```python
  @app.get("/holocron/{name}")
  def read(name: str):
      # BUG #1: FileNotFoundError from storage is unhandled -> 500 instead of 404
      return {"name": name, "body": storage.read_holocron(name)}
  ```
  Reproduces lines 27–30 exactly.
  Source: `src/app/main.py:27-30`.

- **Cause claim — `read_holocron` calls `path.read_text()` on a possibly-missing file.**
  Verified: `storage.read_holocron` constructs `path = BASE_DIR / name` (line 7) without any existence check before calling `path.read_text()` (line 8).
  Source: `src/app/storage.py:6-8`.

- **Behavior claim — `Path.read_text()` raises `FileNotFoundError` when the file is absent.**
  Consistent with documented Python `pathlib` semantics (`Path.read_text` delegates to `open()`, which raises `FileNotFoundError` for missing paths).
  Source: Python standard library behavior; matches usage in `src/app/storage.py:8`.

- **Behavior claim — The route handler does not wrap the call in try/except, so the exception propagates and FastAPI returns HTTP 500.**
  Verified: `main.py:27-30` shows no try/except around `storage.read_holocron(name)`. FastAPI's default exception handler maps unhandled non-`HTTPException` errors to HTTP 500.
  Source: `src/app/main.py:27-30`.

---

## Discrepancies Found

None.

The only deviation from a perfectly exact citation is the `main.py:27` reference
pointing at the decorator line rather than the `def` line — a one-line offset,
which is within the ≤2-line tolerance defined by the
`research-quality-measurement` skill and therefore is **not** counted as a
discrepancy.

---

## Research Quality Assessment

- **Level:** EXCELLENT
- **Verdict:** PASS
- **Verification rate:** 7 / 7 = **100%**
- **Verified:** 7  •  **Minor discrepancies:** 0  •  **Critical discrepancies:** 0

The research document is concise, accurate, and traceable. Every `file:line`
anchor exists in the source tree, snippets reproduce the file contents verbatim,
and the explanatory chain (missing file → `FileNotFoundError` → unhandled →
HTTP 500) matches both the static code and the documented runtime behavior of
`pathlib.Path.read_text` and FastAPI's default exception handling. No
fabricated files, no fabricated line numbers, no misquoted code. With a 100%
verification rate and zero discrepancies, the document qualifies for the highest
research-quality tier.

---

## References

- `homework-4/context/bugs/002-missing-404/research/codebase-research.md` — research under verification
- `homework-4/src/app/main.py` — FastAPI route definitions (source of truth for `main.py` claims)
- `homework-4/src/app/storage.py` — vault read/write helpers (source of truth for `storage.py` claims)
- Python standard library documentation — `pathlib.Path.read_text` raises `FileNotFoundError` on missing files
- FastAPI framework behavior — unhandled non-`HTTPException` exceptions are converted to HTTP 500 responses
