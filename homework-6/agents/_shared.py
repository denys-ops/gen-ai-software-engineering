"""Shared helpers for the pipeline agents: money, time, message envelope, audit, masking.

Centralises the domain invariants from agents.md so each agent stays small and consistent.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

TWO_PLACES = Decimal("0.01")

# --- Time -----------------------------------------------------------------------------


def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string (always timezone-aware)."""
    return datetime.now(timezone.utc).isoformat()


def parse_iso(timestamp: str) -> datetime:
    """Parse an ISO-8601 timestamp. Python 3.11 fromisoformat handles the 'Z' suffix.

    The result is normalised to UTC so callers can read .hour consistently.
    """
    dt = datetime.fromisoformat(timestamp)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# --- Money ----------------------------------------------------------------------------


def to_money(amount: Any) -> Decimal:
    """Coerce a value (string preferred) into a 2-dp Decimal.

    Amounts are parsed from strings to avoid binary-float drift, then quantised to two
    decimal places with banker-free ROUND_HALF_UP semantics via quantize().
    """
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"invalid monetary amount: {amount!r}") from exc
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


# --- PII masking ----------------------------------------------------------------------


def mask_account(account: str | None) -> str:
    """Mask an account number to last-4 (ACC-1001 -> ***1001).

    Used wherever an account number would otherwise be surfaced in a log or message.
    """
    if not account:
        return "***"
    return "***" + account[-4:]


def country_of(transaction: dict[str, Any]) -> str | None:
    """Safely read metadata.country, tolerating a missing or non-dict ``metadata``."""
    meta = transaction.get("metadata")
    return meta.get("country") if isinstance(meta, dict) else None


# --- Message envelope -----------------------------------------------------------------


def build_envelope(
    *,
    source_agent: str,
    target_agent: str,
    data: dict[str, Any],
    message_type: str = "transaction",
) -> dict[str, Any]:
    """Create a standard pipeline message envelope (see agents.md section 3)."""
    return {
        "message_id": str(uuid.uuid4()),
        "timestamp": utc_now_iso(),
        "source_agent": source_agent,
        "target_agent": target_agent,
        "message_type": message_type,
        "data": data,
    }


def reroute(
    message: dict[str, Any],
    *,
    source_agent: str,
    target_agent: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Return a new envelope carrying updated data, fresh id/timestamp, same message_type."""
    return build_envelope(
        source_agent=source_agent,
        target_agent=target_agent,
        data=data,
        message_type=message.get("message_type", "transaction"),
    )


# --- Audit log ------------------------------------------------------------------------


def audit(
    log_path: Path | str | None,
    *,
    agent: str,
    transaction_id: str,
    outcome: str,
) -> dict[str, Any]:
    """Append one append-only JSONL audit entry and return it.

    No PII is written: only the transaction id and the outcome. If ``log_path`` is None the
    entry is built and returned but not persisted (useful for dry-run / tests).
    """
    entry = {
        "timestamp": utc_now_iso(),
        "agent": agent,
        "transaction_id": transaction_id,
        "outcome": outcome,
    }
    if log_path is not None:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    return entry
