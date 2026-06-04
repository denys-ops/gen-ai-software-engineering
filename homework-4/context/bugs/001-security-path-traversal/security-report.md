# Security Report — 001-security-path-traversal

## Summary

The Bug Fixer addressed the write-side path traversal vulnerability in `POST /holocron`
correctly: `write_holocron` now resolves the candidate path and verifies it stays inside
`BASE_DIR` via `Path.is_relative_to`, and the route maps the resulting `ValueError` to an
HTTP 400. Absolute-path payloads (e.g. `/etc/evil`) are also caught because pathlib
discards the left operand of `/` when the right side is absolute and the subsequent
`is_relative_to` check fails.

However, the fix was scoped to the **write** path only. The symmetrical read-side path
traversal in `read_holocron`/`GET /holocron/{name}` is **still exploitable** and represents
the highest-severity finding in this review (HIGH — arbitrary file disclosure). Several
lower-severity hardening gaps remain around input validation, error response shape, and
the unresolved 500-on-missing-file behaviour.

**Highest severity found: HIGH.**

## Findings

### F1 — HIGH: Read-side path traversal still exploitable
- **Location**: `src/app/storage.py:6-8`, `src/app/main.py:27-30`
- **Description**: `read_holocron` builds `path = BASE_DIR / name` and immediately calls
  `path.read_text()` with no confinement check. An attacker can issue
  `GET /holocron/..%2F..%2Fetc%2Fpasswd` (or `../../etc/passwd` after FastAPI's path
  parameter decoding) and read any file the process user can read. Because the bug-id is
  `001-security-path-traversal`, the read-side hole is in scope for this bug even though
  the implementation plan focused on writes.
- **Remediation**: Apply the same guard used in `write_holocron`:
  ```python
  def read_holocron(name: str) -> str:
      resolved = (BASE_DIR / name).resolve()
      if not resolved.is_relative_to(BASE_DIR.resolve()):
          raise ValueError("Path escapes vault")
      return resolved.read_text()
  ```
  Map the `ValueError` to HTTP 400 in the route, the same way `store` does.

### F2 — MEDIUM: `holocron_exists` shares the same traversal vector
- **Location**: `src/app/storage.py:19-20`
- **Description**: `holocron_exists` is not currently wired into any route, but it exposes
  the identical pattern (`BASE_DIR / name` with no confinement). Any future caller that
  forwards user input will reintroduce path traversal — this is a latent footgun.
- **Remediation**: Either delete the helper if unused, or add the same `.resolve()` +
  `is_relative_to` guard before returning `.exists()`.

### F3 — MEDIUM: `read` endpoint returns 500 on missing file
- **Location**: `src/app/main.py:27-30`, `src/app/storage.py:8`
- **Description**: `FileNotFoundError` from `path.read_text()` is not caught, so a request
  for a non-existent holocron yields HTTP 500 with a FastAPI stack trace in debug
  configurations. This is acknowledged as BUG #1 in the source comments. While not part of
  the 001 bug-id, the 500 leaks the resolved local path in the default uvicorn traceback
  if `--reload`/debug logging is enabled, and prevents clients from acting on a normal
  "not found" condition.
- **Remediation**: Catch `FileNotFoundError` in the route and raise
  `HTTPException(status_code=404, detail="Holocron not found")`. Do not surface the
  filesystem path in the response.

### F4 — LOW: No length or charset validation on `name` / `body`
- **Location**: `src/app/main.py:11-13`
- **Description**: The `Holocron` Pydantic model declares `name: str` and `body: str`
  with no `max_length`, `min_length`, or pattern constraint. An attacker can submit
  multi-megabyte bodies (disk exhaustion) or names containing NUL bytes, control
  characters, or platform-specific reserved names (e.g. `CON`, `PRN` on Windows). The
  `is_relative_to` check confines path traversal but does not address these vectors.
- **Remediation**: Constrain the model, e.g.
  ```python
  name: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_\-]+$")
  body: str = Field(max_length=64_000)
  ```
  A strict character allowlist on `name` would also make F1/F2 defence-in-depth.

