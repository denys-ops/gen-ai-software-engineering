from decimal import Decimal
from app.services.store import InMemoryTransactionStore
from app.domain.models import Transaction
from app.domain.enums import TransactionType, TransactionStatus


def make_txn(**kwargs) -> Transaction:
    defaults = dict(
        id="test-id-1",
        to_account="ACC-12345",
        from_account=None,
        amount=Decimal("50.00"),
        currency="USD",
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.COMPLETED,
        timestamp="2024-01-15T10:00:00Z",
    )
    defaults.update(kwargs)
    return Transaction(**defaults)


def test_empty_store_list_returns_empty():
    store = InMemoryTransactionStore()
    assert store.list_all() == []


def test_empty_store_get_returns_none():
    store = InMemoryTransactionStore()
    assert store.get("nonexistent") is None


def test_insert_then_list_contains_txn():
    store = InMemoryTransactionStore()
    txn = make_txn()
    store.insert(txn)
    assert store.list_all() == [txn]


def test_insert_then_get_returns_txn():
    store = InMemoryTransactionStore()
    txn = make_txn()
    store.insert(txn)
    assert store.get(txn.id) == txn


def test_get_unknown_id_returns_none_after_insert():
    store = InMemoryTransactionStore()
    txn = make_txn()
    store.insert(txn)
    assert store.get("other-id") is None


def test_list_preserves_insertion_order():
    store = InMemoryTransactionStore()
    txn1 = make_txn(id="id-1")
    txn2 = make_txn(id="id-2")
    txn3 = make_txn(id="id-3")
    for t in [txn1, txn2, txn3]:
        store.insert(t)
    assert [t.id for t in store.list_all()] == ["id-1", "id-2", "id-3"]


def test_multiple_stores_are_independent():
    s1 = InMemoryTransactionStore()
    s2 = InMemoryTransactionStore()
    s1.insert(make_txn(id="only-in-s1"))
    assert s2.list_all() == []
