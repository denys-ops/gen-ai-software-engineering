"""Tests for config env-override parsing (added after the audit)."""

from __future__ import annotations

import pytest

import config


def test_good_int_override(monkeypatch):
    monkeypatch.setenv("X_OK_INT", "42")
    assert config._get_int("X_OK_INT", 1) == 42


def test_bad_int_env_raises_clear_error(monkeypatch):
    monkeypatch.setenv("X_BAD_INT", "abc")
    with pytest.raises(RuntimeError, match="invalid integer value"):
        config._get_int("X_BAD_INT", 1)


def test_good_decimal_override(monkeypatch):
    monkeypatch.setenv("X_OK_DEC", "12.5")
    assert str(config._get_decimal("X_OK_DEC", "1")) == "12.5"


def test_bad_decimal_env_raises_clear_error(monkeypatch):
    monkeypatch.setenv("X_BAD_DEC", "xyz")
    with pytest.raises(RuntimeError, match="invalid decimal value"):
        config._get_decimal("X_BAD_DEC", "1")


def test_defaults_present():
    assert config.HIGH_VALUE_THRESHOLD == config.Decimal("10000")
    assert config.HOME_COUNTRY == "US"
    assert "USD" in config.ISO_4217_CURRENCIES
    assert "IR" in config.SANCTIONED_COUNTRIES
