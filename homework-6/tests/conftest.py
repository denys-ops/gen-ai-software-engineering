"""Shared pytest fixtures for the pipeline tests."""

from __future__ import annotations

from typing import Any

import pytest

from agents._shared import build_envelope


def _txn(**overrides: Any) -> dict[str, Any]:
    base = {
        "transaction_id": "TXN001",
        "timestamp": "2026-03-16T09:00:00Z",
        "source_account": "ACC-1001",
        "destination_account": "ACC-2001",
        "amount": "1500.00",
        "currency": "USD",
        "transaction_type": "transfer",
        "description": "test",
        "metadata": {"channel": "online", "country": "US"},
    }
    base.update(overrides)
    return base


@pytest.fixture
def make_txn():
    """Factory for a valid transaction dict with optional field overrides."""
    return _txn


@pytest.fixture
def make_message():
    """Factory wrapping a transaction in a message envelope."""

    def _factory(target: str = "transaction_validator", **overrides: Any) -> dict[str, Any]:
        return build_envelope(source_agent="integrator", target_agent=target, data=_txn(**overrides))

    return _factory
