# Verified Research — Bug 003: Silent Overwrite of Existing Holocron

## Verification Summary

**Verdict:** PASS — Research Quality: **EXCELLENT**

All verifiable claims in `codebase-research.md` were checked against the actual
source files (`src/app/main.py` and `src/app/storage.py`). Every cited
`file:line` reference is accurate and every quoted snippet matches the source
character-for-character (modulo leading whitespace). No critical or minor
discrepancies were found. The research is fully trustworthy as evidence for an
implementation plan.

## Verified Claims

- **`src/app/main.py:17-21` — `store()` endpoint definition.** Confirmed: line 17
  contains `def store(holocron: Holocron):`, line 18-19 are the BUG #2 and SECURITY
  comments, line 20 is `try:`, and line 21 calls `storage.write_holocron(holocron.name, holocron.body)`.
  The quoted snippet matches exactly.
- **`src/app/main.py:21` — `storage.write_holocron()` is invoked without any
  prior existence check.** Confirmed: there is no `if holocron_exists(...)` or
  similar guard between the endpoint declaration and the write call.
- **`src/app/storage.py:12` — `resolved = (BASE_DIR / name).resolve()`.**
  Confirmed: line 12 contains the exact string
  `    resolved = (BASE_DIR / name).resolve()`.
- **`src/app/storage.py:11-16` — `write_holocron` function body.** Confirmed:
  line 11 is the `def write_holocron(name: str, body: str) -> None:` signature,
  lines 12-16 contain the resolve, the `is_relative_to` traversal check, the
  `mkdir`, and the unconditional `resolved.write_text(body)` call. The quoted
  snippet matches character-for-character.
- **`src/app/storage.py:16` — `resolved.write_text(body)` unconditionally
  overwrites any existing file.** Confirmed: line 16 reads
  `    resolved.write_text(body)           # BUG #2: silently overwrites existing holocron`.
  There is no precondition check on existence before the write.
- **Cause→Effect chain: `store()` in `main.py` calls `write_holocron()` in
  `storage.py`, and the latter ends with an unconditional `write_text` that
  overwrites existing holocrons silently.** Confirmed by reading both files end
  to end — the path-traversal guard exists (lines 13-14) but no
  existence/conflict guard exists anywhere along the call chain.

## Discrepancies Found

None. No critical or minor discrepancies were identified.

## Research Quality Assessment

**Level:** EXCELLENT
**Verification rate:** 6 / 6 = **100 %**
**Counts:** verified = 6, minor discrepancies = 0, critical discrepancies = 0.

Every `file:line` reference resolves to the correct location in the actual
source, every quoted snippet is an exact reproduction of the underlying code,
and the cause-effect explanation accurately describes the missing existence
check in the `store()` → `write_holocron()` call path. The research is complete
enough, precise enough, and free enough of fabrication that the Bug Planner can
build an implementation plan directly on top of it without re-verification.

## References

- `homework-4/src/app/main.py` — verified lines 16-24 (store endpoint).
- `homework-4/src/app/storage.py` — verified lines 11-20 (`write_holocron` and
  `holocron_exists`).
- `homework-4/context/bugs/003-silent-overwrite/research/codebase-research.md`
  — researcher output under evaluation.
