# Codebase Research — Bug 003: Silent Overwrite of Existing Holocron

## Defect: No 409 Conflict When Holocron Already Exists

**Symptom**

Creating a holocron with a name that already exists silently overwrites the existing content instead of rejecting the request with a 409 Conflict status code. The second POST returns 201 Created and the original holocron data is lost without warning.

**Location (Main.py)**

`src/app/main.py` lines 17-21

**Source Snippet**

```python
def store(holocron: Holocron):
    # BUG #2: no existence check — silently overwrites an existing holocron
    # SECURITY: holocron.name is unsanitized — '../evil.txt' escapes the vault dir
    try:
        storage.write_holocron(holocron.name, holocron.body)
```

**Location (Storage.py)**

`src/app/storage.py` line 12

**Source Snippet**

```python
    resolved = (BASE_DIR / name).resolve()
```

(Relevant code context: The `write_holocron` function at lines 11-16)

```python
def write_holocron(name: str, body: str) -> None:
    resolved = (BASE_DIR / name).resolve()
    if not resolved.is_relative_to(BASE_DIR.resolve()):
        raise ValueError("Path escapes vault")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(body)           # BUG #2: silently overwrites existing holocron
```

**Cause → Effect**

The `store()` endpoint in `main.py` (lines 17-21) calls `storage.write_holocron()` without checking if the holocron name already exists; the `write_holocron()` function (line 12 onwards) constructs a path and validates it against traversal attacks, but `resolved.write_text(body)` at line 16 unconditionally overwrites any existing file without raising an error or exception, allowing duplicate-name requests to silently overwrite prior holocron data instead of returning 409 Conflict.

---

## Files Consulted

- `src/app/main.py` — store endpoint definition
- `src/app/storage.py` — write_holocron function implementation
- `context/bugs/003-silent-overwrite/bug-context.md` — bug report and expected behavior
