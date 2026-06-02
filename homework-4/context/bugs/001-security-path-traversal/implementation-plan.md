# Implementation Plan — SECURITY-001: Write Path Traversal

## Fix 1: Path Traversal Guard in storage.py

**File**: `src/app/storage.py`
**Location**: `write_holocron`, lines 11–14
**Before**:
```python
def write_holocron(name: str, body: str) -> None:
    path = BASE_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)           # BUG #2: silently overwrites existing holocron
```
**After**:
```python
def write_holocron(name: str, body: str) -> None:
    resolved = (BASE_DIR / name).resolve()
    if not resolved.is_relative_to(BASE_DIR.resolve()):
        raise ValueError("Path escapes vault")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(body)           # BUG #2: silently overwrites existing holocron
```
**Test command**: `PYTHONPATH=src uv run pytest -q`

---

## Fix 2: Catch ValueError and Return 400 in main.py

**File**: `src/app/main.py`
**Location**: `store`, lines 16–21
**Before**:
```python
@app.post("/holocron", status_code=201)
def store(holocron: Holocron):
    # BUG #2: no existence check — silently overwrites an existing holocron
    # SECURITY: holocron.name is unsanitized — '../evil.txt' escapes the vault dir
    storage.write_holocron(holocron.name, holocron.body)
    return {"name": holocron.name, "status": "stored"}
```
**After**:
```python
@app.post("/holocron", status_code=201)
def store(holocron: Holocron):
    # BUG #2: no existence check — silently overwrites an existing holocron
    # SECURITY: holocron.name is unsanitized — '../evil.txt' escapes the vault dir
    try:
        storage.write_holocron(holocron.name, holocron.body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"name": holocron.name, "status": "stored"}
```
**Test command**: `PYTHONPATH=src uv run pytest -q`

---

## Fix 3: Import HTTPException in main.py

**File**: `src/app/main.py`
**Location**: module imports, line 1
**Before**:
```python
from fastapi import FastAPI
```
**After**:
```python
from fastapi import FastAPI, HTTPException
```
**Test command**: `PYTHONPATH=src uv run pytest -q`
