import os
import json
import uuid
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal, engine, Base
from backend.db.models import Batch, Match, AIVerification
from backend.parser import InvoiceParser, SettlementParser, BankStatementParser
from backend.normalizer import normalize_dataframe, NormalizedRecord
from backend.ai.engine import (
    FinanceVerificationOrchestrator,
    verify_discrepancy,
    assemble_context_payload,
)

SYNTHETIC_DATA_DIR = "backend/synthetic_data"


@pytest.fixture(scope="module")
def real_synthetic_dataset():
    """Loads normalized records and ground truth from the real synthetic fixtures."""
    inv_df = InvoiceParser().parse(os.path.join(SYNTHETIC_DATA_DIR, "invoices.csv"))
    set_df = SettlementParser().parse(os.path.join(SYNTHETIC_DATA_DIR, "settlements.csv"))
    bnk_df = BankStatementParser().parse(os.path.join(SYNTHETIC_DATA_DIR, "bank_statements.csv"))

    invoices = normalize_dataframe(inv_df, "invoice")
    settlements = normalize_dataframe(set_df, "settlement")
    banks = normalize_dataframe(bnk_df, "bank")

    with open(os.path.join(SYNTHETIC_DATA_DIR, "ground_truth.json"), "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    inv_by_id = {rec.transaction_id: rec for rec in invoices}
    set_by_id = {rec.transaction_id: rec for rec in settlements}
    bnk_by_id = {rec.transaction_id: rec for rec in banks}

    return {
        "invoices": inv_by_id,
        "settlements": set_by_id,
        "banks": bnk_by_id,
        "ground_truth": ground_truth,
    }


@pytest.fixture
def db_session():
    """Provides a transactional DB session for logging tests."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ---------------------------------------------------------------------------
# 1. Integration Tests against Real Synthetic Edge Cases (Not Mocks)
# ---------------------------------------------------------------------------

def test_ai_engine_hero_case_real_edge_case(real_synthetic_dataset):
    """
    Case 1: PRD/SRS Hero case (Scenario 87: ₹12,000 invoice with ₹30 manual fee override -> ₹11,970).
    Verifies that the orchestrator assembles context, proposes fee explanation,
    and Deterministic Validator confirms exact reconciliation with calculation trace.
    """
    gt_hero = [gt for gt in real_synthetic_dataset["ground_truth"] if gt["scenario_id"] == "SCENARIO-0087"][0]
    inv = real_synthetic_dataset["invoices"][gt_hero["invoice_id"]]
    settle = real_synthetic_dataset["settlements"][gt_hero["settlement_id"]]
    bank = real_synthetic_dataset["banks"][gt_hero["bank_txn_id"]]

    assert inv.amount == Decimal("12000.00")
    assert settle.amount == Decimal("11970.00")
    assert settle.fees == Decimal("30.00")

    result = verify_discrepancy(invoice=inv, settlement=settle, bank=bank)

    assert result.is_validated is True
    assert result.difference_amount == Decimal("30.00")
    assert result.likely_reason == "processing_fee"
    assert result.expected_value == Decimal("11970.00")
    assert result.adjusted_confidence == Decimal("99.00")
    assert result.evidence_field == "settlement.fees"
    assert "₹12,000.00 − ₹30.00 (processing fee) = ₹11,970.00 = settlement amount ✓" in result.calculation_trace
    assert result.requires_human_review is False
    assert result.validation_outcome == "exact"


def test_ai_engine_second_real_edge_case(real_synthetic_dataset):
    """
    Case 2: Scenario 88 (₹25,000 invoice with ₹45 flat fee override -> ₹24,955).
    """
    gt_case2 = [gt for gt in real_synthetic_dataset["ground_truth"] if gt["scenario_id"] == "SCENARIO-0088"][0]
    inv = real_synthetic_dataset["invoices"][gt_case2["invoice_id"]]
    settle = real_synthetic_dataset["settlements"][gt_case2["settlement_id"]]
    bank = real_synthetic_dataset["banks"][gt_case2["bank_txn_id"]]

    assert inv.amount == Decimal("25000.00")
    assert settle.amount == Decimal("24955.00")
    assert settle.fees == Decimal("45.00")

    result = verify_discrepancy(invoice=inv, settlement=settle, bank=bank)

    assert result.is_validated is True
    assert result.difference_amount == Decimal("45.00")
    assert result.likely_reason == "processing_fee"
    assert result.expected_value == Decimal("24955.00")
    assert result.adjusted_confidence == Decimal("99.00")
    assert "₹25,000.00 − ₹45.00 (processing fee) = ₹24,955.00 = settlement amount ✓" in result.calculation_trace


def test_ai_engine_third_real_edge_case(real_synthetic_dataset):
    """
    Case 3: Scenario 89 (₹18,500 invoice with ₹50 manual fee discount -> ₹18,450).
    """
    gt_case3 = [gt for gt in real_synthetic_dataset["ground_truth"] if gt["scenario_id"] == "SCENARIO-0089"][0]
    inv = real_synthetic_dataset["invoices"][gt_case3["invoice_id"]]
    settle = real_synthetic_dataset["settlements"][gt_case3["settlement_id"]]
    bank = real_synthetic_dataset["banks"][gt_case3["bank_txn_id"]]

    assert inv.amount == Decimal("18500.00")
    assert settle.amount == Decimal("18450.00")
    assert settle.fees == Decimal("50.00")

    result = verify_discrepancy(invoice=inv, settlement=settle, bank=bank)

    assert result.is_validated is True
    assert result.difference_amount == Decimal("50.00")
    assert result.adjusted_confidence == Decimal("99.00")
    assert "₹18,500.00 − ₹50.00 (processing fee) = ₹18,450.00 = settlement amount ✓" in result.calculation_trace


# ---------------------------------------------------------------------------
# 2. Context Payload Assembly Tests (Section 3 Step 2)
# ---------------------------------------------------------------------------

def test_assemble_context_payload_has_precomputed_delta(real_synthetic_dataset):
    """
    Verifies that assemble_context_payload pre-computes numeric delta
    and attaches structured fee schedule as data.
    """
    gt = real_synthetic_dataset["ground_truth"][86]
    inv = real_synthetic_dataset["invoices"][gt["invoice_id"]]
    settle = real_synthetic_dataset["settlements"][gt["settlement_id"]]

    sys_prompt, user_prompt, delta = assemble_context_payload(invoice=inv, settlement=settle)

    assert "You are a financial reconciliation verification assistant" in sys_prompt
    assert "precomputed_delta_vs_settlement" in user_prompt
    assert "standard_mdr_fee_rate" in user_prompt
    assert delta == Decimal("30.00")


# ---------------------------------------------------------------------------
# 3. Failure Handling & Retry Tests (Section 8)
# ---------------------------------------------------------------------------

def test_failure_handling_malformed_json_fallback():
    """
    Asserts that malformed JSON or corrupted model output gracefully falls back
    to needs_review without raising uncaught exceptions or crashing the batch.
    """
    class FaultyOrchestrator(FinanceVerificationOrchestrator):
        def _execute_llm_call_with_retry(self, *args, **kwargs):
            # Simulate unparseable garbage output
            return {"corrupted_field": "unparseable"}, 100, 20, "mock-model"

    orch = FaultyOrchestrator()
    inv = NormalizedRecord(source_type="invoice", transaction_id="INV-ERR", amount=Decimal("5000.00"), txn_date=date(2026, 8, 1), status="paid")
    settle = NormalizedRecord(source_type="settlement", transaction_id="SET-ERR", amount=Decimal("4900.00"), txn_date=date(2026, 8, 1), status="settled")

    result = orch.verify_discrepancy(invoice=inv, settlement=settle)

    assert result.is_validated is False
    assert result.requires_human_review is True
    assert result.adjusted_confidence <= Decimal("50.00")
    assert "Failed schema validation" in result.notes or "routed to human review" in result.notes


def test_failure_handling_provider_timeout_fallback():
    """
    Asserts that provider timeout / connection error degrades to needs_review gracefully.
    """
    class TimeoutOrchestrator(FinanceVerificationOrchestrator):
        def _execute_llm_call_with_retry(self, *args, **kwargs):
            # Fallback simulated response
            return {
                "difference_amount": 100.0,
                "likely_reason": "insufficient_evidence",
                "reasoning_explanation": "LLM provider timed out; falling back to needs_review.",
                "expected_value": 0.0,
                "confidence_score": 20.0,
                "evidence_field": "settlement.amount",
            }, 50, 20, "gpt-5.6-terra"

    orch = TimeoutOrchestrator()
    inv = NormalizedRecord(source_type="invoice", transaction_id="INV-TO", amount=Decimal("5000.00"), txn_date=date(2026, 8, 1), status="paid")
    settle = NormalizedRecord(source_type="settlement", transaction_id="SET-TO", amount=Decimal("4900.00"), txn_date=date(2026, 8, 1), status="settled")

    result = orch.verify_discrepancy(invoice=inv, settlement=settle)

    assert result.is_validated is False
    assert result.requires_human_review is True
    assert result.likely_reason == "insufficient_evidence"


# ---------------------------------------------------------------------------
# 4. Database Logging Tests (04-Database-Design.md ai_verifications)
# ---------------------------------------------------------------------------

def test_database_logging_ai_verification(db_session: Session, real_synthetic_dataset):
    """
    Verifies that calling verify_discrepancy with a db session and match_id
    creates an ai_verifications row matching 04-Database-Design.md.
    """
    batch = Batch(id=str(uuid.uuid4()), status="processing")
    db_session.add(batch)

    match = Match(
        id=str(uuid.uuid4()),
        batch_id=batch.id,
        match_method="ai",
        status="matched",
        confidence=Decimal("99.00"),
    )
    db_session.add(match)
    db_session.commit()

    gt = real_synthetic_dataset["ground_truth"][86]
    inv = real_synthetic_dataset["invoices"][gt["invoice_id"]]
    settle = real_synthetic_dataset["settlements"][gt["settlement_id"]]

    result = verify_discrepancy(invoice=inv, settlement=settle, db=db_session, match_id=match.id)

    ai_log = db_session.query(AIVerification).filter(AIVerification.match_id == match.id).first()
    assert ai_log is not None
    assert ai_log.difference_amount == Decimal("30.00")
    assert ai_log.likely_reason == "processing_fee"
    assert ai_log.adjusted_confidence == Decimal("99.00")
    assert ai_log.evidence_field == "settlement.fees"
    assert ai_log.model_used is not None
