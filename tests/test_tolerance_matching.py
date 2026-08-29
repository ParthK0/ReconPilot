"""
tests/test_tolerance_matching.py
================================
Tests for Rule 6 (Tolerance Amount Match).
"""

from decimal import Decimal
from datetime import date
from backend.normalizer.normalizer import NormalizedRecord
from backend.rules.rule_engine import match_tolerance_amount, apply_rules_in_order


def test_tolerance_match_within_2_rupees():
    """Variance of Rs 1.50 with matching order ID must match Rule 6 at 95% confidence."""
    inv = NormalizedRecord(
        id="inv-1",
        batch_id="b-1",
        source_type="invoice",
        transaction_id="TXN-1",
        order_id="ORD-TOL-101",
        amount=Decimal("5000.00"),
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    settle = NormalizedRecord(
        id="set-1",
        batch_id="b-1",
        source_type="settlement",
        transaction_id="SET-1",
        order_id="ORD-TOL-101",
        amount=Decimal("4998.50"),  # Rs 1.50 delta
        txn_date=date(2026, 8, 2),
        status="settled",
    )

    res = match_tolerance_amount(invoice=inv, settlement=settle)
    assert res.is_matched is True
    assert res.rule_name == "tolerance_amount_match"
    assert res.confidence == Decimal("95.00")

    # Verify pipeline order
    pipe_res = apply_rules_in_order(invoice=inv, settlement=settle)
    assert pipe_res.is_matched is True
    assert pipe_res.rule_name == "tolerance_amount_match"


def test_tolerance_match_rejects_exceeding_tolerance():
    """Variance of Rs 5.00 exceeds Rs 2.00 tolerance and must fall through."""
    inv = NormalizedRecord(
        id="inv-2",
        batch_id="b-1",
        source_type="invoice",
        transaction_id="TXN-2",
        order_id="ORD-TOL-102",
        amount=Decimal("5000.00"),
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    settle = NormalizedRecord(
        id="set-2",
        batch_id="b-1",
        source_type="settlement",
        transaction_id="SET-2",
        order_id="ORD-TOL-102",
        amount=Decimal("4995.00"),  # Rs 5.00 delta
        txn_date=date(2026, 8, 2),
        status="settled",
    )

    res = match_tolerance_amount(invoice=inv, settlement=settle)
    assert res.is_matched is False
