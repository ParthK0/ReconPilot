"""
tests/test_micro_batching.py
============================
Tests for Cluster Micro-Batching in AI Discrepancy Verification.
"""

from datetime import date
from decimal import Decimal
from backend.normalizer.normalizer import NormalizedRecord
from backend.ai.engine import FinanceVerificationOrchestrator


def test_cluster_micro_batching_execution():
    orchestrator = FinanceVerificationOrchestrator(ai_mode="offline")

    inv1 = NormalizedRecord(
        id="inv_mb_1",
        batch_id="b1",
        source_type="invoice",
        transaction_id="TXN_1",
        order_id="ORD_MB_1",
        amount=Decimal("1000.00"),
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    set1 = NormalizedRecord(
        id="set_mb_1",
        batch_id="b1",
        source_type="settlement",
        transaction_id="SET_1",
        order_id="ORD_MB_1",
        amount=Decimal("980.00"),
        fees=Decimal("20.00"),
        txn_date=date(2026, 8, 3),
        status="settled",
    )

    inv2 = NormalizedRecord(
        id="inv_mb_2",
        batch_id="b1",
        source_type="invoice",
        transaction_id="TXN_2",
        order_id="ORD_MB_2",
        amount=Decimal("2000.00"),
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    set2 = NormalizedRecord(
        id="set_mb_2",
        batch_id="b1",
        source_type="settlement",
        transaction_id="SET_2",
        order_id="ORD_MB_2",
        amount=Decimal("1960.00"),
        fees=Decimal("40.00"),
        txn_date=date(2026, 8, 3),
        status="settled",
    )

    items = [
        {"invoice": inv1, "settlement": set1, "bank": None, "match_id": None},
        {"invoice": inv2, "settlement": set2, "bank": None, "match_id": None},
    ]

    results = orchestrator.verify_discrepancies_clustered(items=items, merchant_type="retail")
    assert len(results) == 2
    assert results[0].is_validated is True
    assert results[0].likely_reason == "processing_fee"
    assert results[1].is_validated is True
    assert results[1].likely_reason == "processing_fee"
    assert "clustered" in results[1].model_used.lower()

