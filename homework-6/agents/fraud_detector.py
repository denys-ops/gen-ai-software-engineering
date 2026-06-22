"""Fraud Detector agent.

Assigns an additive risk score to a validated transaction using configurable rules
(high-value, off-hours, cross-border) and flags it when the score exceeds the threshold.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import config
from agents._shared import audit, country_of, parse_iso, reroute, to_money

AGENT_NAME = "fraud_detector"


def score_transaction(transaction: dict[str, Any]) -> tuple[int, list[str]]:
    """Return (risk_score, triggered_rules) from the configurable fraud rules."""
    triggered: list[str] = []
    score = 0

    amount = to_money(transaction["amount"])
    if amount > config.HIGH_VALUE_THRESHOLD:
        triggered.append("high_value")
        score += config.WEIGHT_HIGH_VALUE

    hour = parse_iso(transaction["timestamp"]).hour
    if config.OFF_HOURS_START <= hour < config.OFF_HOURS_END:
        triggered.append("off_hours")
        score += config.WEIGHT_OFF_HOURS

    country = country_of(transaction)
    if country and country != config.HOME_COUNTRY:
        triggered.append("cross_border")
        score += config.WEIGHT_CROSS_BORDER

    return score, triggered


def process_message(
    message: dict[str, Any], audit_log: Path | str | None = None
) -> dict[str, Any]:
    """Score the validated transaction in ``message`` and route it to compliance."""
    transaction = dict(message["data"])
    txn_id = transaction.get("transaction_id", "UNKNOWN")

    score, triggered = score_transaction(transaction)
    flagged = score > config.FRAUD_FLAG_THRESHOLD

    transaction["risk_score"] = score
    transaction["triggered_rules"] = triggered
    transaction["flagged"] = flagged

    outcome = f"flagged:{score}" if flagged else f"scored:{score}"
    audit(audit_log, agent=AGENT_NAME, transaction_id=txn_id, outcome=outcome)

    return reroute(
        message, source_agent=AGENT_NAME, target_agent="compliance_checker", data=transaction
    )
