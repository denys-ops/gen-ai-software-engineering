# Multi-Agent Banking Transaction Pipeline — Specification

> Ingest the information from this file, implement the Low-Level Tasks, and generate the code that
> will satisfy the High- and Mid-Level Objectives.
>
> **Companion:** domain invariants, message protocol, and agent contracts live in
> [`agents.md`](./agents.md); the rubric authority is [`TASKS.md`](./TASKS.md).

---

## 1. High-Level Objective

Build a file-based multi-agent banking pipeline that ingests raw transactions from
`sample-transactions.json` and runs each one through three sequential agents — a validator, a
fraud detector, and a compliance checker — writing a per-transaction approve/hold/reject outcome
and a run summary to `shared/results/`.

---

## 2. Mid-Level Objectives

Concrete, testable requirements (each verifiable against the 8 sample transactions):

1. **Validation gate** — Every transaction is checked for required fields, ISO 4217 currency,
   `ACC-XXXX` account format, and `amount` parsed as `Decimal` with `amount > 0` (except
   `transaction_type == "refund"`, where a negative amount is allowed; zero is never valid).
   Invalid transactions — e.g. **TXN006** (currency `XYZ`) — are written to `shared/results/`
   with a structured `reason` field and never advance to later agents.
2. **Configurable fraud scoring** — Each validated transaction receives an **additive numeric
   `risk_score`** from env-overridable rule weights (high-value `> 10,000`; off-hours 00:00–05:00;
   cross-border vs. `HOME_COUNTRY`), correctly flagging **TXN002** and **TXN005** (high-value) and
   **TXN004** (off-hours + cross-border DE), while **TXN003** (9,999.99) stays under the threshold.
3. **Compliance decision** — Each transaction reaching the compliance agent gets a terminal
   `decision` of `approve`, `hold`, or `reject`, applying extra scrutiny to `wire_transfer` and
   cross-border transactions and holding any transaction on the sanctioned-country list.
4. **Auditable messaging** — Agents communicate only via JSON message files through
   `shared/{input,processing,output,results}/` using the standard envelope
   (`message_id` uuid4, ISO-8601 `timestamp`, `source_agent`, `target_agent`, `message_type`,
   `data`), and every agent action appends an audit entry of `timestamp + agent + transaction_id +
   outcome` with account numbers masked to last-4.
5. **Deterministic run + coverage** — Running `python integrator.py` processes all 8 sample
   transactions end-to-end with every transaction appearing in `shared/results/`, emits a pipeline
   summary report (counts of approved / held / rejected / flagged), and the test suite reaches
   **≥ 90% coverage**.

---

## 3. Implementation Notes

- **Money:** use `decimal.Decimal` for all amounts, parsing from the JSON **string** field
  (`Decimal("1500.00")`); apply `ROUND_HALF_UP`; never use `float`.
- **Currency:** validate against an ISO 4217 three-letter uppercase allowlist; unknown → reject.
- **Refund exception:** `amount > 0` required for all types except `refund` (negative allowed);
  `amount == 0` always invalid.
- **Configuration:** thresholds and weights live in `config.py` and are env-overridable
  (`HIGH_VALUE_THRESHOLD`, `OFF_HOURS_START/END`, `HOME_COUNTRY`, weight + flag-threshold vars).
  Defaults: high-value `10000`, off-hours `00:00–05:00`, `HOME_COUNTRY=US`. Never hardcode in agents.
- **Audit logging:** append-only JSONL; one line per action `{timestamp, agent, transaction_id,
  outcome}`; account numbers masked to last-4; treat account numbers **and account-holder names**
  as sensitive — no plaintext PII (account numbers, names, descriptions) in logs.
- **Message envelope:** `{message_id, timestamp, source_agent, target_agent, message_type, data}`;
  `message_id = uuid4`, `timestamp = datetime.now(timezone.utc)` ISO-8601.
- **Flow:** sequential, synchronous integrator (validator → fraud_detector → compliance_checker);
  a validator reject short-circuits straight to `shared/results/`.
- **Stack:** Python 3.11, `uv`, FastMCP 3.x (Task 4), pytest + pytest-cov; snake_case modules,
  `process_message(message: dict) -> dict` entrypoint per agent.

---

## 4. Context

### Beginning context
- `homework-6/sample-transactions.json` — 8 raw transaction records (snake_case fields; `amount`
  as a string). No agent code, no `shared/` directories, no `config.py`.

### Ending context
- `homework-6/integrator.py` — orchestrator.
- `homework-6/agents/transaction_validator.py`, `agents/fraud_detector.py`,
  `agents/compliance_checker.py` — the three runtime agents.
