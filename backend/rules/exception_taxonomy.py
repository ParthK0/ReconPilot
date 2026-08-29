"""
backend/rules/exception_taxonomy.py
===================================
ReconPilot 2.0: 30+ Comprehensive Financial Exception Taxonomy.

Standardizes operational discrepancy categories into 8 functional operational domains:
1. Settlement Timing (5)
2. Gateway & Transmission (5)
3. Deductions & Charge Overrides (5)
4. Statutory & Tax Variations (4)
5. Disputes, Risk & Holds (4)
6. Discrepant Payouts (6)
7. Invoices & Refunds (5)
8. Unclassified (1)
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ExceptionDefinition(BaseModel):
    category_id: str
    domain: str
    display_title: str
    description: str
    requires_human_review: bool = True
    suggested_action: str
    financial_impact: str  # "timing", "shortfall", "excess", "statutory", "dispute"


EXCEPTION_DEFINITIONS: Dict[str, ExceptionDefinition] = {
    # 1. Settlement Timing
    "settlement_delay": ExceptionDefinition(
        category_id="settlement_delay",
        domain="Settlement Timing",
        display_title="Settlement Delay",
        description="Payout has not credited within standard T+2 settlement window.",
        suggested_action="Monitor gateway payout queue; flag if delayed past T+4.",
        financial_impact="timing",
    ),
    "settlement_holiday": ExceptionDefinition(
        category_id="settlement_holiday",
        domain="Settlement Timing",
        display_title="Banking / Settlement Holiday",
        description="Settlement cycle deferred due to RTGS/NEFT clearing holiday or central bank non-working day.",
        suggested_action="Allow +1 business day for clearing before triggering dispute.",
        financial_impact="timing",
    ),
    "weekend_settlement": ExceptionDefinition(
        category_id="weekend_settlement",
        domain="Settlement Timing",
        display_title="Weekend Settlement Rollover",
        description="Transaction captured on weekend and scheduled for next Monday batch.",
        suggested_action="Auto-reconcile against Monday settlement ledger.",
        financial_impact="timing",
    ),
    "late_settlement": ExceptionDefinition(
        category_id="late_settlement",
        domain="Settlement Timing",
        display_title="Late Settlement Beyond SLA",
        description="Payout credited 5+ business days past capture window, exceeding contractual gateway SLA.",
        suggested_action="Log SLA breach ticket with payment aggregator.",
        financial_impact="timing",
    ),
    "bank_maintenance": ExceptionDefinition(
        category_id="bank_maintenance",
        domain="Settlement Timing",
        display_title="Bank Node Downtime / Maintenance",
        description="ACH / IMPS batch delayed due to beneficiary banking maintenance window.",
        suggested_action="Verify downstream CBS (Core Banking System) statement batch.",
        financial_impact="timing",
    ),

    # 2. Gateway & Transmission
    "gateway_timeout": ExceptionDefinition(
        category_id="gateway_timeout",
        domain="Gateway & System",
        display_title="Gateway Timeout / State Ambiguity",
        description="Payment state timed out between merchant server and gateway webhook callback.",
        suggested_action="Perform server-to-server status poll on Razorpay order API.",
        financial_impact="timing",
    ),
    "payment_retry": ExceptionDefinition(
        category_id="payment_retry",
        domain="Gateway & System",
        display_title="Payment Retry Surcharge",
        description="Customer re-attempted failed payment; subsequent capture contains retry fee adjustment.",
        suggested_action="Verify single capture idempotency on order_id.",
        financial_impact="shortfall",
    ),
    "network_failure": ExceptionDefinition(
        category_id="network_failure",
        domain="Gateway & System",
        display_title="Inter-Bank Switch Network Failure",
        description="NPCI/Card switch packet dropped during UTR acknowledgement.",
        suggested_action="Request UTR re-query from acquiring bank.",
        financial_impact="timing",
    ),
    "settlement_rollback": ExceptionDefinition(
        category_id="settlement_rollback",
        domain="Gateway & System",
        display_title="Settlement Rollback / Reversal",
        description="Aggregator rolled back a faulty batch disbursement.",
        suggested_action="Check offset transaction in next batch ledger.",
        financial_impact="shortfall",
    ),
    "settlement_retry": ExceptionDefinition(
        category_id="settlement_retry",
        domain="Gateway & System",
        display_title="Settlement Re-Disbursement",
        description="Earlier failed payout re-initiated with fresh reference UTR.",
        suggested_action="Match against latest secondary UTR reference.",
        financial_impact="timing",
    ),

    # 3. Deductions & Charge Overrides
    "manual_fee_adjustment": ExceptionDefinition(
        category_id="manual_fee_adjustment",
        domain="Deductions & Adjustments",
        display_title="Manual Fee Override / Waiver",
        description="Ad-hoc processing fee adjustment or volume rebate not on standard rate schedule.",
        suggested_action="Verify authorized merchant manager approval email.",
        financial_impact="shortfall",
    ),
    "wallet_adjustment": ExceptionDefinition(
        category_id="wallet_adjustment",
        domain="Deductions & Adjustments",
        display_title="Merchant Wallet Balance Adjustment",
        description="Negative ledger offset applied from merchant nodal wallet balance.",
        suggested_action="Reconcile with merchant prepaid reserve ledger.",
        financial_impact="shortfall",
    ),
    "coupon_adjustment": ExceptionDefinition(
        category_id="coupon_adjustment",
        domain="Deductions & Adjustments",
        display_title="Promotional Discount / Coupon Subsidy",
        description="Gateway sponsored promotional discount deducted from merchant net payout.",
        suggested_action="Claim promotion reimbursement from marketing co-op ledger.",
        financial_impact="shortfall",
    ),
    "chargeback": ExceptionDefinition(
        category_id="chargeback",
        domain="Deductions & Adjustments",
        display_title="Cardholder Chargeback Debit",
        description="Customer disputed transaction with issuing bank; amount clawed back with chargeback fee.",
        suggested_action="Submit proof of delivery or fulfillment within 7 days.",
        financial_impact="dispute",
    ),
    "convenience_fee_override": ExceptionDefinition(
        category_id="convenience_fee_override",
        domain="Deductions & Adjustments",
        display_title="Convenience Fee Variance",
        description="Dynamic platform convenience surcharge differs from ERP billed line item.",
        suggested_action="Re-calculate net platform margin against surcharge policy.",
        financial_impact="shortfall",
    ),

    # 4. Statutory & Tax Variations
    "tds_revision": ExceptionDefinition(
        category_id="tds_revision",
        domain="Tax & Statutory",
        display_title="TDS Rate Revision / Threshold Breach",
        description="Section 194-O/194-C TDS rate revised mid-quarter following ₹50L aggregate threshold breach.",
        suggested_action="Update merchant tax rate matrix in ERP tax master.",
        financial_impact="statutory",
    ),
    "gst_revision": ExceptionDefinition(
        category_id="gst_revision",
        domain="Tax & Statutory",
        display_title="GST Statutory Variance",
        description="Discrepancy in 18% or 28% GST computation on gateway MDR fee components.",
        suggested_action="Cross-reference with Monthly GSTR-2B filing report.",
        financial_impact="statutory",
    ),
    "missing_tds_credit": ExceptionDefinition(
        category_id="missing_tds_credit",
        domain="Tax & Statutory",
        display_title="Missing TDS Certificate / Form 26AS",
        description="TDS deducted at source by gateway but missing Form 16A credit in 26AS portal.",
        suggested_action="Request quarterly TDS certificate from Razorpay finance ops.",
        financial_impact="statutory",
    ),
    "cross_state_igst_mismatch": ExceptionDefinition(
        category_id="cross_state_igst_mismatch",
        domain="Tax & Statutory",
        display_title="IGST vs CGST/SGST State Mismatch",
        description="Place of supply mismatch leading to inter-state vs intra-state tax split discrepancy.",
        suggested_action="Align merchant billing address state code with gateway nodal account.",
        financial_impact="statutory",
    ),

    # 5. Disputes, Risk & Holds
    "escrow_hold": ExceptionDefinition(
        category_id="escrow_hold",
        domain="Disputes & Holds",
        display_title="Marketplace Escrow Hold",
        description="Settlement withheld in marketplace nodal escrow pending delivery confirmation.",
        suggested_action="Upload logistics delivery proof to release escrow payout.",
        financial_impact="timing",
    ),
    "fraud_hold": ExceptionDefinition(
        category_id="fraud_hold",
        domain="Disputes & Holds",
        display_title="Risk Engine Suspicious Activity Hold",
        description="Automated fraud detection engine flagged transaction for secondary review.",
        suggested_action="Verify KYC credentials with risk compliance team.",
        financial_impact="dispute",
    ),
    "partial_capture": ExceptionDefinition(
        category_id="partial_capture",
        domain="Disputes & Holds",
        display_title="Partial Order Capture",
        description="Customer authorized full amount but merchant fulfilled and captured only partial order value.",
        suggested_action="Adjust ERP billed amount to match actual captured settlement.",
        financial_impact="shortfall",
    ),
    "pending_kyc_verification": ExceptionDefinition(
        category_id="pending_kyc_verification",
        domain="Disputes & Holds",
        display_title="Pending Merchant KYC Verification",
        description="Gateway paused automated settlement disbursements pending annual KYC re-verification.",
        suggested_action="Submit updated GSTIN/PAN documents to gateway compliance.",
        financial_impact="timing",
    ),

    # 6. Discrepant Payouts
    "over_settlement": ExceptionDefinition(
        category_id="over_settlement",
        domain="Payout Discrepancies",
        display_title="Over-Settlement Excess Credit",
        description="Gateway credited more funds than invoice amount; potential duplicate line credit.",
        suggested_action="Hold excess funds in suspense account; notify aggregator for clawback.",
        financial_impact="excess",
    ),
    "under_settlement": ExceptionDefinition(
        category_id="under_settlement",
        domain="Payout Discrepancies",
        display_title="Under-Settlement Unexplained Shortfall",
        description="Net bank credit is less than expected net settlement after accounting for all fees.",
        suggested_action="Audit bank deductions or intermediary bank processing charges.",
        financial_impact="shortfall",
    ),
    "double_settlement": ExceptionDefinition(
        category_id="double_settlement",
        domain="Payout Discrepancies",
        display_title="Double Payout for Single Order",
        description="Two distinct settlements and bank credits found referencing the same invoice order ID.",
        suggested_action="Reverse secondary duplicate credit to prevent balance audit flag.",
        financial_impact="excess",
    ),
    "split_settlement": ExceptionDefinition(
        category_id="split_settlement",
        domain="Payout Discrepancies",
        display_title="Multi-Part Split Settlement",
        description="Single high-value transaction settled in two separate tranches over multiple days.",
        suggested_action="Link both settlement tranche IDs to the parent invoice record.",
        financial_impact="timing",
    ),
    "missing_credit": ExceptionDefinition(
        category_id="missing_credit",
        domain="Payout Discrepancies",
        display_title="Missing Bank Credit",
        description="Gateway marks settlement status as settled, but bank statement shows no matching UTR deposit.",
        suggested_action="Initiate UTR trace investigation with beneficiary corporate bank.",
        financial_impact="shortfall",
    ),
    "missing_utr": ExceptionDefinition(
        category_id="missing_utr",
        domain="Payout Discrepancies",
        display_title="Missing Bank Reference / UTR Number",
        description="Settlement record lacks valid banking UTR reference number.",
        suggested_action="Request UTR batch report from gateway merchant operations.",
        financial_impact="timing",
    ),
    "unmatched_bank_credit": ExceptionDefinition(
        category_id="unmatched_bank_credit",
        domain="Payout Discrepancies",
        display_title="Unmatched Bank Credit Entry",
        description="Bank statement records an inflow credit that has no corresponding payment gateway settlement.",
        suggested_action="Verify direct bank transfer, interest credit, or non-gateway deposit source.",
        financial_impact="excess",
    ),

    # 7. Invoices & Refunds
    "missing_settlement": ExceptionDefinition(
        category_id="missing_settlement",
        domain="Invoices & Refunds",
        display_title="Uncollected / Missing Gateway Settlement",
        description="Invoice is recorded as paid in ERP ledger, but payment gateway generated no settlement payout.",
        suggested_action="Check gateway payment status or initiate capture reconciliation for order.",
        financial_impact="shortfall",
    ),
    "duplicate_invoice": ExceptionDefinition(
        category_id="duplicate_invoice",
        domain="Invoices & Refunds",
        display_title="Duplicate ERP Invoice",
        description="Multiple invoices share the same order ID and billed amount in ERP ledger.",
        suggested_action="Void duplicate draft invoice in ERP billing system.",
        financial_impact="excess",
    ),
    "refund_pending": ExceptionDefinition(
        category_id="refund_pending",
        domain="Invoices & Refunds",
        display_title="Customer Refund Deduction",
        description="Negative amount / debit offset in settlement representing a customer refund reversal.",
        suggested_action="Match against credit note in accounts receivable ledger.",
        financial_impact="shortfall",
    ),
    "refund_reversal": ExceptionDefinition(
        category_id="refund_reversal",
        domain="Invoices & Refunds",
        display_title="Failed Refund Re-Credit",
        description="Customer refund bounced due to closed bank account; funds returned to merchant balance.",
        suggested_action="Re-initiate refund via alternate payout mode (IMPS/UPI).",
        financial_impact="excess",
    ),
    "manual_refund": ExceptionDefinition(
        category_id="manual_refund",
        domain="Invoices & Refunds",
        display_title="Direct Out-of-Band Refund",
        description="Merchant processed refund directly via NEFT outside the payment gateway flow.",
        suggested_action="Link bank debit reference to order credit note.",
        financial_impact="shortfall",
    ),
    "invoice_amount_updated": ExceptionDefinition(
        category_id="invoice_amount_updated",
        domain="Invoices & Refunds",
        display_title="Post-Settlement Invoice Revision",
        description="Invoice modified or discount applied after settlement was already captured and paid out.",
        suggested_action="Issue supplementary debit/credit note to reconcile invoice variance.",
        financial_impact="shortfall",
    ),

    # 8. Unclassified
    "unknown_discrepancy": ExceptionDefinition(
        category_id="unknown_discrepancy",
        domain="Unclassified",
        display_title="Unresolved Complex Discrepancy",
        description="Discrepancy cannot be resolved by standard rules or verified by AI with high confidence.",
        suggested_action="Route to Senior Finance Controller for line-by-line manual investigation.",
        financial_impact="shortfall",
    ),
}


def get_exception_definition(category: str) -> ExceptionDefinition:
    """Retrieves metadata definition for a given exception category."""
    norm_cat = category.strip().lower()
    if norm_cat in ("unknown", "unclassified"):
        norm_cat = "unknown_discrepancy"
    return EXCEPTION_DEFINITIONS.get(
        norm_cat,
        EXCEPTION_DEFINITIONS["unknown_discrepancy"],
    )


def list_exception_categories() -> List[str]:
    """Returns a list of all 30+ supported exception category IDs."""
    return list(EXCEPTION_DEFINITIONS.keys())
