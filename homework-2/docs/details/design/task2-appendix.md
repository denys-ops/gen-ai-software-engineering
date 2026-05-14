# Task 2 Design — Detailed Appendix

## Classifier Algorithm (Full Detail)

### Function Contract

```python
def classify(ticket_id: UUID, subject: str, description: str) -> ClassificationResult
```

Pure function. No I/O. Deterministic. Never raises on empty strings.

### Input Normalisation

Concatenate `subject + " " + description`, lowercase. All keyword tables are lowercase. Substring containment via `in` — no tokenisation, no stemming.

### Priority Resolution

1. Collect `matched_priorities` for every priority whose keywords appear as substrings.
2. Precedence: `urgent > high > low > medium`.
   - urgent matched → `urgent`
   - else high → `high`
   - else low → `low`
   - else → `medium` (default, no keywords)
3. `medium` never appears in `keywords_found`.

### Category Resolution

Walk categories in declaration order: `account_access → technical_issue → billing_question → feature_request → bug_report → other`. First match wins. `other` is the fallback and never appears in `keywords_found`.

### Confidence Formula

- `keywords_found` = union of all matched priority keywords + all matched category keywords across **all** categories (not just the winner), deduplicated, priority-first order.
- `hits = len(keywords_found)`
- `confidence = round(min(1.0, hits / 5.0), 2)`

### Reasoning String Format

```
"Matched priority keywords: {priority_kws}. Matched category keywords: {category_kws}."
```

Both are Python `repr`-style lists (e.g. `['critical']` or `[]`).

---

## Dependency Injection Wiring

### Production

`services/classification_log.py` declares `_log = ClassificationLog()` and `get_log()`. Routes declare `log: ClassificationLog = Depends(get_log)`.

### Test Isolation

```python
@pytest.fixture
def fresh_log() -> ClassificationLog:
    return ClassificationLog()
```

`client` fixture overrides both:

```python
app.dependency_overrides[get_store] = lambda: fresh_store
app.dependency_overrides[get_log] = lambda: fresh_log
```

Both cleared on teardown via `app.dependency_overrides.clear()`.

### Routes Using the Log

| Route | Dependencies |
|-------|--------------|
| `POST /tickets` | `store`, `log` (only when `auto_classify=true`) |
| `POST /tickets/{id}/auto-classify` | `store`, `log` |
| `GET /tickets/{id}/classifications` | `store` (existence check), `log` |
| All Task 1 routes | `store` only |

---

## Edge Cases

| # | Situation | Behaviour |
|---|-----------|-----------|
| 1 | No keywords in text | `category=other`, `priority=medium`, `confidence=0.0`, `keywords_found=[]` |
| 2 | Only priority keywords match | `category=other`, priority per precedence |
| 3 | Only category keywords match | `priority=medium`, category per first-match |
| 4 | Multiple priorities match | Highest precedence wins; all matched priority keywords in `keywords_found` |
| 5 | Multiple categories match | First-listed wins; all matched category keywords across all categories in `keywords_found` |
| 6 | Same keyword in priority + category | Counted once in `keywords_found` |
| 7 | Mixed-case input | Lowercased before matching |
| 8 | Auto-classify on non-existent ticket | `404`, no log entry written |
| 9 | GET classifications on non-existent ticket | `404` (not `200 []`) |
| 10 | GET classifications — ticket exists, never classified | `200 []` |
| 11 | Auto-classify called twice | Two log entries; ticket ends in same state |
| 12 | POST with `auto_classify=true` + body `category=other` | Classifier overwrites both fields |
| 13 | PUT after auto-classify | Sets fields; no lock. Subsequent auto-classify overwrites again |
| 14 | `?auto_classify=banana` | `400`, `field: "auto_classify"`. Ticket not created |