- `homework-6/config.py` — thresholds/weights (env-overridable).
- `homework-6/shared/{input,processing,output,results}/` — populated during the run.
- Per-transaction result JSON files + `shared/results/summary.json` — the run report; **all 8
  transactions present** in `shared/results/`.
- `homework-6/tests/` — unit tests per agent + 1 integration test, **coverage ≥ 90%**
  (hard gate ≥ 80% blocks push).

---

## 5. Low-Level Tasks

One entry per agent, in pipeline order (the integrator is the orchestrator).

```
Task: Integrator / Orchestrator
Prompt: "Create homework-6/integrator.py: an orchestrator that (1) creates
  shared/{input,processing,output,results}/ if absent, (2) loads sample-transactions.json,
  (3) wraps each transaction in the standard message envelope and drops it in shared/input/,
  (4) runs transaction_validator, then fraud_detector, then compliance_checker sequentially and
  synchronously, moving each message input->processing->output between stages, (5) writes terminal
  outcomes and a summary report to shared/results/, and (6) prints a run summary. Use Decimal for
  money, uuid4 message_id, ISO-8601 UTC timestamps, and an append-only audit log with account
  numbers masked to last-4."
File to CREATE: homework-6/integrator.py
Function to CREATE: run_pipeline(transactions_path: str = "sample-transactions.json") -> dict
Details: Sets up dirs; builds envelopes; calls each agent's process_message in order; on a validator
  reject, short-circuits the message straight to shared/results/ with its reason; aggregates counts
  (validated/rejected/flagged/approved/held) into shared/results/summary.json; never mutates the
  original sample file.
```

```
Task: Transaction Validator
Prompt: "Create homework-6/agents/transaction_validator.py: validates one transaction message.
  Check all required fields present (transaction_id, timestamp, source_account,
  destination_account, amount, currency, transaction_type), parse amount as Decimal, enforce
  amount > 0 EXCEPT when transaction_type == 'refund' (negative allowed, zero never allowed),
  validate currency against an ISO 4217 allowlist, and validate both accounts against ^ACC-\d{4}$.
  Return a new message with status 'validated' or 'rejected' plus a reason. Use Decimal, never
  float; mask accounts to last-4 in any log."
File to CREATE: homework-6/agents/transaction_validator.py
Function to CREATE: process_message(message: dict) -> dict
Details: Rejects TXN006 (currency XYZ) with reason 'unsupported_currency'; passes TXN007 (refund,
  -100.00 GBP) via the refund exception; targets validated messages at fraud_detector and rejected
  messages at results; writes an audit entry {timestamp, agent, transaction_id, outcome}.
```

```
Task: Fraud Detector
Prompt: "Create homework-6/agents/fraud_detector.py: assigns an additive numeric risk score to a
  validated transaction using configurable, env-overridable rules from config.py — high_value
  (amount > high_value_threshold, default 10000), off_hours (timestamp hour within 00:00-05:00 UTC),
  and cross_border (metadata.country != HOME_COUNTRY). Sum the matched rule weights into risk_score,
  attach the list of triggered rules, set a 'flagged' boolean when the score exceeds the flag
  threshold, and forward the message to compliance_checker."
File to CREATE: homework-6/agents/fraud_detector.py
Function to CREATE: process_message(message: dict) -> dict
Details: Flags TXN002 and TXN005 (high_value), TXN004 (off_hours + cross_border DE); leaves TXN003
  (9999.99) below the high_value threshold; reads thresholds/weights from config.py (env
  overridable); adds risk_score, triggered_rules, flagged to message.data; writes an audit entry.
```

```
Task: Compliance Checker
Prompt: "Create homework-6/agents/compliance_checker.py: makes the terminal compliance decision
  (approve | hold | reject) for a fraud-scored transaction. Apply extra scrutiny to wire_transfer
  and cross-border transactions, hold any transaction matching a sanctioned-country flag list, hold
  high-risk fraud-flagged transactions, and otherwise approve. Write the final outcome message to
  shared/results/."
File to CREATE: homework-6/agents/compliance_checker.py
Function to CREATE: process_message(message: dict) -> dict
Details: Holds high-value wires TXN002/TXN005 for manual review, approves clean low-risk
  transactions (TXN001, TXN008), evaluates cross-border TXN004/TXN007 against the sanctioned list,
  sets decision + decision_reason on message.data, and writes {transaction_id}.json plus an audit
  entry into shared/results/.
```
