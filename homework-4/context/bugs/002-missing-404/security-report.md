# Security Report — BUG-002: Missing Holocron Returns 500 Instead of 404

## Summary

The bug-002 fix is a small, surgical change that catches `FileNotFoundError` in the
`GET /holocron/{name}` handler and converts it into a clean `HTTPException(404,
"Holocron not found")`. The change itself does not introduce any new vulnerability,
does not leak internal paths or stack traces, and uses an appropriate HTTP status
code. **Overall posture after the fix is improved** (one error-disclosure / status-
code-misuse class is closed), but the underlying `storage.read_holocron()` function
that this handler still calls remains vulnerable to path traversal — that is the
highest-severity item in scope for this review (CRITICAL, out of scope for this fix
but reachable through the same handler).

## Findings

### CRITICAL — Path traversal still reachable through `GET /holocron/{name}`

- **File / line**: `src/app/storage.py:6-8` (`read_holocron`) reached from
  `src/app/main.py:27-32` (`read`).
- **Description**: `read_holocron` performs `path = BASE_DIR / name` and immediately
  calls `path.read_text()` with no `.resolve()` and no `is_relative_to(BASE_DIR
  .resolve())` confinement check. The `name` path parameter is taken directly from
  the URL with no validation. The bug-002 fix only added a `try/except
  FileNotFoundError` around this call — it does NOT close the traversal vector.
- **Exploitation**: `GET /holocron/..%2F..%2Fetc%2Fpasswd` (or any sibling/parent
  relative reference once URL-decoded) reaches
  `Path("vault") / "../../etc/passwd"`, which `read_text()` will happily read.
  The handler then returns the file contents in `{"body": ...}` — full file
  disclosure. The new 404 branch is bypassed because the file *does* exist; an
  attacker still gets 200 + contents.
- **Why the fix doesn't help**: catching `FileNotFoundError` only triggers when the
  arbitrary path doesn't exist. Existing files outside `BASE_DIR` are still
  successfully read and returned.
- **Remediation**: mirror the `write_holocron` pattern in `read_holocron`:
  ```python
  resolved = (BASE_DIR / name).resolve()
  if not resolved.is_relative_to(BASE_DIR.resolve()):
      raise ValueError("Path escapes vault")
  return resolved.read_text()
  ```
  Then in `main.py:read`, also catch `ValueError` and translate to 400. (This is
  bug-001's territory; flagged here because the bug-002 handler is the entry point
  and a reviewer of this change must not certify the read path as safe.)

### LOW — No input validation on `name` path parameter

- **File / line**: `src/app/main.py:27-28`.
- **Description**: `name: str` accepts any string FastAPI will route through —
  including dots, slashes, NUL bytes, very long values, etc. Even after the
  traversal fix is applied, an explicit allow-list (`^[A-Za-z0-9_\-]{1,64}$`) at
  the handler boundary would reject malicious input before it reaches the
  filesystem layer, providing defense in depth.
- **Remediation**: validate `name` with a Pydantic `Field(pattern=...)` or a
  manual regex check; reject with 400 on mismatch.

### INFO — Generic 404 detail is appropriate; no internal info leakage

- **File / line**: `src/app/main.py:31-32`.
- **Description**: The new `HTTPException(404, detail="Holocron not found")`
  returns a constant string. It does **not** include the requested name, the
  resolved filesystem path, the `FileNotFoundError` message, or any traceback
  fragment. This is the correct behavior — good.
- **Remediation**: none. Keep the detail string static; do not echo `name` back
  in the error body, as that can become an XSS vector if the API is ever
  consumed by a browser that renders the JSON detail in HTML context.

### INFO — Read path has no response size / rate-limiting controls

- **File / line**: `src/app/main.py:27-32`, `src/app/storage.py:6-8`.
- **Description**: `read_text()` loads the entire file into memory before the
  handler returns the body in JSON. Combined with the path-traversal issue
  above, a single request can be used to exfiltrate arbitrarily large files.
  Even after traversal is fixed, no per-IP rate limit exists.
- **Remediation**: enforce a max body size on read (e.g. `Path.stat().st_size`
  check before reading), and add a per-IP rate limiter at the app or reverse-
  proxy layer.

## Verification of Fixes

| Stated concern in bug-002 | Verified? | Notes |
|---|---|---|
| `FileNotFoundError` from `storage.read_holocron` propagates as 500 | ✅ Fixed | `try/except FileNotFoundError` now wraps the call (`main.py:29-32`). |
| Response should be `404 Holocron not found` | ✅ Fixed | `HTTPException(status_code=404, detail="Holocron not found")` returned. |
| No internal path / stack trace leaked in the error body | ✅ Confirmed | Detail string is a constant; the exception object is not echoed. |
| Successful reads still return `{"name", "body"}` with 200 | ✅ Confirmed | Happy path unchanged. |

The bug-002 fix correctly addresses its stated security/quality concern
(status-code misuse and accidental internal-error disclosure). It does **not**
introduce any new vulnerability.

## No-Issue Areas

The following categories were inspected on the changed code and found clean:

- **Injection (shell / SQL / template)**: no `subprocess`, no SQL, no template
  rendering on the changed path.
- **XSS / CSRF**: not applicable — this is a pure JSON API with no HTML output
  and no session-cookie-based authentication. There is no browser-rendered
  surface and no state-changing request that relies on ambient credentials,
  so XSS and CSRF are not relevant threats here. (If a browser front-end is
  later added, re-evaluate.)
- **Hardcoded secrets**: none. `BASE_DIR = Path("vault")` is a non-sensitive
  configuration constant; no API keys, passwords, or tokens appear in the
  changed code.
- **Dependency risks**: imports are limited to `fastapi`, `pydantic`, and
  `pathlib` — no known-CVE imports introduced by this fix.
- **HTTP status codes (this fix)**: 404 is the correct status for "resource
  does not exist" and is client-actionable. Existing 201 (store success),
  400 (validation error) elsewhere are also appropriate.
- **Error-message disclosure (this fix)**: the 404 detail is a static string
  and does not embed the requested name or any path/exception data.

## References

- `context/bugs/002-missing-404/fix-summary.md`
- `src/app/main.py` (entire file reviewed; fix at lines 27-32)
- `src/app/storage.py` (entire file reviewed; `read_holocron` at lines 6-8 is the
  callee that the fixed handler invokes)
