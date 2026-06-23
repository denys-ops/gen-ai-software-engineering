"""Generic, configurable rule engine.

Evaluates a transaction dict against externally-defined rules loaded from a JSON file (default
``rules.json``), so notification/alerting behaviour can be tuned without code edits. Each rule is::

    {
      "id": "high-fraud",
      "match": "all" | "any",          # how to combine the conditions (default "all")
      "when": [{"field": "...", "op": "...", "value": ...}, ...],
      "action": { ...arbitrary action payload (channel/priority/message/...)... }
    }

A field path supports dotted access (``metadata.country``). Money-like fields are coerced so a
string ``amount`` compares numerically. Operators: eq, ne, gt, gte, lt, lte, in, contains, exists.

The engine is pure apart from loading the rules file; malformed rules raise a clear ValueError.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import config
from agents._shared import to_money

# homework-6 root (parent of agents/) — relative RULES_PATH resolves against this, like mcp/server.py.
_ROOT = Path(__file__).resolve().parent.parent

# Fields whose values are monetary and should be compared as numbers, not strings.
_MONEY_FIELDS = frozenset({"amount"})

_rules_cache: dict[str, list[dict[str, Any]]] = {}


def _resolve_path(path: str | Path | None) -> Path:
    raw = Path(path) if path is not None else Path(config.RULES_PATH)
    return raw if raw.is_absolute() else _ROOT / raw


def load_rules(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load and validate the rule list from ``path`` (default ``config.RULES_PATH``). Cached by path."""
    resolved = _resolve_path(path)
    key = str(resolved)
    if key in _rules_cache:
        return _rules_cache[key]

    try:
        document = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"rules file not found: {resolved}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in rules file {resolved}: {exc}") from exc

    rules = document.get("rules") if isinstance(document, dict) else None
    if not isinstance(rules, list):
        raise ValueError(f"rules file {resolved} must contain a top-level 'rules' list")
    for rule in rules:
        _validate_rule(rule)

    _rules_cache[key] = rules
    return rules


def clear_cache() -> None:
    """Drop the rules cache (used by tests that swap rules files)."""
    _rules_cache.clear()


_VALID_OPS = frozenset({"eq", "ne", "gt", "gte", "lt", "lte", "in", "contains", "exists"})


def _validate_rule(rule: Any) -> None:
    if not isinstance(rule, dict):
        raise ValueError(f"each rule must be an object, got {type(rule).__name__}")
    if "id" not in rule:
        raise ValueError(f"rule missing 'id': {rule}")
    match = rule.get("match", "all")
    if match not in ("all", "any"):
        raise ValueError(f"rule {rule['id']!r} has invalid match {match!r} (expected all|any)")
    conditions = rule.get("when")
    if not isinstance(conditions, list) or not conditions:
        raise ValueError(f"rule {rule['id']!r} must have a non-empty 'when' list")
    for cond in conditions:
        if not isinstance(cond, dict) or "field" not in cond or "op" not in cond:
            raise ValueError(f"rule {rule['id']!r} has a malformed condition: {cond}")
        if cond["op"] not in _VALID_OPS:
            raise ValueError(
                f"rule {rule['id']!r} uses unknown operator {cond['op']!r}; valid: {sorted(_VALID_OPS)}"
            )
    if "action" not in rule or not isinstance(rule["action"], dict):
        raise ValueError(f"rule {rule['id']!r} must have an 'action' object")


def _get_field(transaction: dict[str, Any], field: str) -> Any:
    """Safely resolve a dotted field path, tolerating missing/non-dict intermediate values."""
    current: Any = transaction
    for part in field.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _coerce_pair(field: str, actual: Any, expected: Any) -> tuple[Any, Any]:
    """For money fields (and numeric comparisons), coerce both sides to Decimal where possible."""
    if field in _MONEY_FIELDS:
        try:
            return to_money(actual), to_money(expected)
        except (ValueError, InvalidOperation):
            return actual, expected
    return actual, expected


def _to_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _compare(op: str, actual: Any, expected: Any) -> bool:
    if op == "exists":
        return actual is not None
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "in":
        return isinstance(expected, (list, tuple, set, str)) and actual in expected
    if op == "contains":
        return isinstance(actual, (list, tuple, set, str)) and expected in actual

    # Ordered comparisons: compare numerically when both sides parse as numbers.
    left, right = _to_decimal(actual), _to_decimal(expected)
    if left is None or right is None:
        return False
    if op == "gt":
        return left > right
    if op == "gte":
        return left >= right
    if op == "lt":
        return left < right
    if op == "lte":
        return left <= right
    return False


def _matches(rule: dict[str, Any], transaction: dict[str, Any]) -> bool:
    conditions = rule["when"]
    results = []
    for cond in conditions:
        field = cond["field"]
        actual = _get_field(transaction, field)
        if cond["op"] == "exists":
            results.append(actual is not None)
            continue
        actual_c, expected_c = _coerce_pair(field, actual, cond.get("value"))
        results.append(_compare(cond["op"], actual_c, expected_c))
    return all(results) if rule.get("match", "all") == "all" else any(results)


def evaluate(
    transaction: dict[str, Any], rules: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Return the list of matched ``action`` payloads, each annotated with its ``rule_id``."""
    active = rules if rules is not None else load_rules()
    matched: list[dict[str, Any]] = []
    for rule in active:
        if _matches(rule, transaction):
            matched.append({"rule_id": rule["id"], **rule["action"]})
    return matched
