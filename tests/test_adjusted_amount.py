from datetime import date
from decimal import Decimal

import pytest

from backend.normalizer import NormalizedRecord
from backend.rules import match_fee_gst_tds_adjusted_amount


def _record(source_type: str, amount: str, **charges: str) -> NormalizedRecord:
    return NormalizedRecord(
        source_type=source_type,
        transaction_id=f"{source_type}-1",
        amount=Decimal(amount),
        txn_date=date(2026, 8, 1),
        status="settled" if source_type == "settlement" else "paid",
        fees=Decimal(charges.get("fees", "0.00")),
        gst=Decimal(charges.get("gst", "0.00")),
        tds=Decimal(charges.get("tds", "0.00")),
    )


@pytest.mark.parametrize(
    ("invoice_amount", "settlement_amount", "charges", "expected_charges"),
    [
        ("10000.00", "9800.00", {"fees": "200.00"}, ["fees"]),
        ("10000.00", "9964.00", {"gst": "36.00"}, ["gst"]),
        ("10000.00", "9900.00", {"tds": "100.00"}, ["tds"]),
        (
            "10000.00",
            "9664.00",
            {"fees": "200.00", "gst": "36.00", "tds": "100.00"},
            ["fees", "gst", "tds"],
        ),
    ],
)
def test_matches_fixed_schedule_charge_combinations(
    invoice_amount, settlement_amount, charges, expected_charges
):
    result = match_fee_gst_tds_adjusted_amount(
        invoice=_record("invoice", invoice_amount),
        settlement=_record("settlement", settlement_amount, **charges),
    )

    assert result.is_matched is True
    assert result.rule_name == "fee_gst_tds_adjusted_amount"
    assert [charge.charge for charge in result.charge_breakdown.charges] == expected_charges


def test_does_not_false_positive_when_delta_does_not_reconcile():
    result = match_fee_gst_tds_adjusted_amount(
        invoice=_record("invoice", "10000.00"),
        settlement=_record("settlement", "9799.98", fees="200.00"),
    )

    assert result.is_matched is False


def test_non_standard_one_off_fee_falls_through_to_ai():
    result = match_fee_gst_tds_adjusted_amount(
        invoice=_record("invoice", "12000.00"),
        settlement=_record("settlement", "11970.00", fees="30.00"),
    )

    assert result.is_matched is False
