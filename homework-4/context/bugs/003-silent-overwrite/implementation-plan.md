# Implementation Plan — Bug 003: Silent Overwrite of Existing Holocron

## Fix 1: Return 409 Conflict When Holocron Already Exists

**File**: `src/app/main.py`
**Location**: `store`, lines 16–24
**Before**:
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
**After**:
```python
@app.post("/holocron", status_code=201)
def store(holocron: Holocron):
    if storage.holocron_exists(holocron.name):
        raise HTTPException(
            status_code=409,
            detail="Holocron already exists. The Force does not allow overwriting."
        )
    try:
        storage.write_holocron(holocron.name, holocron.body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"name": holocron.name, "status": "stored"}
```
**Test command**: `PYTHONPATH=src uv run pytest -q`
