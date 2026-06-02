"""
Tests for 001-security-path-traversal fix.
Validates that path traversal attempts are rejected with 400.
"""
import pytest


class TestPathTraversalSecurity:
    """Path traversal guard in write_holocron() and error handling in store() endpoint."""

    def test_store_clean_name_returns_201(self, client):
        """Happy path: POST /holocron with a clean name returns 201."""
        response = client.post(
            "/holocron",
            json={"name": "skywalker", "body": "Luke is the chosen one"}
        )
        assert response.status_code == 201
        assert response.json()["status"] == "stored"
        assert response.json()["name"] == "skywalker"

    def test_store_traversal_parent_dir_returns_400(self, client):
        """Error path: POST /holocron with name '../evil.txt' returns 400."""
        response = client.post(
            "/holocron",
            json={"name": "../evil.txt", "body": "Attempted escape"}
        )
        assert response.status_code == 400
        assert "Path escapes vault" in response.json()["detail"]

    def test_store_traversal_multiple_dirs_returns_400(self, client):
        """Error path: POST /holocron with name '../../etc/passwd' returns 400."""
        response = client.post(
            "/holocron",
            json={"name": "../../etc/passwd", "body": "Attempt to escape"}
        )
        assert response.status_code == 400
        assert "Path escapes vault" in response.json()["detail"]

    def test_store_valid_nested_path_returns_201(self, client):
        """Happy path: POST /holocron with valid nested name 'jedi/luke.txt' returns 201."""
        response = client.post(
            "/holocron",
            json={"name": "jedi/luke.txt", "body": "Nested holocron"}
        )
        assert response.status_code == 201
        assert response.json()["status"] == "stored"
        assert response.json()["name"] == "jedi/luke.txt"

    def test_store_absolute_path_returns_400(self, client):
        """Error path: POST /holocron with absolute path returns 400."""
        response = client.post(
            "/holocron",
            json={"name": "/etc/passwd", "body": "Absolute path attempt"}
        )
        assert response.status_code == 400
        assert "Path escapes vault" in response.json()["detail"]
