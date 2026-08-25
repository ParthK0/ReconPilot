from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple, Any, Set, Union
from pydantic import BaseModel, Field

from backend.config.fee_rules import FeeConfig, DEFAULT_FEE_CONFIG, load_fee_config
from backend.normalizer.normalizer import NormalizedRecord

# Documented standard rate schedule for deterministic rule matching (defaults)
STANDARD_FEE_RATE = Decimal("0.02")  # 2.0% standard Razorpay MDR
STANDARD_GST_RATE = Decimal("0.18")  # 18.0% GST on MDR fees
STANDARD_TDS_RATE = Decimal("0.01")  # 1.0% TDS under Section 194O


def round_paisa(val: Decimal) -> Decimal:
    """Rounds to 2 decimal places using half-up standard."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def find_duplicate_order_ids(invoices: List[NormalizedRecord]) -> Set[str]:
    """Identifies order IDs that appear more than once among invoices."""
    seen: Set[str] = set()
    duplicates: Set[str] = set()
    for inv in invoices:
        if inv.order_id:
            if inv.order_id in seen:
                duplicates.add(inv.order_id)
            else:
                seen.add(inv.order_id)
    return duplicates


class ChargeItem(BaseModel):
    charge: str  # 'fees', 'gst', 'tds'
    amount: Decimal


class ChargeBreakdown(BaseModel):
    charges: List[ChargeItem] = Field(default_factory=list)


class RuleMatchResult(BaseModel):
    """
    FR-5: Result of a rule engine match.
    Records which rule fired at 100% confidence with zero AI involvement.
    """
    is_matched: bool
    rule_name: Optional[str] = None
    confidence: Decimal = Decimal("100.00")
    invoice_record: Optional[NormalizedRecord] = None
    settlement_record: Optional[NormalizedRecord] = None
    bank_record: Optional[NormalizedRecord] = None
    notes: Optional[str] = None
    charge_breakdown: Optional[ChargeBreakdown] = None


# ---------------------------------------------------------------------------
# 1. Rule 1: Exact Order ID Match
# ---------------------------------------------------------------------------

def match_exact_order_id(
    invoice: Optional[NormalizedRecord] = None,
    settlement: Optional[NormalizedRecord] = None,
    bank: Optional[NormalizedRecord] = None,
    max_days: int = 2,
    duplicate_order_ids: Optional[Set[str]] = None,
) -> RuleMatchResult:
    """
    Rule 1: Exact Order ID match across sources where amounts agree directly
    and settlement is completed within standard window.
    Disallows matching if the order ID is duplicated across multiple invoices.
    """
    if invoice and settlement:
        # Check duplicate order_id exception condition
        if duplicate_order_ids and invoice.order_id in duplicate_order_ids:
            return RuleMatchResult(
                is_matched=False,
                notes=f"Ambiguous: Duplicate invoice detected for order ID '{invoice.order_id}'. Routed to exceptions.",
            )

        # Must have matching order IDs and identical amounts
        if (
            invoice.order_id
            and settlement.order_id
            and invoice.order_id.strip() == settlement.order_id.strip()
            and invoice.amount == settlement.amount
            and invoice.amount > Decimal("0.00")
            and settlement.status == "settled"
            and invoice.status == "paid"
        ):
            # Check settlement date window
            days_diff = (settlement.txn_date - invoice.txn_date).days
            if 0 <= days_diff <= max_days:
                # If bank record provided, verify bank credited the settlement
                if bank:
                    if bank.status != "credited" or bank.amount != settlement.amount:
                        return RuleMatchResult(is_matched=False)

                return RuleMatchResult(
                    is_matched=True,
                    rule_name="exact_order_id",
                    confidence=Decimal("100.00"),
                    invoice_record=invoice,
                    settlement_record=settlement,
                    bank_record=bank,
                    notes=f"Matched on exact Order ID '{invoice.order_id}' and amount Rs {invoice.amount:,.2f}.",
                )

    return RuleMatchResult(is_matched=False)


# ---------------------------------------------------------------------------
# 2. Rule 2: Exact UTR / Reference Number Match
# ---------------------------------------------------------------------------

def match_exact_reference_number(
    settlement: Optional[NormalizedRecord] = None,
    bank: Optional[NormalizedRecord] = None,
    invoice: Optional[NormalizedRecord] = None,
) -> RuleMatchResult:
    """
    Rule 2: Exact UTR / reference_number match across settlement and bank statements.
    Requires that settlement is settled, bank is credited, and invoice (if present) agrees.
    """
    if settlement and bank:
        if (
            settlement.reference_number
            and bank.reference_number
            and settlement.reference_number.strip() == bank.reference_number.strip()
            and settlement.amount == bank.amount
            and settlement.amount > Decimal("0.00")
            and settlement.status == "settled"
            and bank.status == "credited"
        ):
            # If invoice is present, it must also agree with the transaction
            if invoice and (invoice.amount != settlement.amount or invoice.status != "paid"):
                return RuleMatchResult(is_matched=False)

            return RuleMatchResult(
                is_matched=True,
                rule_name="exact_reference_number",
                confidence=Decimal("100.00"),
                invoice_record=invoice,
                settlement_record=settlement,
                bank_record=bank,
                notes=f"Matched on exact UTR '{settlement.reference_number}' and amount Rs {settlement.amount:,.2f}.",
            )

    return RuleMatchResult(is_matched=False)


# ---------------------------------------------------------------------------
# 3. Rule 3: Exact Amount Match (No Adjustment)
# ---------------------------------------------------------------------------

def match_exact_amount(
    invoice: Optional[NormalizedRecord] = None,
    settlement: Optional[NormalizedRecord] = None,
    bank: Optional[NormalizedRecord] = None,
    max_days: int = 2,
) -> RuleMatchResult:
    """
    Rule 3: Exact amount match without adjustments across active settled records within date window.
    """
    if invoice and settlement and invoice.amount > Decimal("0.00"):
        if (
            invoice.amount == settlement.amount
            and settlement.status == "settled"
            and invoice.status == "paid"
        ):
            days_diff = (settlement.txn_date - invoice.txn_date).days
            if 0 <= days_diff <= max_days:
                if bank and (bank.status != "credited" or bank.amount != settlement.amount):
                    return RuleMatchResult(is_matched=False)

                return RuleMatchResult(
                    is_matched=True,
                    rule_name="exact_amount",
                    confidence=Decimal("100.00"),
                    invoice_record=invoice,
                    settlement_record=settlement,
                    bank_record=bank,
                    notes=f"Matched on identical unadjusted amount Rs {invoice.amount:,.2f}.",
                )

    return RuleMatchResult(is_matched=False)


# ---------------------------------------------------------------------------
# 4. Rule 4: Settlement-Date Window Match (T+2 Days)
# ---------------------------------------------------------------------------

def match_settlement_date_window(
    invoice: Optional[NormalizedRecord] = None,
    settlement: Optional[NormalizedRecord] = None,
    bank: Optional[NormalizedRecord] = None,
    max_days: int = 2,
) -> RuleMatchResult:
    """
    Rule 4: Settlement-date window match (default T+2 days).
    Checks that records agree on amount and settlement occurs within [0, max_days] of transaction date.
    """
    if invoice and settlement and invoice.amount > Decimal("0.00"):
        if (
            invoice.amount == settlement.amount
            and settlement.status == "settled"
            and invoice.status == "paid"
        ):
            days_diff = (settlement.txn_date - invoice.txn_date).days
            if 0 <= days_diff <= max_days:
                if bank and (bank.status != "credited" or bank.amount != settlement.amount):
                    return RuleMatchResult(is_matched=False)

                return RuleMatchResult(
                    is_matched=True,
                    rule_name="settlement_date_window",
                    confidence=Decimal("100.00"),
                    invoice_record=invoice,
                    settlement_record=settlement,
                    bank_record=bank,
                    notes=f"Matched within settlement window (T+{days_diff} days, limit T+{max_days}) and amount Rs {invoice.amount:,.2f}.",
                )

    return RuleMatchResult(is_matched=False)


# ---------------------------------------------------------------------------
# 5. Rule 5: Fee / GST / TDS Adjusted Amount Match (Standard Deterministic Rates)
# ---------------------------------------------------------------------------

def match_fee_gst_tds_adjusted_amount(
    invoice: Optional[NormalizedRecord] = None,
    settlement: Optional[NormalizedRecord] = None,
    bank: Optional[NormalizedRecord] = None,
    fee_config: Optional[Union[FeeConfig, str, dict]] = None,
) -> RuleMatchResult:
    """
    Rule 5: Matches invoice and settlement using configurable deterministic fee/GST/TDS formulas:
    - MDR Fee: fee_config.mdr (default 2.0%)
    - GST: fee_config.gst (default 18.0% of fee)
    - TDS: fee_config.tds (default 1.0% of invoice amount)
    
    Reconciles if settlement.amount == invoice.amount - fees - gst - tds AND the charges match
    the rate schedule. Non-standard one-off manual adjustments (e.g. Rs 30 on Rs 12,000)
    will NOT match this rule, properly deferring to Phase 4 AI verification.
    """
    if not (invoice and settlement):
        return RuleMatchResult(is_matched=False)

    # If both have order IDs, they must match
    if invoice.order_id and settlement.order_id:
        if invoice.order_id.strip() != settlement.order_id.strip():
            return RuleMatchResult(is_matched=False)

    if settlement.status != "settled" or invoice.status != "paid":
        return RuleMatchResult(is_matched=False)

    # If bank is present, it must credit the settled net amount
    if bank and (bank.status != "credited" or bank.amount != settlement.amount):
        return RuleMatchResult(is_matched=False)

    cfg = load_fee_config(fee_config) if fee_config is not None else DEFAULT_FEE_CONFIG

    # 1. Calculate rate deductions from config
    std_fee = round_paisa(invoice.amount * cfg.mdr_rate)
    std_gst = round_paisa(std_fee * cfg.gst_rate)
    std_tds = round_paisa(invoice.amount * cfg.tds_rate)

    # 2. Check if settlement amounts and recorded fees match standard formulas
    actual_fee = settlement.fees
    actual_gst = settlement.gst
    actual_tds = settlement.tds

    total_deductions = actual_fee + actual_gst + actual_tds
    if total_deductions <= Decimal("0.00"):
        return RuleMatchResult(is_matched=False)

    # Validate that every non-zero deduction matches the rate card exactly
    charges_list: List[ChargeItem] = []

    if actual_fee > Decimal("0.00"):
        if actual_fee != std_fee:
            return RuleMatchResult(is_matched=False)
        charges_list.append(ChargeItem(charge="fees", amount=actual_fee))

    if actual_gst > Decimal("0.00"):
        if actual_gst != std_gst:
            return RuleMatchResult(is_matched=False)
        charges_list.append(ChargeItem(charge="gst", amount=actual_gst))

    if actual_tds > Decimal("0.00"):
        if actual_tds != std_tds:
            return RuleMatchResult(is_matched=False)
        charges_list.append(ChargeItem(charge="tds", amount=actual_tds))

    # Verify arithmetic: invoice.amount - sum(deductions) == settlement.amount
    expected_net = round_paisa(invoice.amount - total_deductions)
    if settlement.amount != expected_net:
        return RuleMatchResult(is_matched=False)

    charge_breakdown = ChargeBreakdown(charges=charges_list)
    named_charges = " + ".join(c.charge for c in charges_list)

    return RuleMatchResult(
        is_matched=True,
        rule_name="fee_gst_tds_adjusted_amount",
        confidence=Decimal("100.00"),
        invoice_record=invoice,
        settlement_record=settlement,
        bank_record=bank,
        notes=f"Reconciled via {cfg.merchant_type} rate schedule: {named_charges}.",
        charge_breakdown=charge_breakdown,
    )


# ---------------------------------------------------------------------------
# Ordered Rule Engine Pipeline (FR-4)
# ---------------------------------------------------------------------------

RULE_FUNCTIONS = [
    ("exact_order_id", match_exact_order_id),
    ("exact_reference_number", match_exact_reference_number),
    ("exact_amount", match_exact_amount),
    ("settlement_date_window", match_settlement_date_window),
    ("fee_gst_tds_adjusted_amount", match_fee_gst_tds_adjusted_amount),
]


def apply_rules_in_order(
    invoice: Optional[NormalizedRecord] = None,
    settlement: Optional[NormalizedRecord] = None,
    bank: Optional[NormalizedRecord] = None,
    max_date_window_days: Optional[int] = None,
    duplicate_order_ids: Optional[Set[str]] = None,
    fee_config: Optional[Union[FeeConfig, str, dict]] = None,
) -> RuleMatchResult:
    """
    FR-4: Applies rules in strict priority order:
    1. Exact Order ID
    2. Exact UTR / reference_number
    3. Exact amount (no adjustment)
    4. Settlement-date window (T+2 days or config delay window)
    5. Fee / GST / TDS adjusted amount (configurable deterministic rate formulas)
    
    Returns the first matching RuleMatchResult (100% confidence) or an unmatched result.
    """
    cfg = load_fee_config(fee_config) if fee_config is not None else DEFAULT_FEE_CONFIG
    window_days = max_date_window_days if max_date_window_days is not None else cfg.settlement_delay_days

    # If invoice has a duplicate order ID conflict, do not auto-match; route to exceptions
    if invoice and duplicate_order_ids and invoice.order_id in duplicate_order_ids:
        return RuleMatchResult(
            is_matched=False,
            notes=f"Ambiguous: Duplicate invoice detected for order ID '{invoice.order_id}'. Routed to exceptions.",
        )

    # 1. Exact Order ID
    res1 = match_exact_order_id(
        invoice=invoice,
        settlement=settlement,
        bank=bank,
        max_days=window_days,
        duplicate_order_ids=duplicate_order_ids,
    )
    if res1.is_matched:
        return res1

    # 2. Exact Reference Number / UTR
    res2 = match_exact_reference_number(settlement=settlement, bank=bank, invoice=invoice)
    if res2.is_matched:
        return res2

    # 3. Exact Amount
    res3 = match_exact_amount(invoice=invoice, settlement=settlement, bank=bank, max_days=window_days)
    if res3.is_matched:
        return res3

    # 4. Settlement-Date Window
    res4 = match_settlement_date_window(
        invoice=invoice,
        settlement=settlement,
        bank=bank,
        max_days=window_days,
    )
    if res4.is_matched:
        return res4

    # 5. Fee / GST / TDS Adjusted Amount
    res5 = match_fee_gst_tds_adjusted_amount(invoice=invoice, settlement=settlement, bank=bank, fee_config=cfg)
    if res5.is_matched:
        return res5

    return RuleMatchResult(is_matched=False)
