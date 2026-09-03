"""
backend/services/pipeline.py
============================
Core Reconciliation Pipeline Orchestrator.

Processes a batch through:
1. Deterministic Rule Matching (Sub-millisecond priority chain)
2. Finance Verification Engine (AI) on residual rule misses
3. Multi-Category Exception Classification
4. Comprehensive Gap Detection (Unmatched Invoices & Bank Credits)
5. Honest Metrics Computation & Snapshot Persistence
"""

import json
import os
import time
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, List, Union, Set
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.db.models import Batch, Record, Match, AIVerification, ExceptionRecord, MetricsSnapshot
from backend.config.fee_rules import FeeConfig, load_fee_config
from backend.normalizer import NormalizedRecord
from backend.rules import (
    apply_rules_in_order,
    find_duplicate_order_ids,
    RuleMatchResult,
)
from backend.ai.engine import verify_discrepancy, verify_discrepancies_clustered
from backend.services.metrics import compute_batch_metrics
from backend.logging_config import get_logger

logger = get_logger("pipeline")


def _to_normalized_record(r: Record) -> NormalizedRecord:
    """Converts a database Record entity into a typed NormalizedRecord."""
    return NormalizedRecord(
        id=r.id,
        batch_id=r.batch_id,
        source_type=r.source_type,
        transaction_id=r.transaction_id,
        order_id=r.order_id,
        amount=r.amount,
        txn_date=r.txn_date,
        reference_number=r.reference_number,
        status=r.status,
        fees=r.fees,
        gst=r.gst,
        tds=r.tds,
        raw_payload=r.raw_payload or {},
    )


