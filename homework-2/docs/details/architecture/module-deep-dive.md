# Component Deep-Dive

## API Layer (`api/tickets.py`, `api/imports.py`)

**Responsibility:** HTTP endpoint routing, request validation, response serialization, and dependency injection wiring.

Routes exposed:
- **Ticket CRUD:** POST (create), GET (list/single), PUT (update), DELETE
- **Auto-classification:** POST `/tickets/{id}/auto-classify`, GET `/tickets/{id}/classifications`
- **Bulk import:** POST `/tickets/import`

Each route accepts Pydantic models validated by the framework. FastAPI's 422 responses are intercepted and converted to 400 with a standard error envelope (details array with field-level errors). Dependency injection (`Depends()`) wires in the singleton store and classification log.

The `?auto_classify=true` flag on POST /tickets triggers classification after insertion and overwrites the ticket's category and priority. Invalid query parameter values (e.g., `?auto_classify=banana`) are caught before the ticket is created.

## Domain Layer (`domain/models.py`, `domain/enums.py`)

**Responsibility:** Data contracts and validation rules for all domain entities.

Pydantic v2 models:
- `TicketCreate` (request), `TicketUpdate` (request), `Ticket` (in-memory and response)
- `TicketMetadata` for source/browser/device_type sub-object
- `ClassificationResult` for audit log entries
- `ImportSummary` and `ImportError` for bulk operations

String enums (Status, Category, Priority, Source, DeviceType) use Pydantic's `str` mixin for automatic JSON serialization and FastAPI query parameter validation. All write models use `extra="forbid"` to reject unknown fields.

**No I/O is performed in the domain layer.**

## Store Service (`services/store.py`)

**Responsibility:** In-memory storage and ticket lifecycle management.

`InMemoryTicketStore` is a singleton per app lifetime; tests replace it with a fresh instance via `dependency_overrides`. Methods: `insert`, `get`, `update`, `delete`, `filter`. All data is stored in memory as a dict keyed by ticket UUID. State is lost on restart.

## Classifier Service (`services/classifier.py`)

**Responsibility:** Rule-based keyword matching and decision logic.

`classify(ticket_id, subject, description) -> ClassificationResult` is a pure function:
1. Concatenates and lowercases `subject + " " + description`.
2. Matches priority keywords in precedence order (urgent > high > low > medium).
3. Matches category keywords in declaration order (first match wins).
4. Collects all distinct matched keywords (deduped, priority-first order).
5. Calculates confidence as `min(1.0, len(keywords_found) / 5.0)` rounded to 2 decimal places.
6. Generates a human-readable reasoning string.

Always returns a result; never raises on empty text.

## Classification Log (`services/classification_log.py`)

**Responsibility:** Append-only audit log of all classification decisions.

`ClassificationLog` is a singleton maintaining an in-memory list of `ClassificationResult` objects. `log.record(result)` appends; `log.entries(ticket_id=None)` returns all entries (optionally filtered by ticket_id) in insertion order. The log is lost on restart; per-test isolation uses a fresh instance.

## Importers (`services/importers/csv.py`, `json.py`, `xml.py`)

**Responsibility:** Parse and validate bulk ticket data from three file formats.

Each importer exports `parse(file_bytes) -> (list[TicketCreate], list[ImportError])`:
- **CSV:** RFC 4180, required header row, `tags` semicolon-separated, `metadata_*` flattened, blank cells = omitted
- **JSON:** Top-level array; non-array root → 400; non-object elements → per-row errors
- **XML:** Root `<tickets>`, child `<ticket>`, parsed via `defusedxml.ElementTree` (secure against XXE)

Row numbers are 1-based (data rows only; CSV header is row 0).
