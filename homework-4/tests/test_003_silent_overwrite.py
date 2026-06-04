"""
Tests for BUG-003: Silent Overwrite of Existing Holocron

This test module verifies that the store endpoint rejects duplicate holocron names
with a 409 Conflict status code, preventing silent overwrites of existing holocrons.
"""

import pytest


class TestSilentOverwrite:
    """Tests for the silent overwrite fix."""

    def test_store_first_holocron_returns_201(self, client):
        """Happy path: POST /holocron with a unique name → 201 Created."""
        response = client.post(
            "/holocron",
            json={"name": "wisdom-holocron", "body": "Ancient Force wisdom"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "wisdom-holocron"
        assert data["status"] == "stored"

    def test_store_duplicate_holocron_returns_409(self, client):
        """Error path: Second POST /holocron with same name → 409 Conflict."""
        # First, store a holocron
        first_response = client.post(
            "/holocron",
            json={"name": "wisdom-holocron", "body": "Original wisdom"},
        )
        assert first_response.status_code == 201

        # Attempt to store with the same name
        second_response = client.post(
            "/holocron",
            json={"name": "wisdom-holocron", "body": "Overwrite attempt"},
        )
        assert second_response.status_code == 409
        data = second_response.json()
        assert "already exists" in data["detail"].lower()
        assert "Force does not allow overwriting" in data["detail"]
