import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.store import InMemoryTransactionStore, get_store


@pytest.fixture
def fresh_store() -> InMemoryTransactionStore:
    return InMemoryTransactionStore()


@pytest.fixture
def client(fresh_store: InMemoryTransactionStore) -> TestClient:
    app.dependency_overrides[get_store] = lambda: fresh_store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
