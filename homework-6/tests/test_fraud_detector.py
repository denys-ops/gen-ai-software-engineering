"""Unit tests for the Fraud Detector agent."""

from __future__ import annotations

import config
from agents import fraud_detector as f


class TestScore:
    def test_clean_low_risk(self, make_txn):
        score, rules = f.score_transaction(make_txn())
        assert score == 0 and rules == []

    def test_high_value_flag(self, make_txn):
        score, rules = f.score_transaction(make_txn(amount="25000.00"))
        assert "high_value" in rules
        assert score == config.WEIGHT_HIGH_VALUE

    def test_boundary_not_high_value(self, make_txn):
        # Exactly the threshold is NOT high value (strictly greater).
        score, rules = f.score_transaction(make_txn(amount="10000.00"))
        assert "high_value" not in rules

    def test_off_hours(self, make_txn):
        _, rules = f.score_transaction(make_txn(timestamp="2026-03-16T02:47:00Z"))
        assert "off_hours" in rules

    def test_off_hours_end_exclusive(self, make_txn):
        _, rules = f.score_transaction(make_txn(timestamp="2026-03-16T05:00:00Z"))
        assert "off_hours" not in rules

    def test_cross_border(self, make_txn):
        _, rules = f.score_transaction(make_txn(metadata={"country": "DE"}))
        assert "cross_border" in rules

    def test_missing_metadata_no_cross_border(self, make_txn):
        txn = make_txn()
        del txn["metadata"]
        _, rules = f.score_transaction(txn)
        assert "cross_border" not in rules

    def test_additive_multiple_rules(self, make_txn):
        score, rules = f.score_transaction(
            make_txn(amount="25000.00", timestamp="2026-03-16T02:00:00Z", metadata={"country": "DE"})
        )
        assert set(rules) == {"high_value", "off_hours", "cross_border"}
        assert score == (
            config.WEIGHT_HIGH_VALUE + config.WEIGHT_OFF_HOURS + config.WEIGHT_CROSS_BORDER
        )


class TestProcessMessage:
    def test_flags_high_value(self, make_message):
        out = f.process_message(make_message(target="fraud_detector", amount="25000.00"))
        assert out["data"]["flagged"] is True
        assert out["target_agent"] == "compliance_checker"

    def test_not_flagged_low_risk(self, make_message):
        out = f.process_message(make_message(target="fraud_detector"))
        assert out["data"]["flagged"] is False
        assert out["data"]["risk_score"] == 0
