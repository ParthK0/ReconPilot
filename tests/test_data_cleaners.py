from datetime import date
from decimal import Decimal
import pytest

from backend.normalizer.data_cleaners import (
    clean_currency,
    clean_date,
    clean_reference,
    clean_order_id,
    clean_status,
)


def test_clean_currency_various_formats():
    assert clean_currency("₹12,000") == Decimal("12000.00")
    assert clean_currency("₹12,000.00") == Decimal("12000.00")
    assert clean_currency("12,000.50") == Decimal("12000.50")
    assert clean_currency("12000 INR") == Decimal("12000")
    assert clean_currency("₹ 12,000.00") == Decimal("12000.00")
    assert clean_currency("12000") == Decimal("12000")
    assert clean_currency(12000) == Decimal("12000")
    assert clean_currency(12000.50) == Decimal("12000.50")
    assert clean_currency("-₹50.00") == Decimal("-50.00")
    assert clean_currency("(50.00)") == Decimal("-50.00")
    assert clean_currency(None) == Decimal("0.00")
    assert clean_currency("") == Decimal("0.00")


def test_clean_date_various_formats():
    expected = date(2026, 8, 21)
    assert clean_date("2026-08-21") == expected
    assert clean_date("21-08-2026") == expected
    assert clean_date("21/08/2026") == expected
    assert clean_date("2026/08/21") == expected
    assert clean_date("08/21/2026") == expected
    assert clean_date("21/08/26") == expected
    assert clean_date("08-21-26") == expected
    assert clean_date("21 Aug 2026") == expected
    assert clean_date("21-Aug-2026") == expected
    assert clean_date("Aug 21, 2026") == expected
    assert clean_date("21 Aug", default_year=2026) == expected
    assert clean_date("2026-08-21T14:30:00Z") == expected


def test_clean_reference_normalization():
    assert clean_reference("ABC123") == "ABC123"
    assert clean_reference("abc123") == "ABC123"
    assert clean_reference("ABC-123") == "ABC123"
    assert clean_reference("ABC 123") == "ABC123"
    assert clean_reference("UTR_202608_0001") == "UTR2026080001"
    assert clean_reference(None) is None
    assert clean_reference("") is None


def test_clean_order_id():
    assert clean_order_id("ord-123") == "ORD-123"
    assert clean_order_id("  PO-9988  ") == "PO-9988"
    assert clean_order_id(None) is None


def test_clean_status_synonyms():
    assert clean_status("PAID") == "paid"
    assert clean_status("Success") == "paid"
    assert clean_status("captured") == "paid"
    assert clean_status("Settled") == "settled"
    assert clean_status("CREDITED") == "credited"
    assert clean_status("debited") == "debited"
    assert clean_status("refund_processed") == "refund_processed"
    assert clean_status("reversed") == "refund_processed"
