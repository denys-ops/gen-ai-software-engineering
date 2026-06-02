"""
Tests for BUG-002: Missing Holocron Returns 500 Instead of 404

This test module verifies that the read endpoint correctly returns HTTP 404
when a holocron does not exist, rather than raising an unhandled 500 error.
"""

import pytest


class TestMissing404:
    """Tests for the missing holocron 404 fix."""

    def test_read_nonexistent_holocron_returns_404(self, client):
        """Error path: GET /holocron/{name} for non-existent holocron → 404."""
        response = client.get("/holocron/does-not-exist")
        assert response.status_code == 404
        assert response.json()["detail"] == "Holocron not found"

    def test_read_existing_holocron_returns_200_with_body(self, client):
        """Happy path: GET /holocron/{name} after storing → 200 with body."""
        # First, store a holocron
        store_response = client.post(
            "/holocron",
            json={"name": "test-holocron", "body": "Test content"},
        )
        assert store_response.status_code == 201

        # Then, retrieve it
        read_response = client.get("/holocron/test-holocron")
        assert read_response.status_code == 200
        data = read_response.json()
        assert data["name"] == "test-holocron"
        assert data["body"] == "Test content"
