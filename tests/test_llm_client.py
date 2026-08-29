"""
tests/test_llm_client.py
========================
Unit and integration tests for Phase 1: Robust LLM Client & AI Orchestration.
"""

import os
from decimal import Decimal
import pytest
from datetime import date

from backend.ai.llm_client import (
    LLMClient,
    CostCeilingExceededError,
    LLMConfigurationError,
    MODEL_PRICING,
)
from backend.ai.engine import (
    FinanceVerificationOrchestrator,
    generate_dynamic_supporting_rules,
)
from backend.normalizer.normalizer import NormalizedRecord
from backend.ai.feedback_memory import FeedbackMemoryStore
from backend.db.session import SessionLocal, init_db


def test_cost_calculation_accurate():
    client = LLMClient(ai_mode="offline")
    # 1000 prompt tokens + 200 completion tokens on gemini-2.5-pro
    cost = client.calculate_cost("gemini-2.5-pro", prompt_tokens=1000, completion_tokens=200)
    expected_input = (Decimal("1000") / Decimal("1000000")) * Decimal("1.25")
    expected_output = (Decimal("200") / Decimal("1000000")) * Decimal("5.00")
    assert cost == (expected_input + expected_output).quantize(Decimal("0.000001"))
    assert cost > Decimal("0.00")


def test_cost_ceiling_enforcement_raises():
    # Ceiling of $0.000010
    client = LLMClient(ai_mode="offline", spend_ceiling_usd=Decimal("0.000010"))
    client.cumulative_spend_usd = Decimal("0.000015")
    
    with pytest.raises(CostCeilingExceededError):
        client.check_cost_ceiling()


def test_offline_mode_returns_simulated_completion():
    client = LLMClient(ai_mode="offline")
    response = client.generate_json_completion(
        system_prompt="You are a finance assistant.",
        user_prompt="Explain difference of 30.00",
        fallback_simulation_fn=lambda: {
            "difference_amount": 30.0,
            "likely_reason": "processing_fee",
            "confidence_score": 98.0,
        },
    )
    assert response.is_simulated is True
    assert response.model_name == "offline-simulation"
    assert response.parsed_json["likely_reason"] == "processing_fee"
    assert response.prompt_tokens > 0


def test_dynamic_supporting_rules_generation():
    inv = NormalizedRecord(
        source_type="invoice",
        transaction_id="inv-1",
        order_id="ORD-101",
        amount=Decimal("12000.00"),
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    settle = NormalizedRecord(
        source_type="settlement",
        transaction_id="set-1",
        order_id="ORD-101",
        amount=Decimal("11970.00"),
        txn_date=date(2026, 8, 2),
        status="settled",
        fees=Decimal("30.00"),
        reference_number="UTR-9999",
    )
    bank = NormalizedRecord(
        source_type="bank",
        transaction_id="bnk-1",
        amount=Decimal("11970.00"),
        txn_date=date(2026, 8, 2),
        status="credited",
        reference_number="UTR-9999",
    )

    rules = generate_dynamic_supporting_rules(
        invoice=inv,
        settlement=settle,
        bank=bank,
        numeric_delta=Decimal("30.00"),
    )

    assert len(rules) == 5
    # Rule 1 should report exact delta Rs 30.00
    assert any("Delta Rs 30.00" in r for r in rules)
    # Rule 2 should verify UTR
    assert any("UTR 'UTR-9999' confirmed" in r for r in rules)
    # Rule 4 should verify date window
    assert any("T+1 days" in r for r in rules)
    # Rule 5 should identify one-off override
    assert any("Rs 30.00 differ from standard" in r for r in rules)


def test_feedback_memory_multidimensional_ranking():
    init_db()
    db = SessionLocal()
    try:
        store = FeedbackMemoryStore()
        
        # Insert test cases
        store.record_feedback(
            db=db,
            merchant_type="retail",
            corrected_reason="processing_fee",
            amount_delta=Decimal("30.00"),
            reviewer_notes="Standard fee override approved",
        )
        store.record_feedback(
            db=db,
            merchant_type="saas",
            corrected_reason="tds_deduction",
            amount_delta=Decimal("500.00"),
            reviewer_notes="SaaS subscription TDS adjustment",
        )

        # Query for retail with delta 30.00
        similar = store.find_similar_cases(
            db=db,
            merchant_type="retail",
            amount_delta=Decimal("30.00"),
            candidate_reason="processing_fee",
        )

        assert len(similar) >= 1
        top_match = similar[0]
        assert top_match.merchant_type == "retail"
        assert top_match.corrected_reason == "processing_fee"
        assert top_match.similarity_score >= 0.90
    finally:
        db.close()
