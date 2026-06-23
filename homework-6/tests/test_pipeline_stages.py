"""Tests for the flexible stage system: config.resolve_stages + integrator.process_one/run_pipeline."""

from __future__ import annotations

import json

import pytest

import config
import integrator


# ---------------------------------------------------------------------------
# config.resolve_stages
# ---------------------------------------------------------------------------


class TestResolveStages:
    def test_none_returns_default_stages(self):
        assert config.resolve_stages(None) == config.DEFAULT_STAGES

    def test_single_stage_string(self):
        assert config.resolve_stages("fraud_detector") == ("fraud_detector",)

    def test_single_stage_iterable(self):
        assert config.resolve_stages(["fraud_detector"]) == ("fraud_detector",)

    def test_csv_string_parsed(self):
        result = config.resolve_stages("fraud_detector,compliance_checker")
        assert result == ("fraud_detector", "compliance_checker")

    def test_order_preserved_regardless_of_input_order(self):
        # Input lists notification_agent first, but DEFAULT_STAGES order should win.
        result = config.resolve_stages("notification_agent,fraud_detector")
        # Default order: fraud_detector < compliance_checker < notification_agent
        assert result.index("fraud_detector") < result.index("notification_agent")

    def test_blanks_dropped(self):
        result = config.resolve_stages("fraud_detector,,notification_agent")
        assert "" not in result
        assert "fraud_detector" in result
        assert "notification_agent" in result

    def test_whitespace_stripped(self):
        result = config.resolve_stages("fraud_detector , compliance_checker")
        assert "fraud_detector" in result
        assert "compliance_checker" in result

    def test_unknown_name_raises_value_error(self):
        with pytest.raises(ValueError, match="unknown pipeline stage"):
            config.resolve_stages("bogus")

    def test_multiple_unknown_raises(self):
        with pytest.raises(ValueError):
            config.resolve_stages("foo,bar")

    def test_all_three_stages(self):
        result = config.resolve_stages("fraud_detector,compliance_checker,notification_agent")
        assert result == config.DEFAULT_STAGES

    def test_just_notification_agent(self):
        result = config.resolve_stages("notification_agent")
        assert result == ("notification_agent",)

    def test_validator_not_in_default_stages(self):
        # transaction_validator is the always-on gate, not in the configurable set
        assert "transaction_validator" not in config.DEFAULT_STAGES

    def test_validator_name_raises_as_unknown(self):
        with pytest.raises(ValueError):
            config.resolve_stages("transaction_validator")


# ---------------------------------------------------------------------------
# integrator.process_one — stage isolation
# ---------------------------------------------------------------------------


class TestProcessOne:
    def test_default_stages_run_all(self, make_txn, tmp_path):
        record = make_txn()
        result = integrator.process_one(record, base_dir=str(tmp_path))
        # Full default pipeline: validator + fraud + compliance + notification
        assert "risk_score" in result
        assert "decision" in result
        assert "notifications" in result

    def test_fraud_only_has_risk_score_no_decision(self, make_txn, tmp_path):
        record = make_txn()
        result = integrator.process_one(record, base_dir=str(tmp_path), stages=["fraud_detector"])
        assert "risk_score" in result
        # compliance_checker never ran
        assert "decision" not in result
        # notification_agent never ran
        assert "notifications" not in result

    def test_fraud_only_result_coherent(self, make_txn, tmp_path):
        record = make_txn()
        result = integrator.process_one(record, base_dir=str(tmp_path), stages=["fraud_detector"])
        assert result.get("status") == "validated"
        assert "flagged" in result

    def test_fraud_and_compliance_no_notifications(self, make_txn, tmp_path):
        record = make_txn()
        result = integrator.process_one(
            record,
            base_dir=str(tmp_path),
            stages=["fraud_detector", "compliance_checker"],
        )
        assert "risk_score" in result
        assert "decision" in result
        assert "notifications" not in result

    def test_notification_only_attaches_notifications(self, make_txn, tmp_path):
        record = make_txn()
        result = integrator.process_one(
            record, base_dir=str(tmp_path), stages=["notification_agent"]
        )
        assert "notifications" in result

    def test_csv_stage_override(self, make_txn, tmp_path):
        record = make_txn()
        result = integrator.process_one(
            record, base_dir=str(tmp_path), stages="fraud_detector"
        )
        assert "risk_score" in result
        assert "decision" not in result

    def test_unknown_stage_raises_value_error(self, make_txn, tmp_path):
        record = make_txn()
        with pytest.raises(ValueError, match="unknown pipeline stage"):
            integrator.process_one(record, base_dir=str(tmp_path), stages=["bogus"])

    def test_rejected_transaction_short_circuits(self, make_txn, tmp_path):
        # Invalid currency causes rejection in validator — no downstream stages run
        record = make_txn(currency="XYZ")
        result = integrator.process_one(record, base_dir=str(tmp_path))
        assert result["status"] == "rejected"
        assert "risk_score" not in result


# ---------------------------------------------------------------------------
# integrator.run_pipeline — full batch with notified count
# ---------------------------------------------------------------------------


class TestRunPipeline:
    def _write_sample(self, tmp_path, records):
        p = tmp_path / "batch.json"
        p.write_text(json.dumps(records), encoding="utf-8")
        return p

    def test_summary_has_notified_key(self, make_txn, tmp_path):
        records = [make_txn(transaction_id="TXN-A")]
        path = self._write_sample(tmp_path, records)
        base = tmp_path / "shared"
        summary = integrator.run_pipeline(str(path), base_dir=str(base))
        assert "notified" in summary["counts"]

    def test_notified_count_increments_for_flagged(self, make_txn, tmp_path):
        # A high-value wire triggers flagging -> notifications in rules.json
        records = [
            make_txn(
                transaction_id="TXN-HV",
                amount="25000.00",
                transaction_type="wire_transfer",
            ),
            make_txn(transaction_id="TXN-LOW", amount="100.00"),
        ]
        path = self._write_sample(tmp_path, records)
        base = tmp_path / "shared"
        summary = integrator.run_pipeline(str(path), base_dir=str(base))
        # At least the high-value wire should have produced a notification
        assert summary["counts"]["notified"] >= 1

    def test_clean_transaction_zero_notified(self, make_txn, tmp_path):
        # A completely clean small-amount transaction should produce zero notifications
        records = [
            make_txn(
                transaction_id="TXN-CLEAN",
                amount="100.00",
                transaction_type="transfer",
                metadata={"channel": "online", "country": "US"},
            )
        ]
        path = self._write_sample(tmp_path, records)
        base = tmp_path / "shared"
        summary = integrator.run_pipeline(str(path), base_dir=str(base))
        assert summary["counts"]["notified"] == 0

    def test_uses_real_sample_transactions_file(self, tmp_path):
        # Smoke-test: run the real sample file to ensure default pipeline works end-to-end
        import os

        sample = (
            "/Users/almin/PycharmProjects/gen-ai-software-engineering/homework-6/sample-transactions.json"
        )
        if not os.path.exists(sample):
            pytest.skip("sample-transactions.json not found")
        base = tmp_path / "shared"
        summary = integrator.run_pipeline(sample, base_dir=str(base))
        counts = summary["counts"]
        assert counts["total"] > 0
        assert "notified" in counts
