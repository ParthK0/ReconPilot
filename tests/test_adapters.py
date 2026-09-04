"""
tests/test_adapters.py
======================
Unit tests for the Provider-Agnostic Adapter Layer.
Validates:
1. RazorpayAdapter: Mode separation (DEMO vs PRODUCTION), sandbox synchronization, and disclaimer labeling.
2. StripeAdapter & CashfreeAdapter: Multi-gateway compliance.
3. HDFCBankAdapter & TallyERPAdapter: Commercial bank and ERP normalization.
"""

from decimal import Decimal
import pandas as pd
import pytest

from backend.integrations.base import IntegrationMode, BaseGatewayAdapter, BaseBankAdapter, BaseERPAdapter
from backend.integrations.gateways.razorpay import RazorpayAdapter
from backend.integrations.gateways.stripe import StripeAdapter
from backend.integrations.gateways.cashfree import CashfreeAdapter
from backend.integrations.bank.hdfc import HDFCBankAdapter
from backend.integrations.erp.tally import TallyERPAdapter


def test_razorpay_adapter_mode_detection():
    # Test key -> DEMO mode
    adapter_demo = RazorpayAdapter(key_id="rzp_test_1234567890", key_secret="secret")
    assert adapter_demo.mode == IntegrationMode.DEMO
    assert adapter_demo.provider_name == "razorpay"

    # Live key -> PRODUCTION mode
    adapter_prod = RazorpayAdapter(key_id="rzp_live_1234567890", key_secret="secret")
    assert adapter_prod.mode == IntegrationMode.PRODUCTION


def test_razorpay_adapter_sandbox_sync_with_disclaimer():
    adapter = RazorpayAdapter(key_id="rzp_test_mock", key_secret="secret")
    orders = [
        {
            "order_id": "order_MOCK01",
            "amount_paisa": 499900,
            "amount_inr": "4999.00",
            "customer_name": "Test User",
        }
    ]
    result = adapter.sync_sandbox_batch(orders, simulate_if_unpaid=True)
    assert result.status == "success"
    assert result.mode == IntegrationMode.DEMO
    assert "Demo bank statement generator for Razorpay Test Mode" in result.notes
    assert len(result.records["settlements"]) == 1
    assert len(result.records["invoices"]) == 1
    assert len(result.records["bank_statements"]) == 1

    # Check fee calculation
    settlement = result.records["settlements"][0]
    assert settlement["fees"] == "99.98"  # 2% of 4999.00
    assert settlement["gst"] == "18.00"   # 18% of 99.98


def test_multi_gateway_adapters():
    stripe = StripeAdapter(api_key="sk_test_123")
    assert isinstance(stripe, BaseGatewayAdapter)
    assert stripe.provider_name == "stripe"
    assert stripe.health_check() is True

    cashfree = CashfreeAdapter(app_id="CF123", secret_key="CFSEC")
    assert isinstance(cashfree, BaseGatewayAdapter)
    assert cashfree.provider_name == "cashfree"
    assert cashfree.health_check() is True


def test_hdfc_bank_adapter():
    adapter = HDFCBankAdapter()
    assert isinstance(adapter, BaseBankAdapter)
    assert adapter.bank_code == "HDFC"

    raw_df = pd.DataFrame([
        {
            "Date": "21/08/2026",
            "Narration": "NEFT CR-RAZORPAY SOFTWARE PRIVATE LIMITED-HDFCR520260821000001-CMS",
            "Chq./Ref.No.": "HDFCR520260821000001",
            "Credit": "₹ 12,499.00",
            "Closing Balance": "₹ 25,00,000.00",
        }
    ])
    records = adapter.import_statements(raw_df)
    assert len(records) == 1
    rec = records[0]
    assert rec["amount"] == "12499.00"
    assert rec["txn_date"] == "2026-08-21"
    assert rec["reference_number"] == "HDFCR520260821000001"
    assert rec["status"] == "credited"


def test_tally_erp_adapter():
    adapter = TallyERPAdapter()
    assert isinstance(adapter, BaseERPAdapter)
    assert adapter.erp_name == "tally"

    raw_df = pd.DataFrame([
        {
            "Vch No.": "INV-2026-001",
            "Buyer Ref": "order_TXz12345",
            "Gross Total": "₹ 12,499.00",
            "Date": "19/08/2026",
            "Party's Name": "Acme Corp",
        }
    ])
    records = adapter.import_invoices(raw_df)
    assert len(records) == 1
    rec = records[0]
    assert rec["invoice_id"] == "INV-2026-001"
    assert rec["order_id"] == "ORDER_TXZ12345"
    assert rec["amount"] == "12499.00"
    assert rec["invoice_date"] == "2026-08-19"
