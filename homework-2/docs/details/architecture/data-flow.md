# Data Flow — Classifier Decision and Request Lifecycle

## POST /tickets?auto_classify=true — Request Lifecycle

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router (tickets.py)
    participant V as Pydantic Validation
    participant S as Store
    participant CL as Classifier
    participant LOG as ClassificationLog

    C->>R: POST /tickets?auto_classify=true (JSON body)
    R->>V: Validate TicketCreate
    alt Validation fails
        V-->>R: ValidationError (422)
        R-->>C: 400 error envelope
    end
    V-->>R: TicketCreate model
    R->>S: insert(ticket)
    S-->>R: Ticket stored
    alt auto_classify = true
        R->>CL: classify(id, subject, description)
        CL-->>R: ClassificationResult
        R->>S: update(ticket) with category, priority, updated_at
        S-->>R: Ticket updated
        R->>LOG: record(result)
        LOG-->>R: Log appended
    end
    R-->>C: 201 Ticket
```

### Step-by-step

1. Client sends POST with `TicketCreate` JSON and optional `?auto_classify=true`.
2. FastAPI validates the JSON (`extra="forbid"` rejects unknown fields). Invalid query params caught here.
3. If validation fails → 422 → central handler converts to 400 with standard envelope.
4. Router creates `Ticket` with auto-generated UUID and current UTC timestamp.
5. Router inserts ticket into store.
6. If `auto_classify=true`: classifier invoked → `ClassificationResult` returned → ticket `category`, `priority`, `updated_at` patched → store updated → result logged.
7. Router returns 201 with the ticket.

### POST /tickets/{ticket_id}/auto-classify — Steps

1. Client sends POST with a valid UUID path parameter.
2. Router fetches the ticket from the store; returns 404 if not found.
3. Router invokes the classifier.
4. Router updates the ticket's `category`, `priority`, and `updated_at`.
5. Router records the classification result in the log.
6. Router returns 200 with the `ClassificationResult` (not the full Ticket).

---

## Classifier Decision Flow

```mermaid
flowchart TD
    A["Input: ticket_id, subject, description"] --> B["Concatenate subject + description\nLowercase the text"]
    B --> C["Match priority keywords in precedence order"]
    C -->|urgent keywords found| D["priority = urgent"]
    C -->|no urgent, high keywords found| E["priority = high"]
    C -->|no urgent/high, low keywords found| F["priority = low"]
    C -->|no priority keywords| G["priority = medium (default)"]
    B --> H["Match category keywords in declaration order"]
    H -->|first category matches| I["category = matched category"]
    H -->|no category matches| J["category = other (default)"]
    D & E & F & G --> K["Collect matched keywords from all priority levels"]
    I & J --> L["Collect matched keywords from all categories"]
    K --> M["Deduplicate — priority-first order"]
    L --> M
    M --> N["keywords_found = ordered list"]
    N --> O["hits = len(keywords_found)"]
    O --> P["confidence = round(min(1.0, hits/5.0), 2)"]
    P --> Q["Generate reasoning string"]
    Q --> R["Return ClassificationResult"]
```
