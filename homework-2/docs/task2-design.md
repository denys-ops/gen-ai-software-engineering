# Task 2 Design Note — Auto-Classification

Locked contract for Phase 1 (Task 2). Builds on `task1-design.md`.  
Out of scope: LLM/ML calls, `manual_override` flag, log eviction on ticket delete.

---

## Classifier Algorithm — Summary

`classify(ticket_id, subject, description) -> ClassificationResult` — pure function, no I/O, deterministic.

1. Concatenate `subject + " " + description`, lowercase.
2. Match priority keywords in precedence order: `urgent > high > low > medium` (medium = default, no keywords).
3. Match category keywords in declaration order; first match wins (`other` = fallback, no keywords).
4. Collect all distinct matched keywords across all levels (deduped, priority-first order).
5. `confidence = round(min(1.0, len(keywords_found) / 5.0), 2)`.

---

## Route Contracts

| # | Method | Path | Body | Success | Errors |
|---|--------|------|------|---------|--------|
| 1 | POST | `/tickets` (modified) | `TicketCreate` JSON | 201 + `Ticket` | 400 |
| 2 | POST | `/tickets/{ticket_id}/auto-classify` | — | 200 + `ClassificationResult` | 400, 404 |
| 3 | GET | `/tickets/{ticket_id}/classifications` | — | 200 + `ClassificationResult[]` | 400, 404 |

New query param on POST `/tickets`: `auto_classify: bool = Query(False)`. When `true`, classifier overwrites `category`/`priority` after insert and logs the result. Classifier always overwrites; no manual-override lock.

GET `/tickets/{id}/classifications` requires the ticket to exist (404 if deleted); returns `[]` if ticket exists but has never been classified.

---

## ClassificationResult Schema

```json
{
  "ticket_id": "550e8400-e29b-41d4-a716-446655440000",
  "category": "account_access",
  "priority": "urgent",
  "confidence": 0.60,
  "reasoning": "Matched priority keywords: ['critical']. Matched category keywords: ['login', 'access'].",
  "keywords_found": ["critical", "login", "access"]
}
```

`Ticket` model is NOT extended — confidence lives only in the classification log.

---

## Five-Bullet Summary

- Pure substring classifier: priority precedence `urgent > high > low > medium`, category first-match in declaration order; confidence = `round(min(1.0, distinct_hits / 5.0), 2)`.
- Three route changes: new `POST /tickets/{id}/auto-classify` (200 + ClassificationResult), new `GET /tickets/{id}/classifications` (200 + array, ticket existence required), and `?auto_classify=true` flag on `POST /tickets`.
- Classifier always overwrites category/priority — no manual_override lock, no extra ticket fields; confidence lives only in the classification log.
- `classify(ticket_id, subject, description)` takes `ticket_id` explicitly so the pure function populates `ClassificationResult` without I/O.
- DI mirrors `get_store`: `get_log()` dependency, `fresh_log` fixture, `client` fixture updated to override both for per-test isolation.

---

## Further Reading

Looking for the full algorithm detail, dependency injection wiring, keyword tables, or the 14 edge-case table?  
→ [`docs/details/design/task2-appendix.md`](./details/design/task2-appendix.md)
