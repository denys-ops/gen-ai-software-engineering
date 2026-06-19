"""Integration test for the full pipeline via the integrator.

Isolated from the real ./shared directory by writing into tmp_path.
"""

from __future__ import annotations

import json

import pytest

import integrator

SAMPLE = [
    # clean -> approve
    {"transaction_id": "TXN001", "timestamp": "2026-03-16T09:00:00Z",
     "source_account": "ACC-1001", "destination_account": "ACC-2001", "amount": "1500.00",
     "currency": "USD", "transaction_type": "transfer", "metadata": {"country": "US"}},
    # high-value wire -> hold
    {"transaction_id": "TXN002", "timestamp": "2026-03-16T09:15:00Z",
     "source_account": "ACC-1002", "destination_account": "ACC-3001", "amount": "25000.00",
     "currency": "USD", "transaction_type": "wire_transfer", "metadata": {"country": "US"}},
    # invalid currency -> rejected
    {"transaction_id": "TXN006", "timestamp": "2026-03-16T10:05:00Z",
     "source_account": "ACC-1006", "destination_account": "ACC-7700", "amount": "200.00",
     "currency": "XYZ", "transaction_type": "transfer", "metadata": {"country": "US"}},
    # refund negative -> approve
    {"transaction_id": "TXN007", "timestamp": "2026-03-16T10:10:00Z",
     "source_account": "ACC-1007", "destination_account": "ACC-8800", "amount": "-100.00",
     "currency": "GBP", "transaction_type": "refund", "metadata": {"country": "GB"}},
]


@pytest.fixture
def sample_file(tmp_path):
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(SAMPLE))
    return path


def test_all_transactions_reach_results(sample_file, tmp_path):
    base = tmp_path / "shared"
    summary = integrator.run_pipeline(str(sample_file), base_dir=str(base))

    assert summary["counts"]["total"] == 4
    # Every transaction has a result file.
    for txn in SAMPLE:
        assert (base / "results" / f"{txn['transaction_id']}.json").exists()
    # Lifecycle dirs are drained.
    for stage in ("input", "processing", "output"):
        assert not list((base / stage).glob("*.json"))


def test_expected_outcomes(sample_file, tmp_path):
    base = tmp_path / "shared"
    summary = integrator.run_pipeline(str(sample_file), base_dir=str(base))
    by_id = {t["transaction_id"]: t for t in summary["transactions"]}

    assert by_id["TXN001"]["decision"] == "approve"
    assert by_id["TXN002"]["decision"] == "hold"
    assert by_id["TXN006"]["status"] == "rejected"
    assert by_id["TXN006"]["reason"] == "unsupported_currency"
    assert by_id["TXN007"]["decision"] == "approve"


def test_summary_and_audit_written(sample_file, tmp_path):
    base = tmp_path / "shared"
    integrator.run_pipeline(str(sample_file), base_dir=str(base))
    assert (base / "results" / "summary.json").exists()
    assert (base / "results" / "audit.log").exists()


def test_rejected_short_circuits_no_score(sample_file, tmp_path):
    base = tmp_path / "shared"
    integrator.run_pipeline(str(sample_file), base_dir=str(base))
    rejected = json.loads((base / "results" / "TXN006.json").read_text())
    # Validator short-circuited: fraud fields never added.
    assert "risk_score" not in rejected["data"]


def test_main_entrypoint(sample_file, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["integrator.py", str(sample_file)])
    # main() writes into ./shared; run from a tmp cwd to stay isolated.
    monkeypatch.chdir(sample_file.parent)
    rc = integrator.main()
    assert rc == 0
    assert "Pipeline run summary" in capsys.readouterr().out
