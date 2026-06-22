"""Robustness / error-path tests (added after the audit).

These prove the pipeline degrades gracefully instead of aborting on dirty input.
"""

from __future__ import annotations

import json

import integrator
from agents import compliance_checker as c
from agents import fraud_detector as f
from agents import transaction_validator as v
from agents._shared import country_of


class TestInputGuards:
    def test_invalid_timestamp_rejected(self, make_txn):
        ok, reason = v.validate(make_txn(timestamp="not-a-date"))
        assert not ok and reason == "invalid_timestamp"

    def test_country_of_handles_non_dict_metadata(self):
        assert country_of({"metadata": "oops"}) is None
        assert country_of({}) is None
        assert country_of({"metadata": {"country": "DE"}}) == "DE"

    def test_fraud_survives_non_dict_metadata(self, make_txn):
        score, rules = f.score_transaction(make_txn(metadata="oops"))
        assert "cross_border" not in rules  # no crash, treated as no country

    def test_compliance_survives_non_dict_metadata(self, make_txn):
        txn = make_txn(metadata="oops")
        txn.update({"risk_score": 0, "triggered_rules": [], "flagged": False})
        decision, _ = c.decide(txn)
        assert decision == "approve"


class TestIntegratorResilience:
    def _records(self, make_txn, *specs):
        return [make_txn(transaction_id=tid, **kw) for tid, kw in specs]

    def test_bad_timestamp_does_not_crash_run(self, make_txn, tmp_path):
        path = tmp_path / "t.json"
        path.write_text(json.dumps(self._records(
            make_txn, ("OK", {}), ("BADTS", {"timestamp": "not-a-date"}))))
        base = tmp_path / "shared"
        summary = integrator.run_pipeline(str(path), base_dir=str(base))
        by_id = {t["transaction_id"]: t for t in summary["transactions"]}
        assert by_id["BADTS"]["status"] == "rejected"
        assert by_id["BADTS"]["reason"] == "invalid_timestamp"
        assert by_id["OK"]["status"] == "validated"
        assert (base / "results" / "BADTS.json").exists()

    def test_agent_crash_is_isolated(self, make_txn, tmp_path, monkeypatch):
        # Force the fraud agent to blow up on one specific transaction.
        orig = integrator.fraud_detector.process_message

        def boom(message, audit_log=None):
            if message["data"]["transaction_id"] == "BOOM":
                raise RuntimeError("kaboom")
            return orig(message, audit_log)

        monkeypatch.setattr(integrator.fraud_detector, "process_message", boom)

        path = tmp_path / "t.json"
        path.write_text(json.dumps(self._records(
            make_txn, ("OK1", {}), ("BOOM", {}), ("OK2", {}))))
        base = tmp_path / "shared"
        summary = integrator.run_pipeline(str(path), base_dir=str(base))

        assert summary["counts"]["total"] == 3
        assert summary["counts"]["errors"] == 1
        # Every transaction still produced a result file; the run completed.
        for tid in ("OK1", "BOOM", "OK2"):
            assert (base / "results" / f"{tid}.json").exists()
        boom_data = json.loads((base / "results" / "BOOM.json").read_text())["data"]
        assert boom_data["status"] == "error"
        assert boom_data["reason"].startswith("pipeline_error:")

    def test_duplicate_id_rejected_not_overwritten(self, make_txn, tmp_path):
        path = tmp_path / "t.json"
        path.write_text(json.dumps(self._records(make_txn, ("DUP", {}), ("DUP", {}))))
        base = tmp_path / "shared"
        summary = integrator.run_pipeline(str(path), base_dir=str(base))

        assert summary["counts"]["total"] == 2
        dups = [t for t in summary["transactions"] if t["reason"] == "duplicate_transaction_id"]
        assert len(dups) == 1
        # First result preserved AND the duplicate written under a distinct name.
        assert (base / "results" / "DUP.json").exists()
        assert (base / "results" / "DUP.dup1.json").exists()
