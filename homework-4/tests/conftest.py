# tests/conftest.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from fastapi.testclient import TestClient
from app import storage
from app.main import app

_ORIGINAL_BASE_DIR = storage.BASE_DIR

@pytest.fixture
def client(tmp_path):
    storage.BASE_DIR = tmp_path / "vault"
    storage.BASE_DIR.mkdir()
    yield TestClient(app)
    storage.BASE_DIR = _ORIGINAL_BASE_DIR  # restore after each test
