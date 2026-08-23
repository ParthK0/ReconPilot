from datetime import date
from decimal import Decimal

from backend.ai.validator import validate_finance_verification
from backend.normalizer import NormalizedRecord


def _record(source_type: str, amount: str, **charges: str) -> NormalizedRecord:
    return NormalizedRecord(
        source_type=source_type, transaction_id=f"{source_type}-1", amount=Decimal(amount),
        txn_date=date(2026, 8, 1), status="settled" if source_type == "settlement" else "paid",
        fees=Decimal(charges.get("fees", "0.00")), gst=Decimal(charges.get("gst", "0.00")),
        tds=Decimal(charges.get("tds", "0.00")),
    )


def _claim(**overrides):
    claim = {
        "difference_amount": "30.00", "likely_reason": "processing_fee",
        "reasoning_explanation": "The recorded processing fee explains the gap.",
        "expected_value": "11970.00", "confidence_score": "100.00",
        "evidence_field": "settlement.fees",
    }
    claim.update(overrides)
    return claim


def test_validates_exact_model_claim_and_generates_trace():
    result = validate_finance_verification(_claim(), _record("invoice", "12000.00"), _record("settlement", "11970.00", fees="30.00"))

    assert result.is_valid is True
    assert result.requires_human_review is False
    assert result.outcome == "exact"
    assert Decimal("95") <= result.adjusted_confidence <= Decimal("100")
    assert result.calculation_trace == "₹12,000.00 − ₹30.00 (processing fee) = ₹11,970.00 = settlement amount ✓"


def test_validates_small_rounding_difference_in_documented_band():
    result = validate_finance_verification(_claim(difference_amount="30.80"), _record("invoice", "12000.00"), _record("settlement", "11969.20", fees="30.00"))

    assert result.is_valid is True
    assert result.outcome == "rounding"
    assert Decimal("80") <= result.adjusted_confidence <= Decimal("94")


def test_marks_non_equation_claim_for_human_review():
    result = validate_finance_verification(_claim(likely_reason="duplicate", evidence_field="invoice.order_id", confidence_score="99.00"), _record("invoice", "12000.00"), _record("settlement", "11970.00", fees="30.00"))

    assert result.is_valid is False
    assert result.requires_human_review is True
    assert result.outcome == "unconfirmable"
    assert Decimal("50") <= result.adjusted_confidence <= Decimal("79")


def test_rejects_flatly_wrong_model_arithmetic_under_50_confidence():
    result = validate_finance_verification(_claim(difference_amount="50.00", expected_value="11950.00"), _record("invoice", "12000.00"), _record("settlement", "11970.00", fees="30.00"))

    assert result.is_valid is False
    assert result.requires_human_review is True
    assert result.outcome == "contradicted"
    assert result.adjusted_confidence < Decimal("50")
