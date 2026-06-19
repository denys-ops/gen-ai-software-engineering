"""Transaction Validator agent.

Checks required fields, amount sign/precision, ISO 4217 currency, and account format.
Validated messages are routed to the fraud_detector; rejected ones short-circuit to results.
"""

from __future__ import annotations

import os
import sys

# Allow running directly as `python agents/transaction_validator.py` (puts agents/ on the path)
# as well as importing as part of the package: ensure homework-6/ is importable for `config`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import config
from agents._shared import audit, parse_iso, reroute

AGENT_NAME = "transaction_validator"

REQUIRED_FIELDS = (
    "transaction_id",
    "timestamp",
    "source_account",
    "destination_account",
    "amount",
    "currency",
    "transaction_type",
)

_ACCOUNT_RE = re.compile(config.ACCOUNT_PATTERN)


def validate(transaction: dict[str, Any]) -> tuple[bool, str | None]:
    """Return (is_valid, reason). Reason is None when valid."""
    for field in REQUIRED_FIELDS:
        if transaction.get(field) in (None, ""):
            return False, f"missing_field:{field}"

    # Timestamp must be a parseable ISO-8601 string, otherwise downstream agents would crash.
    try:
        parse_iso(str(transaction["timestamp"]))
    except (ValueError, TypeError):
        return False, "invalid_timestamp"

    currency = transaction["currency"]
    if currency not in config.ISO_4217_CURRENCIES:
        return False, "unsupported_currency"

    for acct_field in ("source_account", "destination_account"):
        if not _ACCOUNT_RE.match(str(transaction[acct_field])):
            return False, f"invalid_account_format:{acct_field}"

    try:
        amount = Decimal(str(transaction["amount"]))
    except (InvalidOperation, ValueError, TypeError):
        return False, "invalid_amount"

    # Banking inputs carry at most 2 decimal places; more is malformed, not silently rounded.
    if amount.as_tuple().exponent < -2:
        return False, "too_many_decimal_places"

    txn_type = transaction["transaction_type"]
    if amount == 0:
        return False, "zero_amount"
    if amount < 0 and txn_type not in config.NEGATIVE_ALLOWED_TYPES:
        return False, "negative_amount_not_allowed"

    return True, None


def process_message(
    message: dict[str, Any], audit_log: Path | str | None = None
) -> dict[str, Any]:
    """Validate the transaction carried by ``message`` and route it onward."""
    transaction = dict(message["data"])
    txn_id = transaction.get("transaction_id", "UNKNOWN")

    is_valid, reason = validate(transaction)

    if is_valid:
        transaction["status"] = "validated"
        transaction["reason"] = None
        outcome = "validated"
        target = "fraud_detector"
    else:
        transaction["status"] = "rejected"
        transaction["reason"] = reason
        outcome = f"rejected:{reason}"
        target = "results"

    # PII-safe audit: only transaction_id + outcome are recorded; account numbers are never logged.
    audit(audit_log, agent=AGENT_NAME, transaction_id=txn_id, outcome=outcome)

    return reroute(message, source_agent=AGENT_NAME, target_agent=target, data=transaction)


def dry_run(transactions_path: str = "sample-transactions.json") -> dict[str, Any]:
    """Validate every transaction in a file WITHOUT processing the pipeline.

    Returns a report with total/valid/invalid counts and per-transaction reasons. Used by the
    `/validate-transactions` slash command (`python agents/transaction_validator.py --dry-run`).
    """
    import json

    records = json.loads(Path(transactions_path).read_text(encoding="utf-8"))
    rows = []
    valid = 0
    for record in records:
        ok, reason = validate(record)
        valid += 1 if ok else 0
        rows.append(
            {
                "transaction_id": record.get("transaction_id", "UNKNOWN"),
                "valid": ok,
                "reason": reason,
            }
        )
    return {
        "total": len(records),
        "valid": valid,
        "invalid": len(records) - valid,
        "results": rows,
    }


def _print_dry_run(report: dict[str, Any]) -> None:
    print(
        f"Validation dry-run: total={report['total']} "
        f"valid={report['valid']} invalid={report['invalid']}"
    )
    print(f"{'TXN':<8} {'VALID':<6} REASON")
    for row in report["results"]:
        print(f"{row['transaction_id']:<8} {str(row['valid']):<6} {row['reason'] or '-'}")


def main(argv: list[str] | None = None) -> int:
    import sys

    args = sys.argv[1:] if argv is None else argv
    if "--dry-run" not in args:
        print("usage: python agents/transaction_validator.py --dry-run [transactions.json]")
        return 2
    rest = [a for a in args if a != "--dry-run"]
    path = rest[0] if rest else "sample-transactions.json"
    _print_dry_run(dry_run(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
