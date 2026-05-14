# Task 1 Design Note — Multi-Format Ticket Import API

Locked contract for Phase 1 (Task 1). Source of truth for test-engineer and developer.  
Out of scope: classification logic, `auto-classify` endpoint, `auto_classify` flag.

---

## Route Contracts Summary

| # | Method | Path | Body | Success | Errors |
|---|--------|------|------|---------|--------|
| 1 | POST | `/tickets` | `TicketCreate` JSON | 201 + `Ticket` | 400 |
| 2 | GET | `/tickets` | — | 200 + `Ticket[]` | 400 (bad enum) |
| 3 | GET | `/tickets/{ticket_id}` | — | 200 + `Ticket` | 400, 404 |
| 4 | PUT | `/tickets/{ticket_id}` | `TicketUpdate` JSON | 200 + `Ticket` | 400, 404 |
| 5 | DELETE | `/tickets/{ticket_id}` | — | 204 | 400, 404 |
| 6 | POST | `/tickets/import` | `multipart/form-data` `file` | 200 + `ImportSummary` | 400 |

All 4xx use the standard envelope: `{"error": "...", "details": [{"field": "...", "message": "..."}]}`.

---

## Key Decisions

- PUT uses `model_dump(exclude_unset=True)` — only keys present in the body are applied; absent keys retain current values; explicit `null` clears the field.
- Status transitions: `→ resolved` sets `resolved_at`; `resolved →` anything clears it.
- Import format detection priority: explicit `?format=` → MIME type → filename suffix; all fail → 400.
- Container-level malformed imports → 400; row-level failures → 200 with errors in `ImportSummary`.
- XML parsed with `defusedxml.ElementTree` exclusively (XXE protection).

---

## Five-Bullet Summary

- All six routes are fully specified with exact request shapes, success codes (201 create / 200 list-get-put-import / 204 delete), and the shared error envelope.
- `POST /tickets/import` accepts `multipart/form-data` with a `file` field; format detected via priority order (explicit `?format=` → MIME → suffix); response is `ImportSummary` with counts and per-row errors only — no created IDs echoed back.
- XML, CSV, and JSON wire schemas are pinned: XML uses `<tickets><ticket>` with snake_case child elements and `<tags><tag>` / `<metadata>` wrappers; CSV uses a required header row with flat `metadata_*` columns and semicolon-separated `tags`; JSON is a top-level array of `TicketCreate` objects.
- PUT uses partial-merge with `exclude_unset=True`: omitted keys retain previous values, explicit `null` clears the field, `updated_at` always refreshes, transitioning into `resolved` sets `resolved_at`, transitioning out clears it.
- The validation error catalogue has 18 conditions (rows 1–18); container-level malformed imports are 400, row-level failures are 200 with `ImportError` entries in `ImportSummary`.

---

## Further Reading

Looking for the full wire-format specs, PUT semantics detail, XML/CSV/JSON schema examples, or the complete validation error catalogue (18 conditions)?  
→ [`docs/details/design/task1-appendix.md`](./details/design/task1-appendix.md)