### F5 — LOW: Error detail string is reused verbatim from the storage layer
- **Location**: `src/app/main.py:22-23`
- **Description**: `HTTPException(status_code=400, detail=str(exc))` echoes whatever
  message the storage layer raised. Today that is the constant `"Path escapes vault"`,
  which is safe, but the contract relies on the storage layer never embedding internal
  paths or file metadata in future `ValueError` messages. Coupling response text to
  internal exception messages is fragile.
- **Remediation**: Translate to a fixed response string in the route
  (`detail="Invalid holocron name"`) and log the underlying exception server-side.

### F6 — INFO: `Path("vault")` is relative to the process CWD
- **Location**: `src/app/storage.py:3`
- **Description**: `BASE_DIR = Path("vault")` resolves relative to wherever the FastAPI
  process was launched. If the service is started from an unexpected directory, the vault
  silently lives somewhere else and `.resolve()` will anchor the traversal check against
  that location. Not directly exploitable, but it makes audit and deployment fragile.
- **Remediation**: Pin the vault to an absolute, deployment-controlled directory, e.g.
  `BASE_DIR = Path(__file__).resolve().parent.parent.parent / "vault"` or read from an
  environment variable.

### F7 — INFO: No symlink hardening
- **Location**: `src/app/storage.py:11-16`
- **Description**: `.resolve()` follows symlinks, so the `is_relative_to` check correctly
  rejects a symlink that *currently* points outside `BASE_DIR`. However, if an attacker
  can plant a symlink inside `vault/` before a write (e.g. via another channel), the
  subsequent write could overwrite the symlink's target. There is no evidence that
  symlink creation is reachable from the public API today, so this is informational.
- **Remediation**: When writing, prefer `O_NOFOLLOW`/`O_EXCL` semantics
  (`resolved.open("xb")`) or explicitly reject paths whose parents contain symlinks.

## Verification of Fixes

| Fix | Stated Concern | Verified? |
|-----|----------------|-----------|
| `write_holocron` resolves `BASE_DIR / name` and asserts `is_relative_to(BASE_DIR.resolve())` (`src/app/storage.py:12-14`) | Prevent attacker-controlled `name` from escaping the vault on write | **Yes** — both sides of the comparison are resolved, so `..` segments, repeated `../`, absolute paths, and resolved symlinks pointing outside the vault are all rejected before any I/O occurs. |
| `store` catches `ValueError` and raises `HTTPException(400, ...)` (`src/app/main.py:20-23`) | Surface the vault-escape rejection as a client error, not a 500 | **Yes** — the route returns HTTP 400 and the response body does not include a stack trace or filesystem path. |
| `HTTPException` added to the FastAPI import (`src/app/main.py:1`) | Make the new error handler importable | **Yes** — symbol is imported and used. |

Net result: the **write-side** path traversal documented in the implementation plan is
fixed. The bug-id more broadly covers "path traversal" and the **read-side** equivalent
(F1) is still present.

## No-Issue Areas

The following categories were checked and found clean in the changed code:

- **Injection (shell / SQL / template)**: No `subprocess`, no SQL driver, no template
  rendering — the changed code only touches the filesystem via pathlib.
- **XSS / CSRF**: Not applicable. The service exposes a pure JSON API with no HTML
  rendering, no cookies, and no session state, so neither XSS sinks nor CSRF tokens are
  relevant.
- **Hardcoded secrets**: No API keys, passwords, tokens, or credentials appear in
  `main.py` or `storage.py`.
- **Dependency risks**: The changed code imports only `fastapi`, `pydantic`, and the
  standard-library `pathlib`. No suspicious or unmaintained packages were introduced; no
  known CVEs apply to the symbols used (`FastAPI`, `HTTPException`, `BaseModel`,
  `Path.resolve`, `Path.is_relative_to`).
- **HTTP status code for the fixed path**: The new `ValueError` → 400 mapping in `store`
  uses an appropriate 4xx code so clients can distinguish a bad request from a server
  fault.

## References

- `context/bugs/001-security-path-traversal/fix-summary.md`
- `context/bugs/001-security-path-traversal/implementation-plan.md`
- `src/app/main.py`
- `src/app/storage.py`
