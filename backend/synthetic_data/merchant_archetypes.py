"""
backend/synthetic_data/merchant_archetypes.py
=============================================
ReconPilot 2.0: 10 Comprehensive Industry Merchant Archetypes.

Defines realistic payment behaviors, schema variations, settlement patterns,
currency formats, date formatting, and exception profiles across:
1. Restaurant (F&B / POS / Tips)
2. Marketplace (B2B2C / Escrow / Split Payouts)
3. SaaS & Cloud (Subscriptions / Pro-rata / Gateway Retries)
4. Travel & Hospitality (Cancellations / Convenience Fees / Commission)
5. Healthcare & TPA (Co-pays / Hospital Packages / Insurance Remittances)
6. Retail & E-Commerce (Omnichannel / Returns / COD)
7. Gaming & Digital Assets (Wallets / Prize Distributions / Section 194B TDS)
8. Education & EdTech (Installments / Scholarships / EMI fee schedules)
9. Logistics & Supply Chain (COD Remittance / Delivery Failure Penalties / 194C TDS)
10. Enterprise B2B (Bulk Invoices / Section 194J TDS / 30-day payment cycles)
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class MerchantArchetype(BaseModel):
    merchant_type: str
    display_name: str
    description: str
    fee_config_name: str
    default_ticket_range: tuple[float, float] = (500.0, 25000.0)
    
    # Custom Column mappings (Schema variations)
    invoice_columns: Dict[str, str]
    settlement_columns: Dict[str, str]
    bank_columns: Dict[str, str]
    
    # Formatting styles
    currency_format: str  # "clean", "rupee_symbol", "inr_suffix", "rupee_space_commas", "usd_symbol"
    date_format: str      # "%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y", "%m/%d/%Y", "%Y/%m/%d"
    
    # Specific operational traits
    primary_payment_mode: str
    typical_settlement_window_days: int
    common_exceptions: List[str]


MERCHANT_ARCHETYPES: Dict[str, MerchantArchetype] = {
    "restaurant": MerchantArchetype(
        merchant_type="restaurant",
        display_name="SpiceRoute Hospitality & Dine-in",
        description="F&B dining with tips, 5% F&B GST, daily settlement, and high-velocity UPI payments.",
        fee_config_name="restaurant",
        default_ticket_range=(250.0, 8500.0),
        invoice_columns={
            "invoice_id": "bill_no",
            "order_id": "table_order_id",
            "amount": "billed_amount",
            "invoice_date": "order_date",
            "customer_name": "guest_name",
            "status": "order_status",
        },
        settlement_columns={
            "settlement_id": "settlement_ref",
            "order_id": "table_order_id",
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
        date_format="%d/%m/%Y",
        primary_payment_mode="UPI",
        typical_settlement_window_days=1,
        common_exceptions=["settlement_delay", "wallet_adjustment", "manual_fee_adjustment", "duplicate_invoice"],
    ),

    "marketplace": MerchantArchetype(
        merchant_type="marketplace",
        display_name="BazaarHub Multi-Vendor Marketplace",
        description="Multi-vendor platform with split settlements, vendor commission, escrow holds, and 1% Section 194-O TDS.",
        fee_config_name="marketplace",
        default_ticket_range=(800.0, 45000.0),
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
        currency_format="rupee_symbol",
        date_format="%d/%m/%Y",
        primary_payment_mode="Credit/Debit Card",
        typical_settlement_window_days=2,
        common_exceptions=["escrow_hold", "split_settlement", "tds_revision", "missing_credit", "refund_pending"],
    ),

    "saas": MerchantArchetype(
        merchant_type="saas",
        display_name="CloudStack Global SaaS Solutions",
        description="B2B subscription software with recurring renewals, pro-rata billings, and chargeback holds.",
        fee_config_name="saas",
        default_ticket_range=(1500.0, 95000.0),
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
        currency_format="inr_suffix",
        date_format="%d-%b-%Y",
        primary_payment_mode="Recurring Mandate / NetBanking",
        typical_settlement_window_days=2,
        common_exceptions=["chargeback", "payment_retry", "gateway_timeout", "settlement_retry"],
    ),

    "travel": MerchantArchetype(
        merchant_type="travel",
        display_name="AeroVoyage Flights & Hospitality",
        description="Airline and hotel reservation engine with dynamic convenience fees, cancellations, and partial refunds.",
        fee_config_name="travel",
        default_ticket_range=(2500.0, 120000.0),
        invoice_columns={
            "invoice_id": "pnr_ticket_no",
            "order_id": "booking_id",
            "amount": "fare_amount",
            "invoice_date": "booking_date",
            "customer_name": "passenger_name",
            "status": "booking_status",
        },
        settlement_columns={
            "settlement_id": "settlement_id",
            "order_id": "booking_id",
            "amount": "net_settlement",
            "settlement_date": "payout_date",
            "reference_number": "utr_number",
            "status": "status",
            "fees": "convenience_fee",
            "gst": "gst_deduction",
            "tds": "tds_amount",
        },
        bank_columns={
            "bank_txn_id": "bank_id",
            "txn_date": "credit_date",
            "description": "narration",
            "reference_number": "utr_number",
            "amount": "credit_amount",
            "balance": "closing_balance",
            "status": "status",
        },
        currency_format="rupee_symbol",
        date_format="%Y-%m-%d",
        primary_payment_mode="Credit Card / NetBanking",
        typical_settlement_window_days=3,
        common_exceptions=["refund_pending", "refund_reversal", "partial_capture", "convenience_fee_override"],
    ),

    "healthcare": MerchantArchetype(
        merchant_type="healthcare",
        display_name="ApexCare Diagnostics & Hospital Network",
        description="Healthcare provider processing insurance co-pays, TPA claim disbursements, and diagnostic packages.",
        fee_config_name="healthcare",
        default_ticket_range=(1200.0, 180000.0),
        invoice_columns={
            "invoice_id": "claim_invoice_no",
            "order_id": "patient_id",
            "amount": "treatment_cost",
            "invoice_date": "admission_date",
            "customer_name": "patient_name",
            "status": "discharge_status",
        },
        settlement_columns={
            "settlement_id": "payout_batch_no",
            "order_id": "patient_id",
            "amount": "remittance_amount",
            "settlement_date": "settled_date",
            "reference_number": "bank_utr",
            "status": "status",
            "fees": "tpa_service_fee",
            "gst": "gst",
            "tds": "tds",
        },
        bank_columns={
            "bank_txn_id": "stmt_txn_id",
            "txn_date": "posting_date",
            "description": "particulars",
            "reference_number": "bank_utr",
            "amount": "amount",
            "balance": "balance",
            "status": "status",
        },
        currency_format="rupee_space_commas",
        date_format="%d/%m/%Y",
        primary_payment_mode="Corporate Insurance / UPI",
        typical_settlement_window_days=2,
        common_exceptions=["missing_bank_credit", "under_settlement", "pending_kyc_verification", "settlement_delay"],
    ),

    "retail": MerchantArchetype(
        merchant_type="retail",
        display_name="MetroMart Omnichannel Retail",
        description="Omnichannel retail merchant with online orders, POS in-store transactions, and product return deductions.",
        fee_config_name="retail",
        default_ticket_range=(450.0, 32000.0),
        invoice_columns={
            "invoice_id": "bill_id",
            "order_id": "order_id",
            "amount": "final_amount",
            "invoice_date": "invoice_date",
            "customer_name": "customer_name",
            "status": "status",
        },
        settlement_columns={
            "settlement_id": "settlement_id",
            "order_id": "order_id",
            "amount": "amount",
            "settlement_date": "settlement_date",
            "reference_number": "reference_number",
            "status": "status",
            "fees": "fees",
            "gst": "gst",
            "tds": "tds",
        },
        bank_columns={
            "bank_txn_id": "bank_txn_id",
            "txn_date": "txn_date",
            "description": "description",
            "reference_number": "reference_number",
            "amount": "amount",
            "balance": "balance",
            "status": "status",
        },
        currency_format="clean",
        date_format="%Y-%m-%d",
        primary_payment_mode="UPI / Debit Card",
        typical_settlement_window_days=2,
        common_exceptions=["settlement_delay", "duplicate_invoice", "refund_pending", "manual_fee_adjustment"],
    ),

    "gaming": MerchantArchetype(
        merchant_type="gaming",
        display_name="PlayVerse Esports & Real Money Gaming",
        description="Online gaming platform with in-game wallet reloads, prize distributions, and 30% Section 194B TDS on winnings.",
        fee_config_name="gaming",
        default_ticket_range=(100.0, 50000.0),
        invoice_columns={
            "invoice_id": "wallet_txn_no",
            "order_id": "gamer_tag_id",
            "amount": "reload_amount",
            "invoice_date": "txn_timestamp",
            "customer_name": "player_username",
            "status": "txn_status",
        },
        settlement_columns={
            "settlement_id": "payout_ref_id",
            "order_id": "gamer_tag_id",
            "amount": "net_wallet_payout",
            "settlement_date": "settlement_timestamp",
            "reference_number": "utr_ref",
            "status": "status",
            "fees": "platform_commission",
            "gst": "gst_28_percent",
            "tds": "tds_194b_deduction",
        },
        bank_columns={
            "bank_txn_id": "bank_line_id",
            "txn_date": "value_date",
            "description": "statement_narration",
            "reference_number": "utr_ref",
            "amount": "amount",
            "balance": "ledger_balance",
            "status": "status",
        },
        currency_format="rupee_symbol",
        date_format="%Y-%m-%d",
        primary_payment_mode="UPI / IMPS",
        typical_settlement_window_days=1,
        common_exceptions=["tds_revision", "wallet_adjustment", "fraud_hold", "gateway_timeout"],
    ),

    "education": MerchantArchetype(
        merchant_type="education",
        display_name="ZenithEd Global Learning Academy",
        description="Higher education and EdTech platform with quarterly tuition EMIs, scholarships, and zero TDS.",
        fee_config_name="education",
        default_ticket_range=(3500.0, 250000.0),
        invoice_columns={
            "invoice_id": "fee_receipt_no",
            "order_id": "enrollment_id",
            "amount": "semester_fee",
            "invoice_date": "registration_date",
            "customer_name": "student_name",
            "status": "fee_status",
        },
        settlement_columns={
            "settlement_id": "disbursement_no",
            "order_id": "enrollment_id",
            "amount": "settlement_amount",
            "settlement_date": "credit_date",
            "reference_number": "cheque_or_utr",
            "status": "status",
            "fees": "bank_subvention_fee",
            "gst": "tax_on_fee",
            "tds": "tds",
        },
        bank_columns={
            "bank_txn_id": "entry_ref",
            "txn_date": "booking_date",
            "description": "memo_text",
            "reference_number": "cheque_or_utr",
            "amount": "amount",
            "balance": "available_funds",
            "status": "status",
        },
        currency_format="rupee_space_commas",
        date_format="%d-%b-%Y",
        primary_payment_mode="NetBanking / EMI Loan",
        typical_settlement_window_days=2,
        common_exceptions=["split_settlement", "settlement_holiday", "manual_refund", "missing_credit"],
    ),

    "logistics": MerchantArchetype(
        merchant_type="logistics",
        display_name="SwiftFreight 3PL & Courier Express",
        description="Supply chain logistics with Cash on Delivery (COD) collection, freight adjustments, and Section 194C TDS.",
        fee_config_name="logistics",
        default_ticket_range=(350.0, 18500.0),
        invoice_columns={
            "invoice_id": "waybill_no",
            "order_id": "consignee_order_id",
            "amount": "cod_amount",
            "invoice_date": "dispatch_date",
            "customer_name": "consignee_name",
            "status": "delivery_status",
        },
        settlement_columns={
            "settlement_id": "remittance_id",
            "order_id": "consignee_order_id",
            "amount": "net_cod_remittance",
            "settlement_date": "remittance_date",
            "reference_number": "utr_no",
            "status": "status",
            "fees": "freight_charge",
            "gst": "gst_18",
            "tds": "tds_194c",
        },
        bank_columns={
            "bank_txn_id": "txn_seq",
            "txn_date": "statement_date",
            "description": "particulars",
            "reference_number": "utr_no",
            "amount": "amount",
            "balance": "balance",
            "status": "status",
        },
        currency_format="clean",
        date_format="%Y/%m/%d",
        primary_payment_mode="Cash on Delivery / UPI QR",
        typical_settlement_window_days=4,
        common_exceptions=["settlement_delay", "network_failure", "under_settlement", "double_settlement"],
    ),

    "enterprise": MerchantArchetype(
        merchant_type="enterprise",
        display_name="Titan Industrial Enterprise Solutions",
        description="B2B industrial supplier with bulk purchase orders, 2% Section 194C / 10% 194J corporate TDS, and 30-day billing cycles.",
        fee_config_name="enterprise",
        default_ticket_range=(15000.0, 850000.0),
        invoice_columns={
            "invoice_id": "document_number",
            "order_id": "po_number",
            "amount": "total_invoice_val",
            "invoice_date": "created_at",
            "customer_name": "client_entity_name",
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
        currency_format="rupee_space_commas",
        date_format="%Y/%m/%d",
        primary_payment_mode="NEFT / RTGS / Corporate Mandate",
        typical_settlement_window_days=2,
        common_exceptions=["tds_revision", "missing_utr", "over_settlement", "bank_maintenance", "unknown_discrepancy"],
    ),

    "cross_border_saas": MerchantArchetype(
        merchant_type="cross_border_saas",
        display_name="CloudMatrix Global B2B SaaS",
        description="Global subscription SaaS processing USD, EUR, and GBP with international card conversions, Razorpay 3% FX spread, and split bank tranches.",
        fee_config_name="saas",
        default_ticket_range=(3500.0, 185000.0),
        invoice_columns={
            "invoice_id": "inv_number",
            "order_id": "subscription_order_id",
            "amount": "gross_usd_inr",
            "invoice_date": "bill_date",
            "customer_name": "client_org",
            "status": "status",
        },
        settlement_columns={
            "settlement_id": "intl_payout_id",
            "order_id": "subscription_order_id",
            "amount": "settled_inr",
            "settlement_date": "conversion_date",
            "reference_number": "swift_utr",
            "status": "status",
            "fees": "fx_markup_fee",
            "gst": "gst_on_fx",
            "tds": "tax_deducted",
        },
        bank_columns={
            "bank_txn_id": "swift_ref",
            "txn_date": "credit_date",
            "description": "narration",
            "reference_number": "swift_utr",
            "amount": "inr_credit",
            "balance": "balance",
            "status": "status",
        },
        currency_format="clean",
        date_format="%Y-%m-%d",
        primary_payment_mode="International Visa / Mastercard / AMEX",
        typical_settlement_window_days=3,
        common_exceptions=["fx_rate_variance", "settlement_delay", "chargeback_debit", "cross_border_withholding"],
    ),
}


def get_archetype(name: str) -> MerchantArchetype:
    """Returns a registered MerchantArchetype by name."""
    norm_name = name.strip().lower()
    if norm_name in ("subscription", "cloud_saas"):
        norm_name = "saas"
    if norm_name in ("global_saas", "international_saas", "cross_border"):
        norm_name = "cross_border_saas"
    if norm_name not in MERCHANT_ARCHETYPES:
        raise ValueError(
            f"Unknown merchant archetype '{name}'. Allowed archetypes: {list(MERCHANT_ARCHETYPES.keys())}"
        )
    return MERCHANT_ARCHETYPES[norm_name]

