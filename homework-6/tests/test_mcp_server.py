"""Tests for the custom FastMCP server (added after the audit).

The server's tool/resource functions are plain callables (FastMCP keeps them callable), so we
point its module-level RESULTS_DIR / SUMMARY_FILE at a tmp dir and call them directly.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SERVER_PATH = Path(__file__).resolve().parent.parent / "mcp" / "server.py"


def _load_server():
    spec = importlib.util.spec_from_file_location("pipeline_server", SERVER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def server(tmp_path, monkeypatch):
    mod = _load_server()
    results = tmp_path / "results"
    results.mkdir()
    monkeypatch.setattr(mod, "RESULTS_DIR", results)
    monkeypatch.setattr(mod, "SUMMARY_FILE", results / "summary.json")
    return mod, results


def _write_result(results: Path, txn_id: str, **data):
    payload = {"data": {"transaction_id": txn_id, **data}}
    (results / f"{txn_id}.json").write_text(json.dumps(payload))


def _write_summary(results: Path):
    summary = {
        "generated_at": "2026-03-16T10:00:00+00:00",
        "counts": {"total": 1, "approved": 1, "held": 0, "rejected": 0},
        "transactions": [
            {"transaction_id": "TXN001", "status": "validated", "risk_score": 0,
             "decision": "approve", "decision_reason": "passed_compliance", "reason": None},
        ],
    }
    (results / "summary.json").write_text(json.dumps(summary))


class TestGetTransactionStatus:
    def test_found(self, server):
        mod, results = server
        _write_result(results, "TXN001", status="validated", decision="approve",
                      source_account="ACC-1001")
        out = mod.get_transaction_status("TXN001")
        assert out["found"] is True
        assert out["status"] == "validated"
        assert out["decision"] == "approve"
        # PII (account number) is NOT surfaced.
        assert "source_account" not in out

    def test_not_found(self, server):
        mod, _ = server
        out = mod.get_transaction_status("NOPE")
        assert out["found"] is False and "error" in out


class TestListResults:
    def test_no_run(self, server):
        mod, _ = server
        out = mod.list_pipeline_results()
        assert "error" in out and out["transactions"] == []

    def test_with_summary(self, server):
        mod, results = server
        _write_summary(results)
        out = mod.list_pipeline_results()
        assert out["counts"]["total"] == 1
        assert out["transactions"][0]["transaction_id"] == "TXN001"


class TestSummaryResource:
    def test_no_run(self, server):
        mod, _ = server
        assert "No pipeline run" in mod.pipeline_summary()

    def test_with_run(self, server):
        mod, results = server
        _write_summary(results)
        text = mod.pipeline_summary()
        assert "TXN001" in text and "approved=1" in text
