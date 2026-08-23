"""Fixed-schedule fee, GST, and TDS reconciliation helpers.

This module deliberately validates the rate card as well as the arithmetic.
That prevents an arbitrary manual adjustment stored in ``settlement.fees``
from being promoted to a deterministic rule match.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List

from pydantic import BaseModel, Field


ONE_PAISA = Decimal("0.01")
STANDARD_FEE_RATE = Decimal("0.02")
STANDARD_GST_RATE = Decimal("0.18")
STANDARD_TDS_RATE = Decimal("0.01")


def _to_paisa(amount: Decimal) -> Decimal:
    return amount.quantize(ONE_PAISA, rounding=ROUND_HALF_UP)


class ChargeBreakdown(BaseModel):
    """One documented settlement charge that explains part of a delta."""

    charge: str
    amount: Decimal
    evidence_field: str


class AdjustedAmountBreakdown(BaseModel):
    """Reusable deterministic arithmetic evidence for a charge adjustment."""

    is_matched: bool
    charges: List[ChargeBreakdown] = Field(default_factory=list)
    difference_amount: Decimal
    total_deductions: Decimal
    expected_settlement_amount: Decimal


def explain_fixed_schedule_deduction(
    invoice_amount: Decimal,
    settlement_amount: Decimal,
    fees: Decimal = Decimal("0.00"),
    gst: Decimal = Decimal("0.00"),
    tds: Decimal = Decimal("0.00"),
    tolerance: Decimal = ONE_PAISA,
) -> AdjustedAmountBreakdown:
    """Explain a mismatch only when it follows ReconPilot's fixed rate card.

    The expected values are rounded to paisa before comparison, matching the
    synthetic-data generator.  GST is 18% of the standard 2% fee (0.36% of
    the invoice), allowing records that contain only the applicable charges.
    """
    charges = []
    expected_charges = {
        "fees": _to_paisa(invoice_amount * STANDARD_FEE_RATE),
        "gst": _to_paisa(invoice_amount * STANDARD_FEE_RATE * STANDARD_GST_RATE),
        "tds": _to_paisa(invoice_amount * STANDARD_TDS_RATE),
    }
    actual_charges = {"fees": fees, "gst": gst, "tds": tds}

    for name, amount in actual_charges.items():
        if amount < Decimal("0.00"):
            return _unmatched_breakdown(invoice_amount, settlement_amount, fees, gst, tds)
        if amount > Decimal("0.00"):
            if abs(amount - expected_charges[name]) > tolerance:
                return _unmatched_breakdown(invoice_amount, settlement_amount, fees, gst, tds)
            charges.append(
                ChargeBreakdown(
                    charge=name,
                    amount=amount,
                    evidence_field=f"settlement.{name}",
                )
            )

    total_deductions = fees + gst + tds
    difference_amount = invoice_amount - settlement_amount
    expected_settlement_amount = invoice_amount - total_deductions
    is_matched = (
        invoice_amount > Decimal("0.00")
        and settlement_amount > Decimal("0.00")
        and bool(charges)
        and difference_amount > Decimal("0.00")
        and abs(difference_amount - total_deductions) <= tolerance
        and abs(expected_settlement_amount - settlement_amount) <= tolerance
    )
    return AdjustedAmountBreakdown(
        is_matched=is_matched,
        charges=charges if is_matched else [],
        difference_amount=difference_amount,
        total_deductions=total_deductions,
        expected_settlement_amount=expected_settlement_amount,
    )


def _unmatched_breakdown(
    invoice_amount: Decimal,
    settlement_amount: Decimal,
    fees: Decimal,
    gst: Decimal,
    tds: Decimal,
) -> AdjustedAmountBreakdown:
    total_deductions = fees + gst + tds
    return AdjustedAmountBreakdown(
        is_matched=False,
        difference_amount=invoice_amount - settlement_amount,
        total_deductions=total_deductions,
        expected_settlement_amount=invoice_amount - total_deductions,
    )
