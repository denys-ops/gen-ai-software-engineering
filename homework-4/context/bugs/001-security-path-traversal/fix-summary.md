# Fix Summary — SECURITY-001: Write Path Traversal

## Changes Made

### Fix 1: Path Traversal Guard in storage.py

**File**: `src/app/storage.py`  
**Function**: `write_holocron` (lines 11–16)

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

**Test Result**: ✅ PASS  
**Command**: `PYTHONPATH=src python -m pytest -q`  
**Output**: 
```
.                                                                        [100%]
1 passed
```

---

### Fix 2: Add Error Handling in main.py

**File**: `src/app/main.py`  
**Function**: `store` (lines 16–24)

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

**Test Result**: ✅ PASS  
**Command**: `PYTHONPATH=src python -m pytest -q`  
**Output**: 
```
.                                                                        [100%]
1 passed
```

---

### Fix 3: Import HTTPException in main.py

**File**: `src/app/main.py`  
**Imports** (line 1)

**Before**:
```python
from fastapi import FastAPI
```

**After**:
```python
from fastapi import FastAPI, HTTPException
```

**Test Result**: ✅ PASS  
**Command**: `PYTHONPATH=src python -m pytest -q`  
**Output**: 
```
.                                                                        [100%]
1 passed
```

---

## Overall Status

**✅ PASSED**

All three fixes have been successfully applied. The test suite passes without errors.

---

## Manual Verification

The following curl commands can be used to verify that the path traversal vulnerability is fixed:

### Test 1: Valid holocron name (should succeed with 201)
```bash
curl -X POST http://localhost:8000/holocron \
  -H "Content-Type: application/json" \
  -d '{"name": "skywalker", "body": "Luke is the chosen one"}' 
# Expected: {"name": "skywalker", "status": "stored"}
# HTTP Status: 201
```

### Test 2: Path traversal attempt (should fail with 400)
```bash
curl -X POST http://localhost:8000/holocron \
  -H "Content-Type: application/json" \
  -d '{"name": "../evil.txt", "body": "Attempted escape"}' 
# Expected: {"detail": "Path escapes vault"}
# HTTP Status: 400
```

### Test 3: Nested path traversal attempt (should fail with 400)
```bash
curl -X POST http://localhost:8000/holocron \
  -H "Content-Type: application/json" \
  -d '{"name": "../../etc/passwd", "body": "Attempt to escape"}' 
# Expected: {"detail": "Path escapes vault"}
# HTTP Status: 400
```

---

## References

- **Implementation Plan**: `context/bugs/001-security-path-traversal/implementation-plan.md`
- **Modified Files**:
  - `src/app/storage.py` — Added path confinement check in `write_holocron()`
  - `src/app/main.py` — Added HTTPException import and error handling in `store()` endpoint

## Defect Resolution

**Vulnerability**: Path Traversal in POST /holocron  
**Root Cause**: Unsanitized `holocron.name` parameter allows attackers to write files outside the vault directory using path traversal sequences (e.g., `../evil.txt`)  
**Fix**: 
1. Resolve file paths and verify they remain within BASE_DIR using `is_relative_to()`
2. Raise ValueError if path escapes vault
3. Catch ValueError in API endpoint and return HTTP 400 with descriptive error message

**Security Impact**: Prevents unauthorized file write access outside the vault directory.
