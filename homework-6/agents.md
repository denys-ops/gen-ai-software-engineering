# agents.md — HW6 Multi-Agent Banking Pipeline

> **Extends the root [`/AGENTS.md`](../AGENTS.md).** That file defines repo-wide stack and
> Python conventions; this file defines the **domain invariants, message protocol, agent
> contracts, configuration, and testing rules** specific to the Homework 6 transaction-processing
> pipeline. Rules here are **non-negotiable** for any AI agent (or human) working on `homework-6/`.
> Workflow nudges live in the slash commands under `/.claude/commands/`.
>
> **Author:** Denys Kondratiuk ·

---

## 1. Project Context

Homework 6 is the capstone. **Four meta-agents** (Claude Code workflows) *produce* a runtime
**multi-agent banking pipeline**:

| Meta-agent | Task | Produces |
|---|---|---|
| Agent 1 — Specification | Task 1 | `specification.md`, this `agents.md`, `/write-spec` |
| Agent 2 — Code generation | Task 2 | the 3 runtime agents + `integrator.py` (uses MCP context7) |
| Agent 3 — Unit tests | Task 3 | tests, `/run-pipeline`, `/validate-transactions`, coverage-gate hook |
| Agent 4 — Documentation | Task 5 | `README.md` (with author name), `HOWTORUN.md` |

The **runtime pipeline** is three cooperating agents run **sequentially and synchronously** by an
integrator, communicating only through JSON message files on disk:

```
sample-transactions.json
        │
        ▼
   integrator ──▶ transaction_validator ──▶ fraud_detector ──▶ compliance_checker ──▶ shared/results/
                        │ (reject short-circuits straight to results/)
```

Reference: `homework-6/TASKS.md` (rubric authority), `homework-3/agents.md` (pattern this file follows).

---

## 2. Domain Invariants

Facts of the domain that must never be violated, regardless of implementation path.

| Invariant | Rule |
|---|---|
| **Decimal only** | All monetary amounts use `decimal.Decimal`. Parse from the JSON **string** `amount` field directly (`Decimal("1500.00")`) — never via `float`. Use `ROUND_HALF_UP`. No `float`, `int`, or arithmetic on raw strings. |
| **ISO 4217 currency** | `currency` must be a 3-letter uppercase code on an allowlist (USD, EUR, GBP, JPY, …). Unknown codes (e.g. `XYZ`) are a **validation reject**. |
| **Account format** | `source_account` and `destination_account` must match `^ACC-\d{4}$` (e.g. `ACC-1001`). |
| **Amount sign** | `amount > 0` is required **except** when `transaction_type == "refund"`, where a negative amount is permitted. `amount == 0` is **never** valid for any type. |
| **Timestamps** | All generated timestamps are ISO-8601 UTC via `datetime.now(timezone.utc)`. Never naive datetimes. Input `timestamp` is parsed as ISO-8601. |
| **Audit-on-action** | Every agent action appends one line to an **append-only** audit log: `{timestamp, agent, transaction_id, outcome}`. The audit log is never mutated or truncated in-place. |
| **PII masking** | Account numbers **and account-holder names** are treated as sensitive. Account numbers are masked to last-4 in all logs and audit entries (`ACC-1001` → `***1001`). Never log full account numbers, names, descriptions, or other PII in plaintext. |

---

## 3. Message Protocol

Agents pass exactly **one JSON message per transaction** through shared directories.

### Envelope schema

| Field | Type | Notes |
|---|---|---|
| `message_id` | string | `uuid4` |
| `timestamp` | string | ISO-8601 UTC, when the message was produced |
| `source_agent` | string | agent that wrote this message |
| `target_agent` | string | next agent to consume it (`results` = terminal) |
| `message_type` | string | e.g. `transaction` |
| `data` | object | transaction payload + accumulated agent annotations |

### Directory lifecycle

```
shared/
├── input/       ← integrator drops initial messages
├── processing/  ← an agent moves a message here while working on it
├── output/      ← agent writes its result for the next agent
└── results/     ← terminal outcomes + summary report
```

A message advances `input → processing → output` per stage; on a validator **reject** it
short-circuits directly to `results/`. The original `sample-transactions.json` is never mutated.

---

## 4. Agent Contracts

Every runtime agent exposes the same entrypoint:

```python
def process_message(message: dict) -> dict: ...
```

