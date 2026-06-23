"""Unit tests for agents/rule_engine.py — the configurable rule engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.rule_engine import clear_cache, evaluate, load_rules

# ---------------------------------------------------------------------------
# Helpers: build minimal rules inline so we never touch rules.json
# ---------------------------------------------------------------------------


def _rule(
    id: str,
    conditions: list[dict],
    action: dict | None = None,
    match: str = "all",
) -> dict:
    return {
        "id": id,
        "match": match,
        "when": conditions,
        "action": action or {"channel": "test", "priority": "low"},
    }


def _cond(field: str, op: str, value=None) -> dict:
    c: dict = {"field": field, "op": op}
    if value is not None:
        c["value"] = value
    return c


# ---------------------------------------------------------------------------
# Operator coverage
# ---------------------------------------------------------------------------


class TestOperators:
    def test_eq_match(self):
        rule = _rule("r", [_cond("status", "eq", "active")])
        assert evaluate({"status": "active"}, rules=[rule]) != []

    def test_eq_no_match(self):
        rule = _rule("r", [_cond("status", "eq", "active")])
        assert evaluate({"status": "inactive"}, rules=[rule]) == []

    def test_ne_match(self):
        rule = _rule("r", [_cond("status", "ne", "inactive")])
        assert evaluate({"status": "active"}, rules=[rule]) != []

    def test_ne_no_match(self):
        rule = _rule("r", [_cond("status", "ne", "active")])
        assert evaluate({"status": "active"}, rules=[rule]) == []

    def test_gt_match(self):
        rule = _rule("r", [_cond("score", "gt", 5)])
        assert evaluate({"score": 10}, rules=[rule]) != []

    def test_gt_no_match(self):
        rule = _rule("r", [_cond("score", "gt", 10)])
        assert evaluate({"score": 5}, rules=[rule]) == []

    def test_gt_equal_no_match(self):
        rule = _rule("r", [_cond("score", "gt", 5)])
        assert evaluate({"score": 5}, rules=[rule]) == []

    def test_gte_match_equal(self):
        rule = _rule("r", [_cond("score", "gte", 5)])
        assert evaluate({"score": 5}, rules=[rule]) != []

    def test_gte_match_greater(self):
        rule = _rule("r", [_cond("score", "gte", 5)])
        assert evaluate({"score": 10}, rules=[rule]) != []

    def test_gte_no_match(self):
        rule = _rule("r", [_cond("score", "gte", 10)])
        assert evaluate({"score": 5}, rules=[rule]) == []

    def test_lt_match(self):
        rule = _rule("r", [_cond("score", "lt", 10)])
        assert evaluate({"score": 5}, rules=[rule]) != []

    def test_lt_no_match(self):
        rule = _rule("r", [_cond("score", "lt", 5)])
        assert evaluate({"score": 10}, rules=[rule]) == []

    def test_lte_match_equal(self):
        rule = _rule("r", [_cond("score", "lte", 5)])
        assert evaluate({"score": 5}, rules=[rule]) != []

    def test_lte_no_match(self):
        rule = _rule("r", [_cond("score", "lte", 3)])
        assert evaluate({"score": 5}, rules=[rule]) == []

    def test_in_match(self):
        rule = _rule("r", [_cond("currency", "in", ["USD", "EUR"])])
        assert evaluate({"currency": "USD"}, rules=[rule]) != []

    def test_in_no_match(self):
        rule = _rule("r", [_cond("currency", "in", ["USD", "EUR"])])
        assert evaluate({"currency": "GBP"}, rules=[rule]) == []

    def test_contains_match(self):
        rule = _rule("r", [_cond("tags", "contains", "fraud")])
        assert evaluate({"tags": ["fraud", "review"]}, rules=[rule]) != []

    def test_contains_no_match(self):
        rule = _rule("r", [_cond("tags", "contains", "fraud")])
        assert evaluate({"tags": ["review"]}, rules=[rule]) == []

    def test_contains_string_match(self):
        rule = _rule("r", [_cond("reason", "contains", "hold")])
        assert evaluate({"reason": "on_hold_review"}, rules=[rule]) != []

    def test_exists_present(self):
        rule = _rule("r", [_cond("flagged", "exists")])
        assert evaluate({"flagged": True}, rules=[rule]) != []

    def test_exists_missing(self):
        rule = _rule("r", [_cond("flagged", "exists")])
        assert evaluate({}, rules=[rule]) == []

    def test_exists_none_value(self):
        # None value is "missing" for exists
        rule = _rule("r", [_cond("flagged", "exists")])
        # The field is absent entirely
        assert evaluate({"other": "x"}, rules=[rule]) == []


# ---------------------------------------------------------------------------
# Dotted-path lookup
# ---------------------------------------------------------------------------


class TestDottedPath:
    def test_nested_match(self):
        rule = _rule("r", [_cond("metadata.country", "eq", "US")])
        txn = {"metadata": {"country": "US"}}
        assert evaluate(txn, rules=[rule]) != []

    def test_nested_no_match(self):
        rule = _rule("r", [_cond("metadata.country", "eq", "US")])
        txn = {"metadata": {"country": "DE"}}
        assert evaluate(txn, rules=[rule]) == []

    def test_missing_nested_key_no_match(self):
        rule = _rule("r", [_cond("metadata.country", "eq", "US")])
        txn = {"metadata": {}}
        assert evaluate(txn, rules=[rule]) == []

    def test_missing_parent_key_no_match(self):
        rule = _rule("r", [_cond("metadata.country", "eq", "US")])
        txn = {}
        assert evaluate(txn, rules=[rule]) == []

    def test_missing_nested_exists_false(self):
        rule = _rule("r", [_cond("metadata.country", "exists")])
        assert evaluate({}, rules=[rule]) == []

    def test_present_nested_exists_true(self):
        rule = _rule("r", [_cond("metadata.country", "exists")])
        assert evaluate({"metadata": {"country": "US"}}, rules=[rule]) != []


# ---------------------------------------------------------------------------
# Match mode: all vs any
# ---------------------------------------------------------------------------


class TestMatchMode:
    def _two_cond_rule(self, match: str) -> dict:
        return _rule(
            "r",
            [_cond("a", "eq", 1), _cond("b", "eq", 2)],
            match=match,
        )

    def test_all_both_match(self):
        rule = self._two_cond_rule("all")
        assert evaluate({"a": 1, "b": 2}, rules=[rule]) != []

    def test_all_one_fail(self):
        rule = self._two_cond_rule("all")
        assert evaluate({"a": 1, "b": 99}, rules=[rule]) == []

    def test_all_neither_match(self):
        rule = self._two_cond_rule("all")
        assert evaluate({"a": 99, "b": 99}, rules=[rule]) == []

    def test_any_one_match(self):
        rule = self._two_cond_rule("any")
        assert evaluate({"a": 1, "b": 99}, rules=[rule]) != []

    def test_any_both_match(self):
        rule = self._two_cond_rule("any")
        assert evaluate({"a": 1, "b": 2}, rules=[rule]) != []

    def test_any_neither_match(self):
        rule = self._two_cond_rule("any")
        assert evaluate({"a": 99, "b": 99}, rules=[rule]) == []


# ---------------------------------------------------------------------------
# Numeric coercion for amount
# ---------------------------------------------------------------------------


class TestNumericCoercion:
    def test_amount_string_gt_threshold_matches(self):
        rule = _rule("r", [_cond("amount", "gt", 10000)])
        assert evaluate({"amount": "25000.00"}, rules=[rule]) != []

    def test_amount_string_below_threshold_no_match(self):
        rule = _rule("r", [_cond("amount", "gt", 10000)])
        assert evaluate({"amount": "9999.99"}, rules=[rule]) == []

    def test_amount_int_gt_threshold(self):
        rule = _rule("r", [_cond("amount", "gt", 10000)])
        assert evaluate({"amount": 25000}, rules=[rule]) != []

    def test_amount_float_gt_threshold(self):
        rule = _rule("r", [_cond("amount", "gt", 10000)])
        assert evaluate({"amount": 25000.00}, rules=[rule]) != []

    def test_amount_exactly_threshold_no_gt_match(self):
        rule = _rule("r", [_cond("amount", "gt", 10000)])
        assert evaluate({"amount": "10000.00"}, rules=[rule]) == []

    def test_amount_exactly_threshold_gte_match(self):
        rule = _rule("r", [_cond("amount", "gte", 10000)])
        assert evaluate({"amount": "10000.00"}, rules=[rule]) != []


# ---------------------------------------------------------------------------
# evaluate() return structure
# ---------------------------------------------------------------------------


class TestEvaluateReturnShape:
    def test_action_annotated_with_rule_id(self):
        rule = _rule("my-rule", [_cond("x", "eq", 1)], action={"channel": "ops", "priority": "high"})
        results = evaluate({"x": 1}, rules=[rule])
        assert len(results) == 1
        assert results[0]["rule_id"] == "my-rule"
        assert results[0]["channel"] == "ops"
        assert results[0]["priority"] == "high"

    def test_multiple_rules_multiple_results(self):
        rules = [
            _rule("r1", [_cond("a", "eq", 1)], action={"channel": "ch1"}),
            _rule("r2", [_cond("b", "eq", 2)], action={"channel": "ch2"}),
        ]
        results = evaluate({"a": 1, "b": 2}, rules=rules)
        assert len(results) == 2
        ids = {r["rule_id"] for r in results}
        assert ids == {"r1", "r2"}

    def test_no_match_returns_empty_list(self):
        rule = _rule("r", [_cond("x", "eq", 99)])
        assert evaluate({"x": 0}, rules=[rule]) == []

    def test_partial_match_only_matched_returned(self):
        rules = [
            _rule("r1", [_cond("a", "eq", 1)]),
            _rule("r2", [_cond("a", "eq", 99)]),
        ]
        results = evaluate({"a": 1}, rules=rules)
        assert len(results) == 1
        assert results[0]["rule_id"] == "r1"

    def test_uses_load_rules_when_no_rules_passed(self):
        # load_rules() reads rules.json which must exist; just verify it returns a list
        results = evaluate({"flagged": True})
        assert isinstance(results, list)

    def test_rule_id_injected_action_fields_present(self):
        # rule_id is injected; other action fields are preserved
        rule = _rule("x", [_cond("v", "eq", 1)], action={"channel": "ops", "extra": "yes"})
        results = evaluate({"v": 1}, rules=[rule])
        assert results[0]["rule_id"] == "x"
        assert results[0]["channel"] == "ops"
        assert results[0]["extra"] == "yes"


# ---------------------------------------------------------------------------
# load_rules — file I/O, caching, clear_cache
# ---------------------------------------------------------------------------


class TestLoadRules:
    def _write_rules(self, tmp_path: Path, rules: list) -> Path:
        p = tmp_path / "test_rules.json"
        p.write_text(json.dumps({"rules": rules}), encoding="utf-8")
        return p

    def test_loads_valid_file(self, tmp_path):
        clear_cache()
        p = self._write_rules(tmp_path, [_rule("r1", [_cond("x", "eq", 1)])])
        loaded = load_rules(p)
        assert isinstance(loaded, list)
        assert loaded[0]["id"] == "r1"

    def test_is_cached_after_first_load(self, tmp_path):
        clear_cache()
        p = self._write_rules(tmp_path, [_rule("r1", [_cond("x", "eq", 1)])])
        first = load_rules(p)
        # mutate file on disk — cached version should still be returned
        p.write_text(json.dumps({"rules": [_rule("r2", [_cond("y", "eq", 2)])]}))
        second = load_rules(p)
        assert first is second  # same object from cache

    def test_clear_cache_forces_reload(self, tmp_path):
        clear_cache()
        p = self._write_rules(tmp_path, [_rule("r1", [_cond("x", "eq", 1)])])
        load_rules(p)
        p.write_text(json.dumps({"rules": [_rule("r2", [_cond("y", "eq", 2)])]}))
        clear_cache()
        reloaded = load_rules(p)
        assert reloaded[0]["id"] == "r2"

    def teardown_method(self, method):
        clear_cache()


# ---------------------------------------------------------------------------
# Malformed rule / file error cases
# ---------------------------------------------------------------------------


class TestMalformedRules:
    """Validation runs on load_rules(), so malformed rules must be tested via file loading."""

    def _write(self, tmp_path: Path, rules: list) -> Path:
        p = tmp_path / "rules.json"
        p.write_text(json.dumps({"rules": rules}), encoding="utf-8")
        return p

    def test_missing_id_raises(self, tmp_path):
        clear_cache()
        bad = {"match": "all", "when": [_cond("x", "eq", 1)], "action": {"channel": "t"}}
        p = self._write(tmp_path, [bad])
        with pytest.raises(ValueError, match="missing 'id'"):
            load_rules(p)

    def test_empty_when_raises(self, tmp_path):
        clear_cache()
        bad = {"id": "r", "when": [], "action": {"channel": "t"}}
        p = self._write(tmp_path, [bad])
        with pytest.raises(ValueError, match="non-empty 'when'"):
            load_rules(p)

    def test_missing_when_raises(self, tmp_path):
        clear_cache()
        bad = {"id": "r", "action": {"channel": "t"}}
        p = self._write(tmp_path, [bad])
        with pytest.raises(ValueError):
            load_rules(p)

    def test_unknown_op_raises(self, tmp_path):
        clear_cache()
        bad = {"id": "r", "when": [{"field": "x", "op": "BOGUS", "value": 1}], "action": {"channel": "t"}}
        p = self._write(tmp_path, [bad])
        with pytest.raises(ValueError, match="unknown operator"):
            load_rules(p)

    def test_missing_action_raises(self, tmp_path):
        clear_cache()
        bad = {"id": "r", "when": [_cond("x", "eq", 1)]}
        p = self._write(tmp_path, [bad])
        with pytest.raises(ValueError, match="'action'"):
            load_rules(p)

    def test_action_not_dict_raises(self, tmp_path):
        clear_cache()
        bad = {"id": "r", "when": [_cond("x", "eq", 1)], "action": "send_email"}
        p = self._write(tmp_path, [bad])
        with pytest.raises(ValueError, match="'action'"):
            load_rules(p)

    def test_bad_match_value_raises(self, tmp_path):
        clear_cache()
        bad = {"id": "r", "match": "both", "when": [_cond("x", "eq", 1)], "action": {"channel": "t"}}
        p = self._write(tmp_path, [bad])
        with pytest.raises(ValueError, match="invalid match"):
            load_rules(p)

    def test_file_not_found_raises(self, tmp_path):
        clear_cache()
        with pytest.raises(ValueError, match="rules file not found"):
            load_rules(tmp_path / "nonexistent.json")

    def test_invalid_json_raises(self, tmp_path):
        clear_cache()
        p = tmp_path / "bad.json"
        p.write_text("not valid json {{{", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid JSON"):
            load_rules(p)

    def test_top_level_not_dict_raises(self, tmp_path):
        clear_cache()
        p = tmp_path / "list.json"
        p.write_text(json.dumps([{"id": "r"}]), encoding="utf-8")
        with pytest.raises(ValueError, match="top-level 'rules' list"):
            load_rules(p)

    def test_top_level_dict_no_rules_key_raises(self, tmp_path):
        clear_cache()
        p = tmp_path / "nokey.json"
        p.write_text(json.dumps({"not_rules": []}), encoding="utf-8")
        with pytest.raises(ValueError, match="top-level 'rules' list"):
            load_rules(p)

    def teardown_method(self, method):
        clear_cache()
