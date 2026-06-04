# Codebase Research: BUG-002 Missing Holocron Returns 500 Instead of 404

## Defect: Unhandled FileNotFoundError in Read Handler

**Symptom:**
When a client requests a holocron that does not exist via `GET /holocron/{name}`, the API returns HTTP 500 Internal Server Error instead of HTTP 404 Not Found.

**Location:**
- `src/app/storage.py:8`
- `src/app/main.py:27`

**Source snippet from src/app/storage.py:8:**
```python
    return path.read_text()         # BUG #1: FileNotFoundError propagates -> 500
```

**Source snippet from src/app/main.py:27:**
```python
def read(name: str):
```

Full context (lines 27–30 in main.py):
```python
@app.get("/holocron/{name}")
def read(name: str):
    # BUG #1: FileNotFoundError from storage is unhandled -> 500 instead of 404
    return {"name": name, "body": storage.read_holocron(name)}
```

**Cause → Effect:**
The `read_holocron()` function in storage.py line 8 calls `path.read_text()` on a file that may not exist. When the file is absent, `Path.read_text()` raises `FileNotFoundError`. Since the route handler at main.py line 27 does not wrap the call in a try-except block, this exception propagates unhandled to FastAPI, which converts it to an HTTP 500 response instead of the semantically correct HTTP 404 Not Found.

---

## Files Consulted

- `src/app/main.py` — FastAPI route definitions
- `src/app/storage.py` — Vault read/write helper functions
- `context/bugs/002-missing-404/bug-context.md` — Bug report and documented locations
