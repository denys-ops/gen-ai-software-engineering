# Security Report — Bug 003: Silent Overwrite of Existing Holocron

## Summary

The fix introduces an existence check via `storage.holocron_exists` and returns **409 Conflict** when a 
holocron with the requested name already exists, preventing silent overwrites. 
`holocron_exists` was simultaneously hardened to enforce the same path-traversal confinement as `write_holocron` 
(`.resolve()` on both sides of `is_relative_to`). 
Overall security posture for the modified code paths is **good**: no new vulnerabilities are introduced, 
the path-traversal guard is correctly mirrored across the write and exists helpers, 
and exceptions are mapped to deterministic 4xx responses rather than leaking 500s. 

Highest severity finding is **LOW** (a benign TOCTOU race between exists-check and write); 
a few **INFO**-level observations remain about missing input length limits and an unrelated, 
pre-existing traversal hole in `read_holocron` that is out of scope for this bug but worth flagging.

## Findings

### 1. TOCTOU race between `holocron_exists` and `write_holocron` — LOW
- **Location**: `src/app/main.py:19-27`
- **Description**: The exists-then-write sequence is not atomic. Two concurrent `POST /holocron` requests for the same `name` can both pass the `holocron_exists` check and then both call `write_holocron`, with the second silently overwriting the first. FastAPI’s sync handlers run in a threadpool, so this is reachable in practice with concurrent clients.
- **Remediation**: Make the write atomic by opening the file with `O_CREAT | O_EXCL` (e.g. `Path.open("x")` or `os.open(..., os.O_WRONLY | os.O_CREAT | os.O_EXCL)`) inside `write_holocron`, and translate the resulting `FileExistsError` into 409. This collapses the check-and-write into a single OS-level operation and removes the race.

### 2. No length / content validation on `name` — INFO
- **Location**: `src/app/main.py:11-13` (`Holocron` model), exercised via `src/app/storage.py:19-23`
- **Description**: `name` is typed as a free-form `str`. While the path-traversal guard prevents escapes, callers may still submit very long names, names with NUL bytes, or names with shell-metacharacters/Unicode that produce surprising filenames inside `vault/`. None is exploitable beyond the vault, but it enables low-impact filesystem clutter and odd directory structures (subpaths via embedded `/`).
- **Remediation**: Constrain `name` with a Pydantic validator: a max length (e.g. 128), a character class such as `^[A-Za-z0-9._-]+$`, and rejection of empty strings. Reject names containing `/` or `\` if subdirectories aren’t intended.

### 3. No length limit on `body` — INFO
- **Location**: `src/app/main.py:11-13`, `src/app/storage.py:11-16`
- **Description**: `body` is an unbounded string. An attacker can POST arbitrarily large payloads, exhausting disk and memory. Not introduced by this fix but unchanged by it.
- **Remediation**: Add a Pydantic `max_length` constraint on `body` (e.g. 1 MiB) and/or enforce a request-size limit at the ASGI layer.

### 4. Pre-existing path traversal in `read_holocron` (unchanged by this fix) — HIGH (informational for this bug)
- **Location**: `src/app/storage.py:6-8`
- **Description**: `read_holocron` still concatenates `BASE_DIR / name` with no `.resolve()` / `is_relative_to` confinement, so `GET /holocron/..%2Fevil.txt`-style inputs can read files outside the vault. This is the subject of bug `001-security-path-traversal`, not bug 003, but it is visible in the same file the fixer touched and must not be assumed to be fixed by the bug-003 work.
- **Remediation**: Out of scope here; tracked under bug 001. Verify that bug 001’s fix has been merged before shipping.

### 5. Error message for path-traversal rejection is identical to write path — INFO
- **Location**: `src/app/storage.py:14, 22`; surfaced at `src/app/main.py:25, 29`
- **Description**: `"Path escapes vault"` is returned both when the existence check rejects the name and when the write rejects it. This is intentional (consistent UX) and does not leak filesystem paths or stack traces, so it is acceptable. Logged as INFO because it confirms no internal-path disclosure occurs.
- **Remediation**: None required.

### 6. HTTP status code mapping is correct — INFO
- **Location**: `src/app/main.py:20-29`
- **Description**: 409 for duplicate (semantically appropriate per RFC 9110 §15.5.10), 400 for path-validation `ValueError`, and 201 on success. No 500s leak from the exists/write path under the modeled failure modes.
- **Remediation**: None.

## Verification of Fixes

| Stated Concern in `fix-summary.md` | Verified? | Notes |
|---|---|---|
| Add existence check so duplicate POST returns 409 instead of silently overwriting | ✅ | `main.py:19-23` raises `HTTPException(409, ...)` when `storage.holocron_exists` returns `True`. |
| Treat path-traversal `ValueError` from `holocron_exists` as 400, not 500 | ✅ | `main.py:24-25` catches `ValueError` from the exists call and maps to 400. |
| Make `holocron_exists` apply the same confinement as `write_holocron` | ✅ | `storage.py:19-23` calls `.resolve()` on the candidate path and `is_relative_to(BASE_DIR.resolve())`, mirroring `write_holocron` at `storage.py:12-13`. Both sides of the check are resolved, so the guard cannot be bypassed by a symlinked `BASE_DIR`. |
| Preserve the original 400 behavior for write-time traversal | ✅ | `main.py:26-29` retains the existing `try/except ValueError` around `write_holocron`. |

The fix does what the summary claims. The duplicate-overwrite vulnerability is closed for the single-request case; only the LOW-severity TOCTOU race remains.

## No-Issue Areas

The following categories were checked against the diff and found clean:

- **Injection (shell / SQL / template)**: No subprocess, ORM, or template usage in the changed code. `holocron.name` and `holocron.body` flow only into `pathlib` and a plain `write_text` call.
- **XSS / CSRF**: Not applicable — pure JSON API with no HTML responses, no session cookies, no browser-state-changing auth. Explicitly out of scope per pipeline instructions.
- **Hardcoded secrets**: None present. No API keys, tokens, or credentials in `main.py` or `storage.py`.
- **Dependency risks**: Only `fastapi`, `pydantic`, and the standard library `pathlib` are imported in the changed files; no known-CVE imports introduced or exposed by this fix.
- **Internal-path / stack-trace leakage in error responses**: Verified — the 400 response carries only `"Path escapes vault"`, and the 409 response carries only a human-readable conflict message. No filesystem paths, no traceback, no `BASE_DIR` value.
- **HTTP status code correctness**: 201 / 400 / 409 are all appropriate and machine-actionable; no 500s introduced by the new code paths.

## References

- `context/bugs/003-silent-overwrite/fix-summary.md`
- `src/app/main.py` (lines 16–30, `store` handler)
- `src/app/storage.py` (lines 11–23, `write_holocron` and `holocron_exists`)
