"""
tests/test_feedback_memory.py
==============================
Tests for Feedback Memory Store & Learning via Retrieval.
"""

from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import Base, FeedbackMemoryRecord
from backend.ai.feedback_memory import FeedbackMemoryStore


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_record_and_retrieve_feedback(test_db):
    store = FeedbackMemoryStore()
    
    # Record human feedback for a custom flat fee waiver
    rec = store.record_feedback(
        db=test_db,
        merchant_type="restaurant",
        order_id="ORD-REST-1001",
        corrected_reason="manual_fee_adjustment",
        amount_delta=Decimal("45.00"),
        reviewer_notes="Approved special corporate F&B waiver.",
        reviewer_action="approved",
    )
    assert rec.id is not None
    assert rec.merchant_type == "restaurant"
    assert rec.amount_delta == Decimal("45.00")

    # Query similar cases with matching delta
    cases = store.find_similar_cases(
        db=test_db,
        merchant_type="restaurant",
        amount_delta=Decimal("45.00"),
    )
    assert len(cases) == 1
    assert cases[0].similarity_score >= 0.95
    assert cases[0].corrected_reason == "manual_fee_adjustment"
    assert "Approved special corporate" in cases[0].reviewer_notes


def test_similarity_ranking(test_db):
    store = FeedbackMemoryStore()
    
    store.record_feedback(
        db=test_db,
        merchant_type="saas",
        corrected_reason="chargeback",
        amount_delta=Decimal("1500.00"),
        reviewer_notes="Customer initiated bank dispute.",
    )
    store.record_feedback(
        db=test_db,
        merchant_type="saas",
        corrected_reason="gateway_retry",
        amount_delta=Decimal("15.00"),
        reviewer_notes="Retry fee deduction.",
    )

    # Search with delta ₹15.00
    top_matches = store.find_similar_cases(
        db=test_db,
        merchant_type="saas",
        amount_delta=Decimal("15.00"),
        limit=1,
    )
    assert len(top_matches) == 1
    assert top_matches[0].corrected_reason == "gateway_retry"
