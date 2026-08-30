"""
tests/test_fx_rules.py
======================
Tests for International FX Spread Tolerance and Multi-Currency Tranches.
"""

from datetime import date
from decimal import Decimal
from backend.normalizer.normalizer import NormalizedRecord
from backend.rules.rule_engine import match_fx_spread_tolerance, apply_rules_in_order
from backend.synthetic_data.merchant_archetypes import get_archetype


def test_fx_spread_tolerance_matching():
    # US Dollar invoice converted to INR with 2.5% FX conversion spread
    inv = NormalizedRecord(
        id="inv_fx_01",
        batch_id="batch_intl",
        source_type="invoice",
        transaction_id="TXN_USD_100",
        order_id="ORD_INTL_001",
        amount=Decimal("10000.00"),
        currency="INR",
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    # Settlement received with 2.5% FX spread deducted
    settle = NormalizedRecord(
        id="set_fx_01",
        batch_id="batch_intl",
        source_type="settlement",
        transaction_id="SET_INR_100",
        order_id="ORD_INTL_001",
        amount=Decimal("9750.00"),
        currency="INR",
        txn_date=date(2026, 8, 3),
        status="settled",
    )

    res = match_fx_spread_tolerance(invoice=inv, settlement=settle)
    assert res.is_matched is True
    assert res.rule_name == "fx_spread_tolerance"
    assert res.confidence == Decimal("94.00")
    assert "international FX spread corridor" in res.notes


def test_cross_border_archetype_registration():
    arch = get_archetype("cross_border_saas")
    assert arch.merchant_type == "cross_border_saas"
    assert "CloudMatrix Global" in arch.display_name
    assert "fx_markup_fee" in arch.settlement_columns.values()