def process_reconciliation_batch(
    db: Session,
    batch_id: str,
    fee_config: Optional[Union[FeeConfig, str, dict]] = None,
    ground_truth: Optional[Union[List[Dict[str, Any]], Dict[str, Any], str]] = None,
    merchant_type: str = "retail",
) -> MetricsSnapshot:
    """
    Executes the end-to-end reconciliation pipeline:
    1. Deterministic Rule Matching
    2. Finance Verification Engine (AI) with Feedback Memory retrieval
    3. Granular Exception Classification for unresolved records
    4. 3-Way Gap Detection (Invoices without settlements, Bank credits without settlements)
    5. Metrics Computation & Snapshot Persistence
    """
    start_time = time.time()
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    batch.status = "processing"
    db.commit()

    # Ground truth mapping: keyed by order_id
    gt_by_order: Optional[Dict[str, Any]] = None
    if ground_truth is not None:
        if isinstance(ground_truth, list):
            gt_by_order = {item["order_id"]: item for item in ground_truth if isinstance(item, dict) and "order_id" in item}
        elif isinstance(ground_truth, dict):
            if all(isinstance(v, dict) for v in ground_truth.values()):
                gt_by_order = ground_truth
            elif "order_id" in ground_truth:
                gt_by_order = {ground_truth["order_id"]: ground_truth}
        elif isinstance(ground_truth, str) and os.path.isfile(ground_truth):
            with open(ground_truth, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    gt_by_order = {item["order_id"]: item for item in data if isinstance(item, dict) and "order_id" in item}

    # Load all normalized records for this batch in a single query
    records = db.query(Record).filter(Record.batch_id == batch_id).all()
    logger.info("Starting reconciliation pipeline for batch '%s' with %d records.", batch_id, len(records))
    invoices_db = [r for r in records if r.source_type == "invoice"]
    settlements_db = [r for r in records if r.source_type == "settlement"]
    banks_db = [r for r in records if r.source_type == "bank"]

    norm_invoices = [_to_normalized_record(r) for r in invoices_db]
    norm_settlements = [_to_normalized_record(r) for r in settlements_db]
    norm_banks = [_to_normalized_record(r) for r in banks_db]

    inv_by_order = {r.order_id: r for r in norm_invoices if r.order_id}
    bank_by_utr = {r.reference_number: r for r in norm_banks if r.reference_number}

    duplicates = find_duplicate_order_ids(norm_invoices)

    rule_matches_count = 0
    ai_verified_count = 0
    exceptions_count = 0

    has_gt = gt_by_order is not None
    tp = 0 if has_gt else None
    fp = 0 if has_gt else None
    fn = 0 if has_gt else None
    ai_correct = 0 if has_gt else None
    ai_total = 0 if has_gt else None

    # Track matched records for 3-way gap detection
    matched_invoice_ids: Set[str] = set()
    matched_bank_ids: Set[str] = set()

    # Clean existing matches for idempotency
    db.query(Match).filter(Match.batch_id == batch_id).delete()
    db.commit()

    # Primary Settlement-Centric Matching Loop
    for settle in norm_settlements:
        inv = inv_by_order.get(settle.order_id)
        bank = bank_by_utr.get(settle.reference_number)
        gt_item = gt_by_order.get(settle.order_id) if has_gt else None
        expected_res = gt_item.get("expected_resolution") if gt_item else None

        # Step 1: Run Deterministic Rules
        if len(norm_banks) > 0 and bank is None:
            rule_res = RuleMatchResult(is_matched=False, notes="Bank credit missing in bank statement.")
        else:
            rule_res: RuleMatchResult = apply_rules_in_order(
                invoice=inv,
                settlement=settle,
                bank=bank,
                duplicate_order_ids=duplicates,
                fee_config=fee_config,
            )

        match_id = str(uuid.uuid4())

        if rule_res.is_matched:
            # Deterministic Rule Match (100% confidence)
            match_row = Match(
                id=match_id,
                batch_id=batch_id,
                settlement_record_id=settle.id,
                invoice_record_id=inv.id if inv else None,
                bank_record_id=bank.id if bank else None,
                match_method="rule",
                rule_name=rule_res.rule_name,
                confidence=rule_res.confidence,
                status="matched",
            )
            db.add(match_row)
            rule_matches_count += 1
            if inv:
                matched_invoice_ids.add(inv.id)
            if bank:
                matched_bank_ids.add(bank.id)

            if has_gt:
                if expected_res in ("rule", "exact", "fee_deduction", "gst_deduction", "tds_deduction"):
                    tp += 1
                else:
                    fp += 1
        else:
            # Step 2: Pass miss to Finance Verification Engine (AI)
            ai_res = verify_discrepancy(
                invoice=inv,
                settlement=settle,
                bank=bank,
                db=db,
                match_id=match_id,
                merchant_type=merchant_type,
            )

            if ai_res.is_validated and ai_res.adjusted_confidence >= Decimal("80.00"):
                # AI-Verified Match
                match_row = Match(
                    id=match_id,
                    batch_id=batch_id,
                    settlement_record_id=settle.id,
                    invoice_record_id=inv.id if inv else None,
                    bank_record_id=bank.id if bank else None,
                    match_method="ai",
                    rule_name=None,
                    confidence=ai_res.adjusted_confidence,
                    status="matched",
                )
                db.add(match_row)
                ai_verified_count += 1
                if inv:
                    matched_invoice_ids.add(inv.id)
                if bank:
                    matched_bank_ids.add(bank.id)

                if has_gt:
                    ai_total += 1
                    if expected_res == "ai":
                        tp += 1
                        ai_correct += 1
                    else:
                        fp += 1
            else:
                # Step 3: Exception Classification
                match_row = Match(
                    id=match_id,
                    batch_id=batch_id,
                    settlement_record_id=settle.id,
                    invoice_record_id=inv.id if inv else None,
                    bank_record_id=bank.id if bank else None,
                    match_method="ai",
                    rule_name=None,
                    confidence=ai_res.adjusted_confidence,
                    status="exception",
                )
                db.add(match_row)
                exceptions_count += 1

                if has_gt:
                    if expected_res == "ai":
                        ai_total += 1
                        fn += 1
                    elif expected_res in ("rule", "exact", "fee_deduction", "gst_deduction", "tds_deduction"):
                        fn += 1

                # Classify into granular exception categories
                if settle.status == "pending" or (inv and inv.status == "pending_settlement"):
                    cat = "settlement_delay"
                    notes = "Settlement delay beyond standard settlement window."
                elif (inv and inv.status == "refunded") or (bank and bank.amount < Decimal("0.00")):
                    cat = "refund_pending"
                    notes = "Negative bank transaction / refund deduction."
                elif inv and inv.order_id in duplicates:
                    cat = "duplicate_invoice"
                    notes = f"Duplicate invoice detected with shared order ID '{inv.order_id}'."
                elif (len(norm_banks) > 0 and bank is None) or (inv and inv.amount == settle.amount and bank and bank.amount != settle.amount):
                    cat = "missing_credit"
                    notes = "Settlement payout not credited in bank statement."
                elif "chargeback" in (ai_res.likely_reason or ""):
                    cat = "chargeback"
                    notes = "Cardholder chargeback dispute debit."
                elif "escrow" in (ai_res.likely_reason or ""):
                    cat = "escrow_hold"
                    notes = "Marketplace escrow hold pending fulfillment."
                elif "fraud" in (ai_res.likely_reason or ""):
                    cat = "fraud_hold"
                    notes = "Automated risk engine fraud hold."
                elif "tds" in (ai_res.likely_reason or ""):
                    cat = "tds_revision"
                    notes = "TDS rate variation or Section 194 threshold adjustment."
                elif "holiday" in (ai_res.likely_reason or ""):
                    cat = "settlement_holiday"
                    notes = "Banking holiday settlement rollover."
                elif ai_res.cost_ceiling_breached:
                    cat = "cost_ceiling_exceeded"
                    notes = "AI budget spend ceiling exceeded; routed to controller review."
                else:
                    cat = "unknown_discrepancy"
                    notes = ai_res.notes or "Discrepancy cannot be resolved by rules or verified by AI."

                exc_row = ExceptionRecord(
                    id=str(uuid.uuid4()),
                    match_id=match_id,
                    record_id=settle.id,
                    category=cat,
                    notes=notes,
                    resolved=False,
                )
                db.add(exc_row)

    # Step 4: 3-Way Gap Detection Pass
    # 4a. Invoices without corresponding settlements (Uncollected/Missing Settlements)
    for inv in norm_invoices:
        if inv.status == "paid" and inv.id not in matched_invoice_ids:
            # Check if this invoice was not evaluated in settlements
            if inv.order_id not in {s.order_id for s in norm_settlements if s.order_id}:
                gap_match_id = str(uuid.uuid4())
                gap_match = Match(
                    id=gap_match_id,
                    batch_id=batch_id,
                    settlement_record_id=None,
                    invoice_record_id=inv.id,
                    bank_record_id=None,
                    match_method="rule",
                    rule_name="gap_uncollected_invoice",
                    confidence=Decimal("100.00"),
                    status="exception",
                )
                db.add(gap_match)
                exceptions_count += 1
                exc_row = ExceptionRecord(
                    id=str(uuid.uuid4()),
                    match_id=gap_match_id,
                    record_id=inv.id,
                    category="missing_settlement",
                    notes=f"Paid ERP invoice '{inv.order_id}' has no corresponding settlement from payment gateway.",
                    resolved=False,
                )
                db.add(exc_row)

    # 4b. Bank entries without corresponding settlements (Unmatched Bank Credits)
    for bnk in norm_banks:
        if bnk.status == "credited" and bnk.id not in matched_bank_ids:
            if bnk.reference_number not in {s.reference_number for s in norm_settlements if s.reference_number}:
                gap_match_id = str(uuid.uuid4())
                gap_match = Match(
                    id=gap_match_id,
                    batch_id=batch_id,
                    settlement_record_id=None,
                    invoice_record_id=None,
                    bank_record_id=bnk.id,
                    match_method="rule",
                    rule_name="gap_unmatched_bank_credit",
                    confidence=Decimal("100.00"),
                    status="exception",
                )
                db.add(gap_match)
                exceptions_count += 1
                exc_row = ExceptionRecord(
                    id=str(uuid.uuid4()),
                    match_id=gap_match_id,
                    record_id=bnk.id,
                    category="unmatched_bank_credit",
                    notes=f"Bank credit of Rs {bnk.amount:,.2f} with UTR '{bnk.reference_number}' has no linked settlement record.",
                    resolved=False,
                )
                db.add(exc_row)

    db.commit()

    processing_time = round(time.time() - start_time, 2)
    total_processed = len(norm_settlements)

    metrics = compute_batch_metrics(
        total_records=total_processed,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        rule_matches=rule_matches_count,
        ai_verified=ai_verified_count,
        exceptions=exceptions_count,
        ai_correct=ai_correct,
        ai_total=ai_total,
        processing_time_seconds=processing_time,
    )

    snapshot = MetricsSnapshot(
        id=str(uuid.uuid4()),
        batch_id=batch_id,
        records_processed=metrics.total_records,
        rule_matches=metrics.rule_matches_count,
        ai_verified=metrics.ai_verified_count,
        needs_review=metrics.exceptions_count,
        match_rate=Decimal(str(metrics.match_rate)),
        precision=Decimal(str(metrics.precision)) if metrics.precision is not None else None,
        recall=Decimal(str(metrics.recall)) if metrics.recall is not None else None,
        true_positives=metrics.true_positives,
        false_positives=metrics.false_positives,
        false_negatives=metrics.false_negatives,
        ai_accuracy=Decimal(str(metrics.ai_accuracy)) if metrics.ai_accuracy is not None else None,
        processing_time_seconds=Decimal(str(metrics.processing_time_seconds)),
        manual_hours_saved=Decimal(str(metrics.manual_hours_saved)),
    )
    db.add(snapshot)
    batch.status = "done"
    db.commit()
    db.refresh(snapshot)
    logger.info(
        "Batch '%s' reconciliation complete in %.2fs: %d rule matches, %d AI verified, %d exceptions (match rate: %.2f%%).",
        batch_id,
        processing_time,
        metrics.rule_matches_count,
        metrics.ai_verified_count,
        metrics.exceptions_count,
        float(metrics.match_rate),
    )
    return snapshot
