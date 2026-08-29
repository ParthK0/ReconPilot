"""
tests/test_gap_detection.py
===========================
Tests for 3-way gap detection (missing settlements and unmatched bank credits).
"""

import uuid
from decimal import Decimal
from datetime import date
import pytest
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal, init_db
from backend.db.models import Batch, Record, ExceptionRecord, Match
from backend.services.pipeline import process_reconciliation_batch


@pytest.fixture
def db_session():
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_gap_detection_uncollected_invoices_and_unmatched_bank_credits(db_session: Session):
    """
    Asserts that:
    1. A paid invoice with NO matching settlement is flagged as 'missing_settlement'.
    2. A bank credit with NO matching settlement is flagged as 'unmatched_bank_credit'.
    """
    batch_id = str(uuid.uuid4())
    batch = Batch(
        id=batch_id,
        settlement_filename="test_settlements.csv",
        bank_filename="test_bank.csv",
        invoice_filename="test_invoices.csv",
        status="processing",
    )
    db_session.add(batch)
    db_session.commit()

    # 1. Invoice with order_id that has NO settlement
    unmatched_inv = Record(
        id=str(uuid.uuid4()),
        batch_id=batch_id,
        source_type="invoice",
        transaction_id="INV-GAP-1",
        order_id="ORD-UNCOLLECTED-999",
        amount=Decimal("15000.00"),
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    # 2. Bank credit with UTR that has NO settlement
    unmatched_bank = Record(
        id=str(uuid.uuid4()),
        batch_id=batch_id,
        source_type="bank",
        transaction_id="BNK-GAP-1",
        amount=Decimal("8500.00"),
        txn_date=date(2026, 8, 2),
        reference_number="UTR-MYSTERY-8888",
        status="credited",
    )
    # 3. Paired settlement + invoice + bank (normal match)
    normal_inv = Record(
        id=str(uuid.uuid4()),
        batch_id=batch_id,
        source_type="invoice",
        transaction_id="INV-NORM-1",
        order_id="ORD-NORMAL-100",
        amount=Decimal("5000.00"),
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    normal_settle = Record(
        id=str(uuid.uuid4()),
        batch_id=batch_id,
        source_type="settlement",
        transaction_id="SET-NORM-1",
        order_id="ORD-NORMAL-100",
        amount=Decimal("5000.00"),
        txn_date=date(2026, 8, 2),
        reference_number="UTR-NORM-100",
        status="settled",
    )
    normal_bank = Record(
        id=str(uuid.uuid4()),
        batch_id=batch_id,
        source_type="bank",
        transaction_id="BNK-NORM-1",
        amount=Decimal("5000.00"),
        txn_date=date(2026, 8, 2),
        reference_number="UTR-NORM-100",
        status="credited",
    )

    db_session.add_all([unmatched_inv, unmatched_bank, normal_inv, normal_settle, normal_bank])
    db_session.commit()

    snapshot = process_reconciliation_batch(db_session, batch_id, fee_config="retail")

    assert snapshot.records_processed == 1  # 1 settlement processed
    assert snapshot.rule_matches == 1       # normal match matched by Rule 1

    # Check exceptions created
    exceptions = db_session.query(ExceptionRecord).join(Record).filter(Record.batch_id == batch_id).all()
    categories = [e.category for e in exceptions]

    assert "missing_settlement" in categories
    assert "unmatched_bank_credit" in categories

    missing_set_exc = next(e for e in exceptions if e.category == "missing_settlement")
    assert "ORD-UNCOLLECTED-999" in missing_set_exc.notes
