"""Independent verification for Finance Verification Engine responses."""

from datetime import date
from decimal import Decimal
from typing import Any, Literal, Mapping, Union

from pydantic import BaseModel, Field

from backend.normalizer.normalizer import NormalizedRecord


ONE_PAISA = Decimal("0.01")
ROUNDING_TOLERANCE = Decimal("2.00")


class FinanceVerificationResponse(BaseModel):
    """The strict JSON response shape specified in 06-AI-Design.md §4."""

    difference_amount: Decimal
    likely_reason: Literal[
        "processing_fee", "gst_deduction", "tds_deduction", "settlement_delay",
        "partial_refund", "duplicate", "insufficient_evidence",
    ]
    reasoning_explanation: str
    expected_value: Decimal
    confidence_score: Decimal = Field(ge=Decimal("0"), le=Decimal("100"))
    evidence_field: str


class ValidationResult(BaseModel):
    """A deterministic verdict; confidence never uses the model's score."""

    is_valid: bool
    requires_human_review: bool
    outcome: Literal["exact", "rounding", "unconfirmable", "contradicted"]
    adjusted_confidence: Decimal
    calculation_trace: str
    notes: str


def validate_finance_verification(
    response: Union[FinanceVerificationResponse, Mapping[str, Any]],
    invoice: NormalizedRecord,
    settlement: NormalizedRecord,
) -> ValidationResult:
    """Re-derive a model claim from record fields without trusting its math."""
    claim = response if isinstance(response, FinanceVerificationResponse) else FinanceVerificationResponse.model_validate(response)
    actual_delta = invoice.amount - settlement.amount
    formulas = {
        "processing_fee": (settlement.fees, "settlement.fees", "processing fee"),
        "gst_deduction": (settlement.fees + settlement.gst, "settlement.gst", "fee and GST deduction"),
        "tds_deduction": (settlement.fees + settlement.gst + settlement.tds, "settlement.tds", "fee, GST, and TDS deduction"),
    }
    formula = formulas.get(claim.likely_reason)
    if formula is None:
        return ValidationResult(
            is_valid=False, requires_human_review=True, outcome="unconfirmable",
            adjusted_confidence=Decimal("65.00"),
            calculation_trace=(f"₹{invoice.amount:,.2f} vs ₹{settlement.amount:,.2f}; "
                               f"{claim.likely_reason.replace('_', ' ')} cannot be independently confirmed by an amount equation."),
            notes="Plausible non-equation explanation; route to human review.",
        )

    deduction, required_evidence, label = formula
    independently_expected = invoice.amount - deduction
    claim_agrees_with_records = (
        deduction > Decimal("0.00")
        and claim.evidence_field == required_evidence
        and abs(claim.difference_amount - actual_delta) <= ONE_PAISA
        and abs(claim.expected_value - independently_expected) <= ONE_PAISA
    )
    if not claim_agrees_with_records:
        return _contradicted(invoice, settlement, claim, actual_delta)

    reconciliation_error = abs(independently_expected - settlement.amount)
    if reconciliation_error <= ONE_PAISA:
        return ValidationResult(
            is_valid=True, requires_human_review=False, outcome="exact",
            adjusted_confidence=Decimal("99.00"),
            calculation_trace=(f"₹{invoice.amount:,.2f} − ₹{deduction:,.2f} ({label}) = "
                               f"₹{settlement.amount:,.2f} = settlement amount ✓"),
            notes="Validator independently confirmed exact reconciliation to the paisa.",
        )
    if reconciliation_error <= ROUNDING_TOLERANCE:
        return ValidationResult(
            is_valid=True, requires_human_review=False, outcome="rounding",
            adjusted_confidence=Decimal("88.00"),
            calculation_trace=(f"₹{invoice.amount:,.2f} − ₹{deduction:,.2f} ({label}) = "
                               f"₹{independently_expected:,.2f} ≈ ₹{settlement.amount:,.2f} "
                               "(within ₹2.00 rounding tolerance) ✓"),
            notes="Validator confirmed reconciliation within the documented rounding tolerance.",
        )
    return _contradicted(invoice, settlement, claim, actual_delta)


def _contradicted(invoice, settlement, claim, actual_delta) -> ValidationResult:
    return ValidationResult(
        is_valid=False, requires_human_review=True, outcome="contradicted",
        adjusted_confidence=Decimal("40.00"),
        calculation_trace=(f"₹{invoice.amount:,.2f} vs ₹{settlement.amount:,.2f} "
                           f"(actual delta ₹{actual_delta:,.2f}) ≠ claimed ₹{claim.difference_amount:,.2f} ✗"),
        notes="Validator contradicted the model claim; route as unknown for review.",
    )


def validate_verification_math(
    invoice_amount: Decimal, settlement_amount: Decimal, difference_amount: Decimal,
    likely_reason: str, claimed_expected_value: Decimal, raw_ai_confidence: Decimal,
    fees: Decimal = Decimal("0.00"), gst: Decimal = Decimal("0.00"), tds: Decimal = Decimal("0.00"),
) -> ValidationResult:
    """Compatibility wrapper for existing callers; new code passes response JSON."""
    invoice = NormalizedRecord(source_type="invoice", transaction_id="validator-invoice", amount=invoice_amount, txn_date=date.today(), status="paid")
    settlement = NormalizedRecord(source_type="settlement", transaction_id="validator-settlement", amount=settlement_amount, txn_date=date.today(), status="settled", fees=fees, gst=gst, tds=tds)
    evidence = {"processing_fee": "settlement.fees", "gst_deduction": "settlement.gst", "tds_deduction": "settlement.tds"}
    return validate_finance_verification({
        "difference_amount": difference_amount, "likely_reason": likely_reason,
        "reasoning_explanation": "Compatibility wrapper claim.", "expected_value": claimed_expected_value,
        "confidence_score": raw_ai_confidence, "evidence_field": evidence.get(likely_reason, "settlement.amount"),
    }, invoice, settlement)
