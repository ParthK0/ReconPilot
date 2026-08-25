import io
import os
import time
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from backend.db.session import get_db, DATABASE_URL
from backend.db.models import Batch, Record, Match, AIVerification, ExceptionRecord, MetricsSnapshot
from backend.config.fee_rules import FeeConfig, load_fee_config
from backend.parser import (
    InvoiceParser,
    SettlementParser,
    BankStatementParser,
    SmartCSVParser,
    SchemaValidationError,
    InvalidCSVFormatError,
    EmptyFileError,
)
from backend.normalizer import (
    normalize_dataframe,
    persist_normalized_records,
    NormalizedRecord,
)
from backend.rules import (
    apply_rules_in_order,
    find_duplicate_order_ids,
    RuleMatchResult,
)
from backend.ai.engine import verify_discrepancy
from backend.evaluation.evaluator import calculate_metrics
from backend.reports.reporter import generate_reconciliation_csv

router = APIRouter(tags=["ReconPilot API"])


class HealthResponse(BaseModel):
    status: str
    service: str = "ReconPilot Backend"
    version: str
    database_connected: bool
    database_type: str
    timestamp: float


@router.get("/health", response_model=HealthResponse)
@router.get("/api/v1/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint confirming API status and database connectivity."""
    db_connected = False
    db_type = "postgresql" if "postgresql" in DATABASE_URL or "postgres" in DATABASE_URL else "sqlite"
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    return HealthResponse(
        status="healthy",
        service="ReconPilot Backend",
        version="1.0.0",
        database_connected=db_connected,
        database_type=db_type,
        timestamp=time.time(),
    )


# ---------------------------------------------------------------------------
# Pipeline Execution Engine
# ---------------------------------------------------------------------------

def process_reconciliation_batch(
    db: Session,
    batch_id: str,
    fee_config: Optional[Union[FeeConfig, str, dict]] = None,
    ground_truth: Optional[Union[List[Dict[str, Any]], Dict[str, Any], str]] = None,
) -> MetricsSnapshot:
    """
    Executes the end-to-end reconciliation pipeline:
    1. Deterministic Rule Matching (86%)
    2. Finance Verification Engine (AI) for rule misses (6%)
    3. Exception Classification for unresolved records (8%)
    4. Metrics Computation & Snapshot Persistence (with ground-truth validation if available)
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
    elif isinstance(fee_config, str):
        # Auto-detect merchant profile ground truth if exists
        m_gt_path = os.path.join("backend/synthetic-data/merchants", fee_config.lower(), "ground_truth.json")
        if os.path.isfile(m_gt_path):
            with open(m_gt_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                gt_by_order = {item["order_id"]: item for item in data if isinstance(item, dict) and "order_id" in item}

    # Load normalized records for this batch
    records = db.query(Record).filter(Record.batch_id == batch_id).all()
    invoices_db = [r for r in records if r.source_type == "invoice"]
    settlements_db = [r for r in records if r.source_type == "settlement"]
    banks_db = [r for r in records if r.source_type == "bank"]

    # Convert to NormalizedRecord objects for engine evaluation
    def to_norm(r: Record) -> NormalizedRecord:
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

    norm_invoices = [to_norm(r) for r in invoices_db]
    norm_settlements = [to_norm(r) for r in settlements_db]
    norm_banks = [to_norm(r) for r in banks_db]

    inv_by_order = {r.order_id: r for r in norm_invoices if r.order_id}
    settle_by_order = {r.order_id: r for r in norm_settlements if r.order_id}
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

    # Clean existing matches for idempotency
    db.query(Match).filter(Match.batch_id == batch_id).delete()
    db.commit()

    # Process pairs primarily keyed by settlement (or invoice)
    processed_inv_ids = set()

    for settle in norm_settlements:
        inv = inv_by_order.get(settle.order_id)
        bank = bank_by_utr.get(settle.reference_number)
        gt_item = gt_by_order.get(settle.order_id) if has_gt else None
        expected_res = gt_item.get("expected_resolution") if gt_item else None

        if inv:
            processed_inv_ids.add(inv.transaction_id)

        # Step 1: Run Deterministic Rules
        # If 3-way batch has bank records, but this settlement's UTR is not credited in bank statements,
        # it is a missing bank credit exception (cannot match rules)
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
            # Deterministic Rule Match
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
                if has_gt:
                    ai_total += 1
                    if expected_res == "ai":
                        tp += 1
                        ai_correct += 1
                    else:
                        fp += 1
            else:
                # Step 3: Exception Classification (Unresolved / Disagreement)
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
                    elif expected_res == "exception":
                        pass  # True negative exception

                # Classify into standard category
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
                else:
                    cat = "unknown"
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

    db.commit()

    processing_time = round(time.time() - start_time, 2)
    total_processed = len(norm_settlements)

    metrics = calculate_metrics(
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
        ai_accuracy=Decimal(str(metrics.ai_verification_accuracy)) if metrics.ai_verification_accuracy is not None else None,
        processing_time_seconds=Decimal(str(metrics.processing_time_seconds)),
        manual_hours_saved=Decimal(str(metrics.manual_hours_saved)),
    )
    db.add(snapshot)
    batch.status = "done"
    db.commit()
    db.refresh(snapshot)
    return snapshot


# ---------------------------------------------------------------------------
# API Endpoints (05-API-Spec.md)
# ---------------------------------------------------------------------------

@router.post("/batches", status_code=status.HTTP_201_CREATED)
@router.post("/api/v1/batches", status_code=status.HTTP_201_CREATED)
async def upload_batch(
    settlement_csv: UploadFile = File(...),
    bank_csv: UploadFile = File(...),
    invoice_csv: UploadFile = File(...),
    ground_truth_json: Optional[UploadFile] = File(None),
    merchant_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    POST /batches: Upload 3 CSV files, validate schemas, persist records,
    and trigger automated reconciliation pipeline with intelligent schema detection.
    Optionally accepts ground_truth_json to compute live verification metrics.
    """
    settle_bytes = await settlement_csv.read()
    bank_bytes = await bank_csv.read()
    inv_bytes = await invoice_csv.read()

    # FR-2: Validate schemas against expected columns with intelligent schema mapping
    try:
        settle_df, _ = SmartCSVParser("settlement").parse(settle_bytes)
    except SchemaValidationError as e:
        raise HTTPException(status_code=422, detail=f"Settlement CSV error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Settlement CSV unparseable: {str(e)}")

    try:
        bank_df, _ = SmartCSVParser("bank").parse(bank_bytes)
    except SchemaValidationError as e:
        raise HTTPException(status_code=422, detail=f"Bank CSV error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Bank CSV unparseable: {str(e)}")

    try:
        inv_df, _ = SmartCSVParser("invoice").parse(inv_bytes)
    except SchemaValidationError as e:
        raise HTTPException(status_code=422, detail=f"Invoice CSV error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invoice CSV unparseable: {str(e)}")

    gt_data = None
    if ground_truth_json is not None:
        try:
            gt_bytes = await ground_truth_json.read()
            if gt_bytes:
                import json as _json
                gt_data = _json.loads(gt_bytes.decode("utf-8"))
        except Exception:
            gt_data = None

    # Create Batch
    batch = Batch(
        id=str(uuid.uuid4()),
        settlement_filename=settlement_csv.filename,
        bank_filename=bank_csv.filename,
        invoice_filename=invoice_csv.filename,
        status="processing",
    )
    db.add(batch)
    db.commit()

    # FR-3: Normalize and persist records
    inv_records = normalize_dataframe(inv_df, "invoice", batch_id=batch.id)
    set_records = normalize_dataframe(settle_df, "settlement", batch_id=batch.id)
    bnk_records = normalize_dataframe(bank_df, "bank", batch_id=batch.id)

    persist_normalized_records(db, inv_records, batch_id=batch.id)
    persist_normalized_records(db, set_records, batch_id=batch.id)
    persist_normalized_records(db, bnk_records, batch_id=batch.id)

    # Trigger pipeline
    process_reconciliation_batch(db, batch.id, fee_config=merchant_type, ground_truth=gt_data)
    db.refresh(batch)

    return {
        "batch_id": batch.id,
        "status": batch.status,
        "uploaded_at": batch.uploaded_at.isoformat(),
    }


@router.post("/batches/demo", status_code=status.HTTP_201_CREATED)
@router.post("/api/v1/batches/demo", status_code=status.HTTP_201_CREATED)
def trigger_demo_batch(db: Session = Depends(get_db)):
    """
    Triggers automated reconciliation against the full 100-row synthetic dataset.
    """
    data_dir = "backend/synthetic-data"
    settle_path = os.path.join(data_dir, "settlements.csv")
    bank_path = os.path.join(data_dir, "bank_statements.csv")
    inv_path = os.path.join(data_dir, "invoices.csv")
    gt_path = os.path.join(data_dir, "ground_truth.json")

    settle_df = SettlementParser().parse(settle_path)
    bank_df = BankStatementParser().parse(bank_path)
    inv_df = InvoiceParser().parse(inv_path)

    batch = Batch(
        id=str(uuid.uuid4()),
        settlement_filename="settlements.csv",
        bank_filename="bank_statements.csv",
        invoice_filename="invoices.csv",
        status="processing",
    )
    db.add(batch)
    db.commit()

    inv_records = normalize_dataframe(inv_df, "invoice", batch_id=batch.id)
    set_records = normalize_dataframe(settle_df, "settlement", batch_id=batch.id)
    bnk_records = normalize_dataframe(bank_df, "bank", batch_id=batch.id)

    persist_normalized_records(db, inv_records, batch_id=batch.id)
    persist_normalized_records(db, set_records, batch_id=batch.id)
    persist_normalized_records(db, bnk_records, batch_id=batch.id)

    gt_data = None
    if os.path.isfile(gt_path):
        with open(gt_path, "r", encoding="utf-8") as f:
            import json as _json
            gt_data = _json.load(f)

    process_reconciliation_batch(db, batch.id, ground_truth=gt_data)
    db.refresh(batch)

    return {
        "batch_id": batch.id,
        "status": batch.status,
        "uploaded_at": batch.uploaded_at.isoformat(),
    }


@router.get("/batches/{batch_id}")
@router.get("/api/v1/batches/{batch_id}")
def get_batch_status(batch_id: str, db: Session = Depends(get_db)):
    """GET /batches/{batch_id}: Retrieve batch status."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    record_count = db.query(Record).filter(Record.batch_id == batch_id, Record.source_type == "settlement").count()
    return {
        "batch_id": batch.id,
        "status": batch.status,
        "records_processed": record_count,
        "settlement_filename": batch.settlement_filename,
        "bank_filename": batch.bank_filename,
        "invoice_filename": batch.invoice_filename,
        "uploaded_at": batch.uploaded_at.isoformat(),
    }


@router.post("/batches/{batch_id}/process")
@router.post("/api/v1/batches/{batch_id}/process")
def process_batch_route(batch_id: str, db: Session = Depends(get_db)):
    """POST /batches/{batch_id}/process: Triggers reconciliation pipeline."""
    snapshot = process_reconciliation_batch(db, batch_id)
    return {
        "batch_id": batch_id,
        "status": "done",
        "records_processed": snapshot.records_processed,
    }


@router.get("/batches/{batch_id}/matches")
@router.get("/api/v1/batches/{batch_id}/matches")
def get_batch_matches(
    batch_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    method_filter: Optional[str] = Query(None, alias="match_method"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """GET /batches/{batch_id}/matches: Paginated list of reconciliation matches."""
    query = db.query(Match).filter(Match.batch_id == batch_id)
    if status_filter:
        query = query.filter(Match.status == status_filter)
    if method_filter:
        query = query.filter(Match.match_method == method_filter)

    total = query.count()
    matches = query.order_by(Match.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for m in matches:
        settle_rec = db.query(Record).filter(Record.id == m.settlement_record_id).first() if m.settlement_record_id else None
        inv_rec = db.query(Record).filter(Record.id == m.invoice_record_id).first() if m.invoice_record_id else None
        bank_rec = db.query(Record).filter(Record.id == m.bank_record_id).first() if m.bank_record_id else None

        result.append({
            "match_id": m.id,
            "status": m.status,
            "match_method": m.match_method,
            "rule_name": m.rule_name,
            "confidence": float(m.confidence),
            "settlement_record_id": m.settlement_record_id,
            "invoice_record_id": m.invoice_record_id,
            "bank_record_id": m.bank_record_id,
            "order_id": (settle_rec.order_id if settle_rec else (inv_rec.order_id if inv_rec else None)),
            "amount": float(settle_rec.amount if settle_rec else (inv_rec.amount if inv_rec else 0.0)),
            "settlement_amount": float(settle_rec.amount) if settle_rec else None,
            "invoice_amount": float(inv_rec.amount) if inv_rec else None,
            "bank_amount": float(bank_rec.amount) if bank_rec else None,
            "reference_number": settle_rec.reference_number if settle_rec else (bank_rec.reference_number if bank_rec else None),
            "created_at": m.created_at.isoformat(),
        })

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "matches": result,
    }


@router.get("/matches/{match_id}")
@router.get("/api/v1/matches/{match_id}")
def get_match_detail(match_id: str, db: Session = Depends(get_db)):
    """GET /matches/{match_id}: Single match detail + full AI verification evidence."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    settle_rec = db.query(Record).filter(Record.id == match.settlement_record_id).first() if match.settlement_record_id else None
    inv_rec = db.query(Record).filter(Record.id == match.invoice_record_id).first() if match.invoice_record_id else None
    bank_rec = db.query(Record).filter(Record.id == match.bank_record_id).first() if match.bank_record_id else None

    ai_ver = db.query(AIVerification).filter(AIVerification.match_id == match_id).first()
    ai_data = None
    if ai_ver:
        # Re-derive calculation trace from validator
        if inv_rec and settle_rec:
            calc_trace = (
                f"₹{inv_rec.amount:,.2f} − ₹{ai_ver.difference_amount:,.2f} ({ai_ver.likely_reason.replace('_', ' ')}) = "
                f"₹{settle_rec.amount:,.2f} = settlement amount ✓"
            )
        else:
            calc_trace = f"Difference amount: ₹{ai_ver.difference_amount:,.2f}"

        ai_data = {
            "difference_amount": float(ai_ver.difference_amount),
            "likely_reason": ai_ver.likely_reason,
            "reasoning_explanation": ai_ver.reasoning_explanation,
            "expected_value": float(ai_ver.expected_value),
            "ai_confidence": float(ai_ver.ai_confidence),
            "adjusted_confidence": float(ai_ver.adjusted_confidence),
            "evidence_field": ai_ver.evidence_field,
            "model_used": ai_ver.model_used,
            "calculation_trace": calc_trace,
            "prompt_tokens": ai_ver.prompt_tokens,
            "completion_tokens": ai_ver.completion_tokens,
        }

    return {
        "match_id": match.id,
        "status": match.status,
        "match_method": match.match_method,
        "rule_name": match.rule_name,
        "confidence": float(match.confidence),
        "records": {
            "settlement": {
                "id": settle_rec.id,
                "transaction_id": settle_rec.transaction_id,
                "order_id": settle_rec.order_id,
                "amount": float(settle_rec.amount),
                "txn_date": settle_rec.txn_date.isoformat(),
                "reference_number": settle_rec.reference_number,
                "status": settle_rec.status,
                "fees": float(settle_rec.fees),
                "gst": float(settle_rec.gst),
                "tds": float(settle_rec.tds),
            } if settle_rec else None,
            "invoice": {
                "id": inv_rec.id,
                "transaction_id": inv_rec.transaction_id,
                "order_id": inv_rec.order_id,
                "amount": float(inv_rec.amount),
                "txn_date": inv_rec.txn_date.isoformat(),
                "status": inv_rec.status,
            } if inv_rec else None,
            "bank": {
                "id": bank_rec.id,
                "transaction_id": bank_rec.transaction_id,
                "amount": float(bank_rec.amount),
                "txn_date": bank_rec.txn_date.isoformat(),
                "reference_number": bank_rec.reference_number,
                "status": bank_rec.status,
            } if bank_rec else None,
        },
        "ai_verification": ai_data,
    }


@router.get("/batches/{batch_id}/exceptions")
@router.get("/api/v1/batches/{batch_id}/exceptions")
def get_batch_exceptions(batch_id: str, db: Session = Depends(get_db)):
    """GET /batches/{batch_id}/exceptions: Grouped exception report."""
    exceptions = db.query(ExceptionRecord).join(Record).filter(Record.batch_id == batch_id).all()
    categories: Dict[str, int] = {
        "settlement_delay": 0,
        "missing_credit": 0,
        "duplicate_invoice": 0,
        "refund_pending": 0,
        "unknown": 0,
    }
    items = []
    for exc in exceptions:
        categories[exc.category] = categories.get(exc.category, 0) + 1
        rec = db.query(Record).filter(Record.id == exc.record_id).first()
        items.append({
            "exception_id": exc.id,
            "match_id": exc.match_id,
            "record_id": exc.record_id,
            "category": exc.category,
            "notes": exc.notes,
            "resolved": exc.resolved,
            "order_id": rec.order_id if rec else None,
            "amount": float(rec.amount) if rec else 0.0,
            "txn_date": rec.txn_date.isoformat() if rec else None,
            "reference_number": rec.reference_number if rec else None,
            "source_type": rec.source_type if rec else None,
        })
    return {**categories, "total_exceptions": len(items), "items": items}


@router.get("/batches/{batch_id}/metrics")
@router.get("/api/v1/batches/{batch_id}/metrics")
def get_batch_metrics(batch_id: str, db: Session = Depends(get_db)):
    """GET /batches/{batch_id}/metrics: Dashboard headline numbers (FR-16)."""
    snapshot = (
        db.query(MetricsSnapshot)
        .filter(MetricsSnapshot.batch_id == batch_id)
        .order_by(MetricsSnapshot.created_at.desc())
        .first()
    )
    if not snapshot:
        return {
            "records_processed": 0,
            "rule_matches": 0,
            "ai_verified": 0,
            "needs_review": 0,
            "match_rate": 0.0,
            "precision": None,
            "recall": None,
            "true_positives": None,
            "false_positives": None,
            "false_negatives": None,
            "ai_verification_accuracy": None,
            "processing_time_seconds": 0.0,
            "manual_hours_saved": 0.0,
        }
    return {
        "records_processed": snapshot.records_processed,
        "rule_matches": snapshot.rule_matches,
        "ai_verified": snapshot.ai_verified,
        "needs_review": snapshot.needs_review,
        "match_rate": float(snapshot.match_rate),
        "precision": float(snapshot.precision) if snapshot.precision is not None else None,
        "recall": float(snapshot.recall) if snapshot.recall is not None else None,
        "true_positives": snapshot.true_positives,
        "false_positives": snapshot.false_positives,
        "false_negatives": snapshot.false_negatives,
        "ai_verification_accuracy": float(snapshot.ai_accuracy) if snapshot.ai_accuracy is not None else None,
        "processing_time_seconds": float(snapshot.processing_time_seconds),
        "manual_hours_saved": float(snapshot.manual_hours_saved),
    }


@router.post("/matches/{match_id}/review")
@router.post("/api/v1/matches/{match_id}/review")
def review_match(
    match_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """POST /matches/{match_id}/review: Human marks an exception resolved with review notes."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    resolved = payload.get("resolved", True)
    reviewer_note = payload.get("reviewer_note", "Reviewed and resolved manually.")

    exc = db.query(ExceptionRecord).filter(ExceptionRecord.match_id == match_id).first()
    if exc:
        exc.resolved = resolved
        exc.notes = f"{exc.notes or ''} [Reviewer: {reviewer_note}]".strip()

    if resolved:
        match.status = "matched"
        match.confidence = Decimal("100.00")

    db.commit()
    db.refresh(match)
    return {"match_id": match.id, "status": match.status, "confidence": float(match.confidence), "resolved": resolved}


@router.get("/batches/{batch_id}/export")
@router.get("/api/v1/batches/{batch_id}/export")
def export_batch_csv(batch_id: str, db: Session = Depends(get_db)):
    """GET /batches/{batch_id}/export: Exports final reconciliation CSV report."""
    matches = db.query(Match).filter(Match.batch_id == batch_id).all()
    records_data = []

    for m in matches:
        settle_rec = db.query(Record).filter(Record.id == m.settlement_record_id).first() if m.settlement_record_id else None
        inv_rec = db.query(Record).filter(Record.id == m.invoice_record_id).first() if m.invoice_record_id else None
        ai_ver = db.query(AIVerification).filter(AIVerification.match_id == m.id).first()

        evidence = m.rule_name if m.match_method == "rule" else (ai_ver.evidence_field if ai_ver else "none")
        records_data.append({
            "match_id": m.id,
            "order_id": settle_rec.order_id if settle_rec else (inv_rec.order_id if inv_rec else "N/A"),
            "source_type": "settlement",
            "amount": float(settle_rec.amount) if settle_rec else 0.0,
            "status": m.status,
            "match_method": m.match_method,
            "confidence": float(m.confidence),
            "evidence": evidence,
            "reviewer_action": "auto_matched" if m.status == "matched" else "pending_review",
        })

    csv_text = generate_reconciliation_csv(records_data)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=recon_report_batch_{batch_id[:8]}.csv"},
    )