| Agent (file) | Consumes | Owns the decision | Output target |
|---|---|---|---|
| **Integrator** (`integrator.py`) | `sample-transactions.json` | orchestration: build envelopes, run agents in order, aggregate summary | `shared/results/` (+ `summary.json`) |
| **Transaction Validator** (`agents/transaction_validator.py`) | raw transaction message | fields / amount-sign / ISO 4217 / account format → `validated` or `rejected` + `reason` | `fraud_detector`, or `results/` on reject |
| **Fraud Detector** (`agents/fraud_detector.py`) | validated message | additive `risk_score` from configurable rules → `triggered_rules`, `flagged` | `compliance_checker` |
| **Compliance Checker** (`agents/compliance_checker.py`) | fraud-scored message | terminal `decision` ∈ {`approve`, `hold`, `reject`} + `decision_reason` | `shared/results/` |

**Ordering invariants:**
- The pipeline is **sequential and synchronous**: validator → fraud_detector → compliance_checker. No concurrency, no daemons.
- **Validator short-circuit:** a rejected transaction never reaches the fraud or compliance agents.
- Each agent **adds** to `message.data` (does not delete prior annotations) and writes its own audit entry.

The integrator entrypoint is:

```python
def run_pipeline(transactions_path: str = "sample-transactions.json") -> dict: ...
```

---

## 5. Configuration Rules

Fraud/compliance thresholds live in `homework-6/config.py` (env-overridable; env wins over default).

| Setting | Env var | Default |
|---|---|---|
| High-value threshold | `HIGH_VALUE_THRESHOLD` | `10000` |
| Off-hours window (start, end, UTC hour) | `OFF_HOURS_START` / `OFF_HOURS_END` | `0` / `5` (00:00–05:00 UTC) |
| Home country | `HOME_COUNTRY` | `US` |
| Risk weights | `WEIGHT_HIGH_VALUE` / `WEIGHT_CROSS_BORDER` / `WEIGHT_OFF_HOURS` | tunable additive weights |
| Flag threshold | `FRAUD_FLAG_THRESHOLD` | score above which `flagged = true` |

Thresholds must **never** be hardcoded inside agent logic — read them from `config.py` so behavior
is tunable without code edits. `HOME_COUNTRY=US` means DE/GB/EU transactions count as cross-border.

---

## 6. Naming & Stack Conventions

- **Stack:** Python 3.11, `uv`, FastMCP 3.x (Task 4 custom MCP server), pytest + pytest-cov.
- **Modules:** `snake_case`; runtime agents live in `homework-6/agents/<name>.py`.
- **Models / classes:** `PascalCase`. **Functions / variables:** `snake_case`.
- **Agent entrypoint:** `process_message(message: dict) -> dict` (uniform across all 3 agents).
- **Test files:** `test_*.py`; classes `Test*`; methods `test_*`.

---

## 7. Testing & Coverage Rules

- Use **pytest + pytest-cov**. One unit-test module per agent + **at least one integration test** for the full pipeline.
- **Isolate from the real `shared/`** — use `tmp_path` (or equivalent) so tests never read/write the repo's working directories.
- **Deterministic:** inject/freeze timestamps; never depend on wall-clock time or `datetime.now()` directly in assertions.
- **Coverage gate ≥ 80% blocks `git push`** (Task 3 hook). **Target ≥ 90%.**

---

## 8. Sample-Data Expectations (test oracle)

The 8 transactions in `sample-transactions.json` are the acceptance fixtures. Expected outcomes:

| TXN | Key attribute | Expected behavior |
|---|---|---|
| TXN001 | USD transfer 1500, US | validated → low risk → **approve** |
| TXN002 | USD **wire** 25000, US | validated → **high-value flag** → **hold** (wire scrutiny) |
| TXN003 | USD transfer **9999.99**, US | validated → **below** high-value threshold (boundary) → approve |
| TXN004 | EUR transfer 500, **DE, 02:47** | validated → **off-hours + cross-border flag** |
| TXN005 | USD **wire** 75000, US | validated → **high-value flag** → **hold** (wire scrutiny) |
| TXN006 | currency **XYZ** | **rejected** at validation (`unsupported_currency`) |
| TXN007 | GBP **refund**, **−100.00**, GB | **passes** validation via refund-negative exception; cross-border |
| TXN008 | USD transfer 3200, US | validated → low risk → **approve** |

All 8 must appear in `shared/results/` after a run.
