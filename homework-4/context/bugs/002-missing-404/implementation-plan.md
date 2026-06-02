# Implementation Plan — BUG-002: Missing Holocron Returns 500 Instead of 404

## Fix 1: Catch FileNotFoundError in read route and return 404

**File**: `src/app/main.py`
**Location**: `read`, lines 27–30
**Before**:
```python
@app.get("/holocron/{name}")
def read(name: str):
    # BUG #1: FileNotFoundError from storage is unhandled -> 500 instead of 404
    return {"name": name, "body": storage.read_holocron(name)}
```
**After**:
```python
@app.get("/holocron/{name}")
def read(name: str):
    try:
        return {"name": name, "body": storage.read_holocron(name)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Holocron not found")
```
**Test command**: `PYTHONPATH=src uv run pytest -q`
