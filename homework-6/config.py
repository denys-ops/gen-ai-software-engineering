"""Configuration for the multi-agent banking pipeline.

All fraud/compliance thresholds are env-overridable so behaviour can be tuned without code edits
(env wins over the default). See agents.md section 5.
"""

from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation

# --- Currency -------------------------------------------------------------------------

# ISO 4217 allowlist (subset sufficient for the sample data + common majors).
ISO_4217_CURRENCIES: frozenset[str] = frozenset(
    {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "SEK", "NOK"}
)

# Account number format, e.g. ACC-1001.
ACCOUNT_PATTERN: str = r"^ACC-\d{4}$"

# Transaction types that are allowed to carry a negative amount (e.g. a reversal).
NEGATIVE_ALLOWED_TYPES: frozenset[str] = frozenset({"refund"})

# Path to the configurable notification rule set (rule engine). Relative paths resolve against the
# homework-6 root in agents/rule_engine.py; env wins so the rules file can be swapped without edits.
RULES_PATH: str = os.environ.get("RULES_PATH", "rules.json")


def _get_decimal(name: str, default: str) -> Decimal:
    raw = os.environ.get(name, default)
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(f"invalid decimal value for {name!r}: {raw!r}") from exc


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"invalid integer value for {name!r}: {raw!r}") from exc


def _get_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


# --- Fraud-detection rules (env-overridable) ------------------------------------------

# Amount strictly greater than this is "high value".
HIGH_VALUE_THRESHOLD: Decimal = _get_decimal("HIGH_VALUE_THRESHOLD", "10000")

# Off-hours window, inclusive start hour .. exclusive end hour (UTC). Default 00:00-05:00.
OFF_HOURS_START: int = _get_int("OFF_HOURS_START", 0)
OFF_HOURS_END: int = _get_int("OFF_HOURS_END", 5)

# Home country; transactions whose metadata.country differs are "cross-border".
HOME_COUNTRY: str = _get_str("HOME_COUNTRY", "US")

# Additive risk weights per triggered rule.
WEIGHT_HIGH_VALUE: int = _get_int("WEIGHT_HIGH_VALUE", 50)
WEIGHT_CROSS_BORDER: int = _get_int("WEIGHT_CROSS_BORDER", 30)
WEIGHT_OFF_HOURS: int = _get_int("WEIGHT_OFF_HOURS", 20)

# Risk score strictly greater than this flags the transaction for review.
FRAUD_FLAG_THRESHOLD: int = _get_int("FRAUD_FLAG_THRESHOLD", 40)

# --- Compliance rules -----------------------------------------------------------------

# Country codes that are always held for manual review.
SANCTIONED_COUNTRIES: frozenset[str] = frozenset(
    c for c in _get_str("SANCTIONED_COUNTRIES", "IR,KP,SY,CU").split(",") if c
)

# Transaction types subject to extra compliance scrutiny.
HIGH_SCRUTINY_TYPES: frozenset[str] = frozenset({"wire_transfer"})

# --- Flexible pipeline: enable/disable stages -----------------------------------------

# Ordered registry of optional stages run after the always-on transaction_validator gate.
DEFAULT_STAGES: tuple[str, ...] = ("fraud_detector", "compliance_checker", "notification_agent")


def resolve_stages(names: object = None) -> tuple[str, ...]:
    """Validate and canonically order a stage selection.

    ``names`` may be None (defaults to ENABLED_STAGES at runtime — here, DEFAULT_STAGES), a
    comma-separated string, or an iterable of names. Blanks are dropped; unknown names raise
    ValueError (callers turn this into a clear startup error or an HTTP 400). The validator is
    never included — it is the always-on entry gate. The result preserves DEFAULT_STAGES order.
    """
    raw: object = DEFAULT_STAGES if names is None else names
    parts = raw.split(",") if isinstance(raw, str) else list(raw)
    requested = [str(s).strip() for s in parts if str(s).strip()]
    unknown = [s for s in requested if s not in DEFAULT_STAGES]
    if unknown:
        raise ValueError(
            f"unknown pipeline stage(s): {unknown}; valid: {list(DEFAULT_STAGES)}"
        )
    return tuple(s for s in DEFAULT_STAGES if s in requested)


# Env-overridable default selection. A bad ENABLED_STAGES value surfaces as a clear startup error.
ENABLED_STAGES: tuple[str, ...] = resolve_stages(
    _get_str("ENABLED_STAGES", ",".join(DEFAULT_STAGES))
)
