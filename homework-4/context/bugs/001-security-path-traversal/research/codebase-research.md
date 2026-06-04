# Codebase Research — SECURITY-001: Write Path Traversal

## Defect 1: Unsanitized Path Traversal in `write_holocron()`

**Symptom**

An attacker can write files outside the vault directory by submitting a POST request to `/holocron` with a `name` field containing path traversal sequences (e.g., `../pwned.txt`). Files are created at arbitrary locations on the filesystem where the process has write permission.

**Location**

`src/app/storage.py` line 12

**Source Snippet**

```python
def write_holocron(name: str, body: str) -> None:
    path = BASE_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)           # BUG #2: silently overwrites existing holocron
```

**Cause → Effect**

The `name` parameter is directly concatenated with `BASE_DIR` without validating that the resulting path stays within the vault directory, allowing `../` sequences to escape the vault and write to arbitrary locations on disk.

---

## Defect 2: Unsanitized Name Parameter in POST Handler

**Symptom**

An attacker can write files outside the vault directory by submitting a POST request to `/holocron` with a `name` field containing path traversal sequences. The unsanitized `name` is passed directly to `storage.write_holocron()` without validation.

**Location**

`src/app/main.py` line 20

**Source Snippet**

```python
@app.post("/holocron", status_code=201)
def store(holocron: Holocron):
    # BUG #2: no existence check — silently overwrites an existing holocron
    # SECURITY: holocron.name is unsanitized — '../evil.txt' escapes the vault dir
    storage.write_holocron(holocron.name, holocron.body)
    return {"name": holocron.name, "status": "stored"}
```

**Cause → Effect**

The POST handler passes the user-supplied `holocron.name` field directly to `storage.write_holocron()` without any validation or sanitization, allowing path traversal payloads to reach the path construction logic unchecked.

---

## Files Consulted

- `src/app/storage.py` — Storage layer with `write_holocron()` function
- `src/app/main.py` — FastAPI route handlers including POST `/holocron` endpoint
- `context/bugs/001-security-path-traversal/bug-context.md` — Bug report with reproduction steps
