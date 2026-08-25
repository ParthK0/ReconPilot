from decimal import Decimal
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from backend.config.fee_rules import FeeConfig, load_fee_config


class MerchantProfile(BaseModel):
    """
    Specification for a merchant profile including schema column names,
    formatting styles, fee config, and behavioral nuances.
    """
    merchant_type: str
    display_name: str
    fee_config_name: str
    
    # Custom column names for each file type
    invoice_columns: Dict[str, str]  # canonical_name -> merchant_col_name
    settlement_columns: Dict[str, str]
    bank_columns: Dict[str, str]
    
    # Formatting nuances
    currency_format: str  # "clean", "rupee_symbol", "inr_suffix", "rupee_space_commas"
    date_format: str      # "%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y", "%m/%d/%Y", "%Y/%m/%d"
    
    @property
    def fee_config(self) -> FeeConfig:
        return load_fee_config(self.fee_config_name)


MERCHANT_PROFILES: Dict[str, MerchantProfile] = {
    "retail": MerchantProfile(
        merchant_type="retail",
        display_name="QuickMart Retail Ltd (D2C / E-Commerce)",
        fee_config_name="retail",
        invoice_columns={
            "invoice_id": "inv_id",
            "order_id": "order_no",
            "amount": "invoice_value",
            "invoice_date": "bill_date",
            "customer_name": "customer",
            "status": "state",
        },
        settlement_columns={
            "settlement_id": "set_id",
            "order_id": "order_no",
            "amount": "settlement_value",
            "settlement_date": "payout_date",
            "reference_number": "utr_no",
            "status": "state",
            "fees": "mdr",
            "gst": "gst_amount",
            "tds": "tds_deducted",
        },
        bank_columns={
            "bank_txn_id": "statement_id",
            "txn_date": "posting_date",
            "description": "narration",
            "reference_number": "utr_no",
            "amount": "credit_amount",
            "balance": "closing_balance",
            "status": "state",
        },
        currency_format="clean",
        date_format="%Y-%m-%d",
    ),
    "marketplace": MerchantProfile(
        merchant_type="marketplace",
        display_name="BazaarHub Multi-Vendor Marketplace",
        fee_config_name="marketplace",
        invoice_columns={
            "invoice_id": "invoice_number",
            "order_id": "order_number",
            "amount": "gross_amount",
            "invoice_date": "created_date",
            "customer_name": "buyer_name",
            "status": "status",
        },
        settlement_columns={
            "settlement_id": "payout_id",
            "order_id": "order_number",
            "amount": "settlement_amount",
            "settlement_date": "settled_at",
            "reference_number": "bank_ref_no",
            "status": "status",
            "fees": "processing_fees",
            "gst": "tax_amount",
            "tds": "withholding_tax",
        },
        bank_columns={
            "bank_txn_id": "bank_ref",
            "txn_date": "value_date",
            "description": "particulars",
            "reference_number": "bank_ref_no",
            "amount": "amount",
            "balance": "balance",
            "status": "status",
        },
        currency_format="rupee_symbol",  # e.g. ₹12,000.00
        date_format="%d/%m/%Y",
    ),
    "subscription": MerchantProfile(
        merchant_type="subscription",
        display_name="CloudSaaS Subscriptions & Billing",
        fee_config_name="subscription",
        invoice_columns={
            "invoice_id": "receipt_id",
            "order_id": "merchant_order_id",
            "amount": "total_value",
            "invoice_date": "billing_date",
            "customer_name": "account_name",
            "status": "payment_status",
        },
        settlement_columns={
            "settlement_id": "disbursement_id",
            "order_id": "merchant_order_id",
            "amount": "net_payout",
            "settlement_date": "deposit_date",
            "reference_number": "utr",
            "status": "settlement_status",
            "fees": "gateway_fee",
            "gst": "tax",
            "tds": "tds",
        },
        bank_columns={
            "bank_txn_id": "txn_id",
            "txn_date": "statement_date",
            "description": "transaction_details",
            "reference_number": "utr",
            "amount": "amount",
            "balance": "available_balance",
            "status": "txn_status",
        },
        currency_format="inr_suffix",  # e.g. 12000.00 INR
        date_format="%d-%b-%Y",        # e.g. 21-Aug-2026
    ),
    "restaurant": MerchantProfile(
        merchant_type="restaurant",
        display_name="SpiceRoute Hospitality & POS",
        fee_config_name="restaurant",
        invoice_columns={
            "invoice_id": "bill_no",
            "order_id": "order_id",
            "amount": "billed_amount",
            "invoice_date": "order_date",
            "customer_name": "payer_name",
            "status": "order_status",
        },
        settlement_columns={
            "settlement_id": "settlement_ref",
            "order_id": "order_id",
            "amount": "amount_paid",
            "settlement_date": "settle_date",
            "reference_number": "rrn",
            "status": "state",
            "fees": "commission",
            "gst": "service_tax",
            "tds": "tax_deducted",
        },
        bank_columns={
            "bank_txn_id": "entry_id",
            "txn_date": "trans_date",
            "description": "memo",
            "reference_number": "rrn",
            "amount": "amount",
            "balance": "account_balance",
            "status": "state",
        },
        currency_format="clean",
        date_format="%m/%d/%Y",
    ),
    "enterprise": MerchantProfile(
        merchant_type="enterprise",
        display_name="Titan Industrial Enterprise Solutions",
        fee_config_name="enterprise",
        invoice_columns={
            "invoice_id": "document_number",
            "order_id": "po_number",
            "amount": "total",
            "invoice_date": "created_at",
            "customer_name": "client_name",
            "status": "status",
        },
        settlement_columns={
            "settlement_id": "batch_id",
            "order_id": "po_number",
            "amount": "net_amount",
            "settlement_date": "value_date",
            "reference_number": "payment_reference",
            "status": "status",
            "fees": "charges",
            "gst": "tax",
            "tds": "tds_amount",
        },
        bank_columns={
            "bank_txn_id": "line_id",
            "txn_date": "booking_date",
            "description": "description",
            "reference_number": "payment_reference",
            "amount": "amount",
            "balance": "ledger_balance",
            "status": "status",
        },
        currency_format="rupee_space_commas",  # e.g. ₹ 12,000.00
        date_format="%Y/%m/%d",
    ),
}


def get_merchant_profile(name: str) -> MerchantProfile:
    """Returns a registered MerchantProfile by name."""
    name_lower = name.strip().lower()
    if name_lower not in MERCHANT_PROFILES:
        raise ValueError(f"Unknown merchant profile '{name}'. Choose from: {list(MERCHANT_PROFILES.keys())}")
    return MERCHANT_PROFILES[name_lower]
