"""Unit tests for shared helpers."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from agents._shared import (
    build_envelope,
    mask_account,
    parse_iso,
    audit,
    reroute,
    to_money,
    utc_now_iso,
)


class TestToMoney:
    def test_parses_string_to_two_places(self):
        assert to_money("1500.5") == Decimal("1500.50")

    def test_rounds_half_up(self):
        assert to_money("1.005") == Decimal("1.01")

    def test_accepts_integer(self):
        assert to_money(100) == Decimal("100.00")

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            to_money("not-a-number")


class TestMaskAccount:
    def test_masks_to_last4(self):
        assert mask_account("ACC-1001") == "***1001"

    def test_handles_none(self):
        assert mask_account(None) == "***"

    def test_handles_empty(self):
        assert mask_account("") == "***"


class TestTime:
    def test_utc_now_iso_is_tz_aware(self):
        assert utc_now_iso().endswith("+00:00")

    def test_parse_iso_handles_z_suffix(self):
        dt = parse_iso("2026-03-16T02:47:00Z")
        assert dt.hour == 2 and dt.tzinfo is not None

    def test_parse_iso_normalises_naive_to_utc(self):
        dt = parse_iso("2026-03-16T02:47:00")
        assert dt.tzinfo is not None


class TestEnvelope:
    def test_build_envelope_has_all_fields(self):
        env = build_envelope(source_agent="a", target_agent="b", data={"x": 1})
        for field in (
            "message_id",
            "timestamp",
            "source_agent",
            "target_agent",
            "message_type",
            "data",
        ):
            assert field in env
        assert env["message_type"] == "transaction"

    def test_reroute_preserves_message_type(self):
        env = build_envelope(source_agent="a", target_agent="b", data={}, message_type="custom")
        out = reroute(env, source_agent="b", target_agent="c", data={"y": 2})
        assert out["message_type"] == "custom"
        assert out["target_agent"] == "c"
        assert out["data"] == {"y": 2}


class TestAudit:
    def test_writes_jsonl_entry(self, tmp_path):
        log = tmp_path / "audit.log"
        audit(log, agent="validator", transaction_id="TXN001", outcome="validated")
        audit(log, agent="fraud", transaction_id="TXN001", outcome="scored:0")
        lines = log.read_text().strip().splitlines()
        assert len(lines) == 2
        entry = json.loads(lines[0])
        assert entry["agent"] == "validator"
        assert entry["transaction_id"] == "TXN001"
        # No PII fields persisted.
        assert "source_account" not in entry

    def test_none_path_does_not_write(self):
        entry = audit(None, agent="a", transaction_id="T", outcome="ok")
        assert entry["outcome"] == "ok"
