"""
backend/analytics/cash_position.py
==================================
ReconPilot 2.0: Cash Position & Working Capital Analytics Engine.

Computes a real-time treasury position snapshot directly from reconciled batch state:
- Current Book Balance (Confirmed bank receipts credited to merchant account)
- Pending Gateway Settlements (Gross captured volume pending T+2 deposit)
- Pending Refunds & Chargeback Reserves (Reserved cash buffer for active disputes)
- Expected Cash Tomorrow (Projected net inflows based on known fee schedules)
- Liquidity Health Index (Confirmed vs Pending inflow confidence ratio)
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.models import Batch, Record, Match, ExceptionRecord
from backend.config.fee_rules import FeeConfig, load_fee_config


ONE_PAISA = Decimal("0.01")


def _paisa(val: Decimal) -> Decimal:
    return val.quantize(ONE_PAISA, rounding=ROUND_HALF_UP)


class CashPositionSnapshot(BaseModel):
    batch_id: str
    merchant_type: str
    currency: str = "INR"
    
    # Core Balances
    current_bank_balance: Decimal
    gross_volume_processed: Decimal
    settled_volume_credited: Decimal
    pending_settlement_inflows: Decimal
    pending_refund_reserves: Decimal
    
    # Projections
    expected_cash_tomorrow: Decimal
    expected_mdr_tax_deductions: Decimal
    
    # Health & Metrics
    reconciled_cash_ratio: float       # Percentage of volume fully reconciled
    liquidity_health_index: float      # Health score 0-100
    disputed_volume_at_risk: Decimal
    summary_narrative: str


def compute_cash_position(
    db: Session,
    batch_id: str,
    fee_config: Optional[Any] = None,
    opening_bank_balance: Decimal = Decimal("500000.00"),
) -> CashPositionSnapshot:
    """
    Derives real-time cash position and next-day working capital projections.
    """
    records = db.query(Record).filter(Record.batch_id == batch_id).all()
    matches = db.query(Match).filter(Match.batch_id == batch_id).all()
    exceptions = db.query(ExceptionRecord).join(Record).filter(Record.batch_id == batch_id).all()
    
    cfg = load_fee_config(fee_config)

    invoices = [r for r in records if r.source_type == "invoice"]
    settlements = [r for r in records if r.source_type == "settlement"]
    banks = [r for r in records if r.source_type == "bank"]

    gross_invoice_vol = sum((r.amount for r in invoices), Decimal("0.00"))
    settled_credited_vol = sum((r.amount for r in banks if r.amount > Decimal("0.00")), Decimal("0.00"))
    
    # Calculate pending settlements (settlements with status 'pending' or in exception category 'settlement_delay')
    pending_settle_vol = Decimal("0.00")
    for s in settlements:
        if s.status == "pending":
            pending_settle_vol += s.amount
            
    for exc in exceptions:
        if exc.category in ("settlement_delay", "settlement_holiday", "weekend_settlement") and not exc.resolved:
            rec = next((r for r in records if r.id == exc.record_id), None)
            if rec and rec.amount > Decimal("0.00"):
                pending_settle_vol += rec.amount

    # Calculate pending refunds & chargebacks
    pending_refund_vol = Decimal("0.00")
    for b in banks:
        if b.amount < Decimal("0.00"):
            pending_refund_vol += abs(b.amount)
            
    for exc in exceptions:
        if exc.category in ("refund_pending", "chargeback", "refund_reversal") and not exc.resolved:
            rec = next((r for r in records if r.id == exc.record_id), None)
            if rec:
                pending_refund_vol += abs(rec.amount)

    # Disputed volume
    disputed_vol = Decimal("0.00")
    for exc in exceptions:
        if exc.category in ("chargeback", "fraud_hold", "escrow_hold") and not exc.resolved:
            rec = next((r for r in records if r.id == exc.record_id), None)
            if rec:
                disputed_vol += abs(rec.amount)

    # Estimated MDR and Tax on pending settlements
    est_mdr = _paisa(pending_settle_vol * cfg.mdr_rate)
    est_gst = _paisa(est_mdr * cfg.gst_rate)
    est_tds = _paisa(pending_settle_vol * cfg.tds_rate)
    total_est_deductions = est_mdr + est_gst + est_tds
    
    # Expected net cash tomorrow
    expected_cash_tomorrow = _paisa(pending_settle_vol - total_est_deductions - pending_refund_vol)
    current_balance = _paisa(opening_bank_balance + settled_credited_vol - pending_refund_vol)

    total_matched = sum(1 for m in matches if m.status == "matched")
    total_records = len(settlements) or 1
    reconciled_ratio = round((total_matched / total_records) * 100.0, 2)
    
    # Liquidity index: higher when settled is high and disputed is low
    liq_index = min(100.0, max(0.0, float(reconciled_ratio * 0.8 + 20.0 - float(disputed_vol / (gross_invoice_vol or Decimal("1.00")) * Decimal("50.00")))))

    narrative = (
        f"Treasury position healthy. ₹{current_balance:,.2f} confirmed book cash, "
        f"₹{pending_settle_vol:,.2f} in pipeline pending T+{cfg.settlement_delay_days} clearance, "
        f"and ₹{expected_cash_tomorrow:,.2f} projected net liquidity tomorrow."
    )

    return CashPositionSnapshot(
        batch_id=batch_id,
        merchant_type=cfg.merchant_type,
        currency="INR",
        current_bank_balance=current_balance,
        gross_volume_processed=_paisa(gross_invoice_vol),
        settled_volume_credited=_paisa(settled_credited_vol),
        pending_settlement_inflows=_paisa(pending_settle_vol),
        pending_refund_reserves=_paisa(pending_refund_vol),
        expected_cash_tomorrow=expected_cash_tomorrow,
        expected_mdr_tax_deductions=total_est_deductions,
        reconciled_cash_ratio=reconciled_ratio,
        liquidity_health_index=round(liq_index, 1),
        disputed_volume_at_risk=_paisa(disputed_vol),
        summary_narrative=narrative,
    )
