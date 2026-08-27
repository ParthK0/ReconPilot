"""
tests/test_cash_position.py
===========================
Tests for Cash Position & Working Capital Analytics.
"""

from decimal import Decimal
from datetime import date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import Base, Batch, Record, Match, ExceptionRecord
from backend.analytics.cash_position import compute_cash_position


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_cash_position_computation(test_db):
    batch = Batch(id="batch-test-cash-01", status="done")
    test_db.add(batch)

    # 1. Invoice
    inv = Record(
        id="rec-inv-1",
        batch_id=batch.id,
        source_type="invoice",
        transaction_id="inv-1",
        order_id="ORD-1",
        amount=Decimal("10000.00"),
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    # 2. Credited Bank settlement
    bnk = Record(
        id="rec-bnk-1",
        batch_id=batch.id,
        source_type="bank",
        transaction_id="bnk-1",
        amount=Decimal("9800.00"),
        txn_date=date(2026, 8, 2),
        reference_number="UTR001",
        status="credited",
    )
    # 3. Pending settlement (delayed)
    settle_pending = Record(
        id="rec-set-pending",
        batch_id=batch.id,
        source_type="settlement",
        transaction_id="set-pending",
        order_id="ORD-2",
        amount=Decimal("5000.00"),
        txn_date=date(2026, 8, 2),
        reference_number="UTR002",
        status="pending",
    )
    # 4. Refund debit
    bnk_refund = Record(
        id="rec-bnk-refund",
        batch_id=batch.id,
        source_type="bank",
        transaction_id="bnk-refund",
        amount=Decimal("-500.00"),
        txn_date=date(2026, 8, 3),
        reference_number="UTR_REF",
        status="debited",
    )

    test_db.add_all([inv, bnk, settle_pending, bnk_refund])
    test_db.commit()

    snapshot = compute_cash_position(test_db, batch.id, fee_config="retail", opening_bank_balance=Decimal("100000.00"))

    assert snapshot.batch_id == batch.id
    assert snapshot.gross_volume_processed == Decimal("10000.00")
    assert snapshot.settled_volume_credited == Decimal("9800.00")
    assert snapshot.pending_settlement_inflows == Decimal("5000.00")
    assert snapshot.pending_refund_reserves == Decimal("500.00")
    assert snapshot.expected_cash_tomorrow > Decimal("0.00")
    assert snapshot.liquidity_health_index > 0.0
