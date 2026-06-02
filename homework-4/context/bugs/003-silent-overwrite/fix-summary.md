# Fix Summary — Bug 003: Silent Overwrite of Existing Holocron

## Changes Made

### Fix 1: Add Existence Check to `store` Function

**File**: `src/app/main.py`  
**Function**: `store` (lines 16–32)

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
    try:
        if storage.holocron_exists(holocron.name):
            raise HTTPException(
                status_code=409,
                detail="Holocron already exists. The Force does not allow overwriting."
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    try:
        storage.write_holocron(holocron.name, holocron.body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"name": holocron.name, "status": "stored"}
```

**Test Result**: PASS  
**Notes**: Added existence check before writing. If holocron already exists, returns 409 Conflict. Also added exception handling around the existence check to catch path validation errors and return 400.

### Supporting Fix: Update `holocron_exists` in `storage.py`

**File**: `src/app/storage.py`  
**Function**: `holocron_exists` (lines 19–21)

**Before**:
```python
def holocron_exists(name: str) -> bool:
    return (BASE_DIR / name).exists()
```

**After**:
```python
def holocron_exists(name: str) -> bool:
    resolved = (BASE_DIR / name).resolve()
    if not resolved.is_relative_to(BASE_DIR.resolve()):
        raise ValueError("Path escapes vault")
    return resolved.exists()
```

**Test Result**: PASS  
**Notes**: Added path traversal validation to `holocron_exists` to ensure it validates paths before checking existence. This prevents absolute or escaped paths from being treated as valid existing holocrons. Validation is consistent with `write_holocron`.

## Overall Status

**PASSED**

All 8 tests pass successfully.

```
8 passed, 1 warning in 0.05s
```

## Manual Verification

### Verify 409 Conflict for Duplicate Holocron

```bash
# Store initial holocron
curl -X POST http://localhost:8000/holocron \
  -H "Content-Type: application/json" \
  -d '{"name": "test-holocron", "body": "First version"}'

# Expected: 201 Created
# {"name": "test-holocron", "status": "stored"}

# Attempt to store with same name
curl -X POST http://localhost:8000/holocron \
  -H "Content-Type: application/json" \
  -d '{"name": "test-holocron", "body": "Overwrite attempt"}'

# Expected: 409 Conflict
# {"detail": "Holocron already exists. The Force does not allow overwriting."}
```

### Verify 400 for Path Traversal

```bash
# Attempt with path traversal
curl -X POST http://localhost:8000/holocron \
  -H "Content-Type: application/json" \
  -d '{"name": "../evil.txt", "body": "Escape attempt"}'

# Expected: 400 Bad Request
# {"detail": "Path escapes vault"}
```

### Verify 400 for Absolute Path

```bash
# Attempt with absolute path
curl -X POST http://localhost:8000/holocron \
  -H "Content-Type: application/json" \
  -d '{"name": "/etc/passwd", "body": "Absolute path attempt"}'

# Expected: 400 Bad Request
# {"detail": "Path escapes vault"}
```

## References

- `context/bugs/003-silent-overwrite/implementation-plan.md` — Original fix specification
- `src/app/main.py` — Modified `store` function
- `src/app/storage.py` — Modified `holocron_exists` function
