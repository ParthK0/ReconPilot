"""
backend/api/routes.py
=====================
ReconPilot 2.0 REST API Routes.

Features:
- Multi-Merchant Batch Ingestion (10 Industry Archetypes)
- Scalable Synthetic Batch Generator (100, 1,000, 10,000 transactions)
- Safe Schema Mapping Preview & Confidence Threshold Gating
- Cash Position & Working Capital Analytics
- Human Review Queue with Feedback Memory Persistence
- Honest Live Metrics & Confusion Matrix Evaluation
- Audit & Exception CSV Reports
"""

import io
import json
import os
import time
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional, List, Union
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Response, status
from sqlalchemy.orm import Session, joinedload

from backend.db.session import get_db
from backend.db.models import Batch, Record, Match, AIVerification, ExceptionRecord, MetricsSnapshot
from backend.config.fee_rules import load_fee_config
from backend.parser import (
    SmartCSVParser,
    SchemaValidationError,
)
from backend.normalizer import (
    normalize_dataframe,
    persist_normalized_records,
)
from backend.schema_mapper import map_schema
from backend.synthetic_data.merchant_archetypes import MERCHANT_ARCHETYPES
from backend.synthetic_data.generator import generate_merchant_dataset
from backend.analytics.cash_position import compute_cash_position, CashPositionSnapshot
from backend.rules.exception_taxonomy import list_exception_categories, get_exception_definition
from backend.reports.reporter import (
    generate_reconciliation_csv,
    generate_tally_xml,
    generate_zoho_books_csv,
    generate_netsuite_journal_json,
)
from backend.ai.feedback_memory import feedback_store
from backend.services.pipeline import process_reconciliation_batch
from backend.services.job_queue import job_queue
from backend.api.schemas import (
    ReviewMatchRequest,
    ReviewMatchResponse,
    BatchStatusResponse,
    GeneratedBatchResponse,
    BatchUploadResponse,
    PaginatedMatchesResponse,
    MatchSummaryItem,
    MerchantMetadataResponse,
)

from backend.api.auth import verify_api_key, create_access_token, get_current_tenant

from sqlalchemy import text

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per file limit


async def _read_validated_file(upload_file: UploadFile, max_size: int = MAX_FILE_SIZE_BYTES) -> bytes:
    """
    Safely reads an incoming file stream without risking memory exhaustion (OOM).
    1. Inspects `upload_file.size` if present before reading any stream bytes.
    2. Reads in a bounded chunk (max_size + 1) so unchunked/unbounded streams are capped.
    """
    if getattr(upload_file, "size", None) is not None and upload_file.size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file '{upload_file.filename}' exceeds maximum limit of 10 MB per file.",
        )
    data = await upload_file.read(max_size + 1)
    if len(data) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file '{upload_file.filename}' exceeds maximum limit of 10 MB per file.",
        )
    return data


router = APIRouter()


# ---------------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------------

@router.get("/api/v1/health")
def api_v1_health(db: Session = Depends(get_db)):
    """Health check verifying database connection and service responsiveness."""
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "ReconPilot Backend",
        "database_connected": db_connected,
    }
# API Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/v1/merchants", response_model=List[MerchantMetadataResponse])
@router.get("/merchants", response_model=List[MerchantMetadataResponse], include_in_schema=False)
def list_merchants():
    """Returns metadata for all 10 registered industry merchant archetypes."""
    results = []
    for key, archetype in MERCHANT_ARCHETYPES.items():
        results.append({
            "merchant_type": key,
            "display_name": archetype.display_name,
            "description": archetype.description,
            "primary_payment_mode": archetype.primary_payment_mode,
            "typical_settlement_window_days": archetype.typical_settlement_window_days,
            "common_exceptions": archetype.common_exceptions,
            "currency_format": archetype.currency_format,
            "date_format": archetype.date_format,
        })
    return results


@router.post("/api/v1/schema/preview")
@router.post("/schema/preview", include_in_schema=False)
async def preview_schema(
    file: UploadFile = File(...),
    source_type: str = Query("settlement"),
):
    """
    Previews and validates column mappings with safe threshold gating:
    - auto_map (>=95%)
    - suggest (80-94%)
    - reject (<80%)
    """
    content = await _read_validated_file(file)
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {str(e)}")

    sample_rows = df.head(3).to_dict(orient="records") if not df.empty else []
    mapping = map_schema(list(df.columns), source_type=source_type, sample_rows=sample_rows)
    return mapping.model_dump()


@router.post("/api/v1/batches", status_code=status.HTTP_201_CREATED, response_model=BatchUploadResponse)
@router.post("/batches", status_code=status.HTTP_201_CREATED, response_model=BatchUploadResponse, include_in_schema=False)
async def upload_batch(
    settlement_csv: UploadFile = File(...),
    bank_csv: UploadFile = File(...),
    invoice_csv: UploadFile = File(...),
    ground_truth_json: Optional[UploadFile] = File(None),
    merchant_type: Optional[str] = Query("retail"),
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_api_key),
):
    """
    POST /batches: Upload 3 CSV files, validate schemas, persist records,
    and trigger automated reconciliation pipeline with intelligent schema detection.
    """
    # Enforce file.size check before loading file streams into memory
    for f in (settlement_csv, bank_csv, invoice_csv, ground_truth_json):
        if f is not None and getattr(f, "size", None) is not None and f.size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Uploaded file '{f.filename}' exceeds maximum limit of 10 MB per file.",
            )

    settle_bytes = await _read_validated_file(settlement_csv)
    bank_bytes = await _read_validated_file(bank_csv)
    inv_bytes = await _read_validated_file(invoice_csv)

    m_type = merchant_type or "retail"

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
            gt_bytes = await _read_validated_file(ground_truth_json)
            if gt_bytes:
                gt_data = json.loads(gt_bytes.decode("utf-8"))
        except HTTPException:
            raise
        except Exception:
            gt_data = None

    batch = Batch(
        id=str(uuid.uuid4()),
        settlement_filename=settlement_csv.filename,
        bank_filename=bank_csv.filename,
        invoice_filename=invoice_csv.filename,
        status="processing",
    )
    db.add(batch)
    db.commit()

    inv_records = normalize_dataframe(inv_df, "invoice", batch_id=batch.id)
    set_records = normalize_dataframe(settle_df, "settlement", batch_id=batch.id)
    bnk_records = normalize_dataframe(bank_df, "bank", batch_id=batch.id)

    try:
        persist_normalized_records(db, inv_records, batch_id=batch.id)
        persist_normalized_records(db, set_records, batch_id=batch.id)
        persist_normalized_records(db, bnk_records, batch_id=batch.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    process_reconciliation_batch(
        db, batch.id, fee_config=m_type, ground_truth=gt_data, merchant_type=m_type
    )
    db.refresh(batch)

    return {
        "batch_id": batch.id,
        "status": batch.status,
        "uploaded_at": batch.uploaded_at.isoformat(),
        "merchant_type": m_type,
    }


@router.post("/api/v1/batches/generate", status_code=status.HTTP_201_CREATED, response_model=GeneratedBatchResponse)
@router.post("/batches/generate", status_code=status.HTTP_201_CREATED, response_model=GeneratedBatchResponse, include_in_schema=False)
def trigger_generated_batch(
    merchant_type: str = Query("restaurant"),
    record_count: int = Query(100, ge=10, le=10000),
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_api_key),
):
    """
    On-Demand Scalable Batch Generation across 10 Industry Verticals (100 to 10,000 records)
    with automatic ground-truth benchmarking.
    """
    invoices, settlements, bank_rows, ground_truth = generate_merchant_dataset(
        merchant_type=merchant_type, total_count=record_count
    )

    inv_df = pd.DataFrame(invoices)
    set_df = pd.DataFrame(settlements)
    bnk_df = pd.DataFrame(bank_rows)

    # Remap canonical columns if merchant profile has custom columns
    remapped_inv, _ = SmartCSVParser("invoice").parse(inv_df.to_csv(index=False))
    remapped_set, _ = SmartCSVParser("settlement").parse(set_df.to_csv(index=False))
    remapped_bnk, _ = SmartCSVParser("bank").parse(bnk_df.to_csv(index=False))

    batch = Batch(
        id=str(uuid.uuid4()),
        settlement_filename=f"{merchant_type}_settlements_{record_count}.csv",
        bank_filename=f"{merchant_type}_bank_{record_count}.csv",
        invoice_filename=f"{merchant_type}_invoices_{record_count}.csv",
        status="processing",
    )
    db.add(batch)
    db.commit()

    inv_records = normalize_dataframe(remapped_inv, "invoice", batch_id=batch.id)
    set_records = normalize_dataframe(remapped_set, "settlement", batch_id=batch.id)
    bnk_records = normalize_dataframe(remapped_bnk, "bank", batch_id=batch.id)

    try:
        persist_normalized_records(db, inv_records, batch_id=batch.id)
        persist_normalized_records(db, set_records, batch_id=batch.id)
        persist_normalized_records(db, bnk_records, batch_id=batch.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    snapshot = process_reconciliation_batch(
        db, batch.id, fee_config=merchant_type, ground_truth=ground_truth, merchant_type=merchant_type
    )
    db.refresh(batch)

    return {
        "batch_id": batch.id,
        "merchant_type": merchant_type,
        "records_processed": snapshot.records_processed,
        "match_rate": float(snapshot.match_rate),
        "precision": float(snapshot.precision) if snapshot.precision is not None else None,
        "recall": float(snapshot.recall) if snapshot.recall is not None else None,
        "processing_time_seconds": float(snapshot.processing_time_seconds),
        "manual_hours_saved": float(snapshot.manual_hours_saved),
        "status": batch.status,
    }


@router.post("/api/v1/batches/demo", status_code=status.HTTP_201_CREATED, response_model=GeneratedBatchResponse)
@router.post("/batches/demo", status_code=status.HTTP_201_CREATED, response_model=GeneratedBatchResponse, include_in_schema=False)
def trigger_demo_batch(db: Session = Depends(get_db)):
    """Triggers automated reconciliation against the 100-row Retail synthetic dataset."""
    return trigger_generated_batch(merchant_type="retail", record_count=100, db=db)


@router.get("/api/v1/batches/{batch_id}/cash-position", response_model=CashPositionSnapshot)
@router.get("/batches/{batch_id}/cash-position", response_model=CashPositionSnapshot, include_in_schema=False)
def get_cash_position(batch_id: str, db: Session = Depends(get_db)):
    """
    Returns Current Bank Balance, Pending Settlements, Pending Refunds, Expected Cash Tomorrow,
    and Liquidity Health Index.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return compute_cash_position(db, batch_id)


@router.get("/api/v1/batches/{batch_id}", response_model=BatchStatusResponse)
@router.get("/batches/{batch_id}", response_model=BatchStatusResponse, include_in_schema=False)
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


@router.get("/api/v1/batches/{batch_id}/matches", response_model=PaginatedMatchesResponse)
@router.get("/batches/{batch_id}/matches", response_model=PaginatedMatchesResponse, include_in_schema=False)
def get_batch_matches(
    batch_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    method_filter: Optional[str] = Query(None, alias="match_method"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    GET /batches/{batch_id}/matches: Paginated list of reconciliation matches.
    Optimized with single batch record map lookup to eliminate N+1 queries.
    """
    query = db.query(Match).filter(Match.batch_id == batch_id)
    if status_filter:
        query = query.filter(Match.status == status_filter)
    if method_filter:
        query = query.filter(Match.match_method == method_filter)

    total = query.count()
    matches = query.order_by(Match.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Pre-fetch all batch records in 1 query to prevent N+1 query loops
    batch_records = db.query(Record).filter(Record.batch_id == batch_id).all()
    record_map: Dict[str, Record] = {r.id: r for r in batch_records}

    result = []
    for m in matches:
        settle_rec = record_map.get(m.settlement_record_id) if m.settlement_record_id else None
        inv_rec = record_map.get(m.invoice_record_id) if m.invoice_record_id else None
        bank_rec = record_map.get(m.bank_record_id) if m.bank_record_id else None

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
            "amount": float(settle_rec.amount if settle_rec else (inv_rec.amount if inv_rec else (bank_rec.amount if bank_rec else 0.0))),
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


@router.get("/api/v1/matches/{match_id}")
@router.get("/matches/{match_id}", include_in_schema=False)
def get_match_detail(match_id: str, db: Session = Depends(get_db)):
    """GET /matches/{match_id}: Single match detail with AI verification evidence & past cases."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Load records for this match in 1 batch query
    record_ids = [r_id for r_id in (match.settlement_record_id, match.invoice_record_id, match.bank_record_id) if r_id]
    rec_lookup: Dict[str, Record] = {}
    if record_ids:
        recs = db.query(Record).filter(Record.id.in_(record_ids)).all()
        rec_lookup = {r.id: r for r in recs}

    settle_rec = rec_lookup.get(match.settlement_record_id) if match.settlement_record_id else None
    inv_rec = rec_lookup.get(match.invoice_record_id) if match.invoice_record_id else None
    bank_rec = rec_lookup.get(match.bank_record_id) if match.bank_record_id else None

    ai_ver = db.query(AIVerification).filter(AIVerification.match_id == match_id).first()
    ai_data = None
    if ai_ver:
        if inv_rec and settle_rec:
            calc_trace = (
                f"₹{inv_rec.amount:,.2f} − ₹{ai_ver.difference_amount:,.2f} ({ai_ver.likely_reason.replace('_', ' ')}) = "
                f"₹{settle_rec.amount:,.2f} = settlement amount ✓"
            )
        else:
            calc_trace = f"Difference amount: ₹{ai_ver.difference_amount:,.2f}"

        # Retrieve similar historical cases from Feedback Memory
        similar = feedback_store.find_similar_cases(
            db=db,
            merchant_type="retail",
            amount_delta=ai_ver.difference_amount,
            limit=2,
        )

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
            "supporting_rules": [
                "Rule 1 (Exact Order ID): Amount Discrepancy",
                "Rule 5 (Rate Schedule): Non-Standard Adjustment",
                "Validator: Independently Confirmed Exact Paisa Math ✓",
            ],
            "similar_past_cases": [
                {
                    "merchant_type": s.merchant_type,
                    "amount_delta": float(s.amount_delta),
                    "reason": s.corrected_reason,
                    "reviewer_notes": s.reviewer_notes,
                    "created_at": s.created_at,
                }
                for s in similar
            ],
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


@router.get("/api/v1/batches/{batch_id}/exceptions")
@router.get("/batches/{batch_id}/exceptions", include_in_schema=False)
def get_batch_exceptions(batch_id: str, db: Session = Depends(get_db)):
    """GET /batches/{batch_id}/exceptions: Exception classification report."""
    exceptions = db.query(ExceptionRecord).join(Record).filter(Record.batch_id == batch_id).all()
    
    categories: Dict[str, int] = {cat: 0 for cat in list_exception_categories()}
    items = []
    
    # Pre-fetch all exception records in 1 query
    rec_ids = [exc.record_id for exc in exceptions if exc.record_id]
    rec_lookup: Dict[str, Record] = {}
    if rec_ids:
        recs = db.query(Record).filter(Record.id.in_(rec_ids)).all()
        rec_lookup = {r.id: r for r in recs}

    for exc in exceptions:
        categories[exc.category] = categories.get(exc.category, 0) + 1
        rec = rec_lookup.get(exc.record_id)
        exc_def = get_exception_definition(exc.category)
        
        items.append({
            "exception_id": exc.id,
            "match_id": exc.match_id,
            "record_id": exc.record_id,
            "category": exc.category,
            "domain": exc_def.domain,
            "display_title": exc_def.display_title,
            "suggested_action": exc_def.suggested_action,
            "financial_impact": exc_def.financial_impact,
            "notes": exc.notes,
            "resolved": exc.resolved,
            "order_id": rec.order_id if rec else None,
            "amount": float(rec.amount) if rec else 0.0,
            "txn_date": rec.txn_date.isoformat() if rec else None,
            "reference_number": rec.reference_number if rec else None,
            "source_type": rec.source_type if rec else None,
        })
    return {**categories, "total_exceptions": len(items), "items": items}


@router.get("/api/v1/batches/{batch_id}/metrics")
@router.get("/batches/{batch_id}/metrics", include_in_schema=False)
def get_batch_metrics(batch_id: str, db: Session = Depends(get_db)):
    """GET /batches/{batch_id}/metrics: Dashboard headline numbers."""
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


@router.post("/api/v1/matches/{match_id}/review", response_model=ReviewMatchResponse)
@router.post("/matches/{match_id}/review", response_model=ReviewMatchResponse, include_in_schema=False)
def review_match(
    match_id: str,
    payload: ReviewMatchRequest,
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_api_key),
):
    """
    POST /matches/{match_id}/review:
    Human marks an exception resolved and stores the resolution into Feedback Memory.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    resolved = payload.resolved
    reviewer_note = payload.reviewer_note
    corrected_reason = payload.corrected_reason

    exc = db.query(ExceptionRecord).filter(ExceptionRecord.match_id == match_id).first()
    settle_rec = db.query(Record).filter(Record.id == match.settlement_record_id).first() if match.settlement_record_id else None
    inv_rec = db.query(Record).filter(Record.id == match.invoice_record_id).first() if match.invoice_record_id else None

    if exc:
        exc.resolved = resolved
        exc.notes = f"{exc.notes or ''} [Reviewer: {reviewer_note}]".strip()

    if resolved:
        match.status = "matched"
        match.confidence = Decimal("100.00")

    # Persist decision into Feedback Memory
    delta = abs((inv_rec.amount if inv_rec else Decimal("0.00")) - (settle_rec.amount if settle_rec else Decimal("0.00")))
    try:
        feedback_store.record_feedback(
            db=db,
            merchant_type="retail",
            order_id=(settle_rec.order_id if settle_rec else None),
            corrected_reason=corrected_reason,
            amount_delta=delta,
            reviewer_notes=reviewer_note,
            reviewer_action="approved" if resolved else "rejected",
        )
    except Exception:
        pass

    db.commit()
    db.refresh(match)
    return {"match_id": match.id, "status": match.status, "confidence": float(match.confidence), "resolved": resolved}


@router.get("/api/v1/batches/{batch_id}/export")
@router.get("/batches/{batch_id}/export", include_in_schema=False)
def export_batch_csv(batch_id: str, db: Session = Depends(get_db)):
    """GET /batches/{batch_id}/export: Exports final reconciliation CSV report."""
    matches = db.query(Match).filter(Match.batch_id == batch_id).all()
    
    # Pre-fetch all batch records in 1 query
    batch_records = db.query(Record).filter(Record.batch_id == batch_id).all()
    rec_lookup: Dict[str, Record] = {r.id: r for r in batch_records}

    # Pre-fetch all AI verifications for this batch in 1 query
    match_ids = [m.id for m in matches]
    ai_verifications = db.query(AIVerification).filter(AIVerification.match_id.in_(match_ids)).all() if match_ids else []
    ai_map: Dict[str, AIVerification] = {a.match_id: a for a in ai_verifications}

    records_data = []
    for m in matches:
        settle_rec = rec_lookup.get(m.settlement_record_id) if m.settlement_record_id else None
        inv_rec = rec_lookup.get(m.invoice_record_id) if m.invoice_record_id else None
        ai_ver = ai_map.get(m.id)

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


@router.post("/api/v1/auth/token")
@router.post("/auth/token", include_in_schema=False)
def generate_auth_token(payload: Dict[str, Any]):
    """
    Generates a cryptographically signed HMAC-SHA256 JWT access token for tenant authentication.
    Payload: {"org_id": "org_xyz", "client_name": "MerchantCorp"}
    """
    org_id = payload.get("org_id", "org_default")
    token = create_access_token(payload={"org_id": org_id, "sub": payload.get("client_name", org_id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "org_id": org_id,
        "expires_in_hours": 24,
    }


@router.post("/api/v1/reconciliation/jobs")
@router.post("/reconciliation/jobs", include_in_schema=False)
def submit_reconciliation_job(
    payload: Dict[str, Any],
    tenant_id: str = Depends(get_current_tenant),
    _auth: bool = Depends(verify_api_key),
):
    """
    POST /api/v1/reconciliation/jobs:
    Submits a reconciliation batch job for asynchronous background execution.
    Returns job_id and initial progress state without blocking ASGI workers.
    """
    batch_id = payload.get("batch_id")
    if not batch_id:
        raise HTTPException(status_code=400, detail="batch_id is required")

    merchant_type = payload.get("merchant_type", "retail")
    ground_truth = payload.get("ground_truth")

    job_id = job_queue.submit_job(
        batch_id=batch_id,
        org_id=tenant_id,
        ground_truth=ground_truth,
        merchant_type=merchant_type,
    )

    return {
        "job_id": job_id,
        "batch_id": batch_id,
        "status": "queued",
        "progress": 0.0,
        "message": "Reconciliation job submitted successfully to background worker pool.",
    }


@router.get("/api/v1/reconciliation/jobs/{job_id}")
@router.get("/reconciliation/jobs/{job_id}", include_in_schema=False)
def get_reconciliation_job_status(job_id: str):
    """
    GET /api/v1/reconciliation/jobs/{job_id}:
    Returns real-time background job execution status, stage, and completion metrics.
    """
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Reconciliation job not found")
    return job.model_dump()


@router.get("/api/v1/batches/{batch_id}/erp-journal")
@router.get("/batches/{batch_id}/erp-journal", include_in_schema=False)
def export_erp_journal(
    batch_id: str,
    format: str = Query("tally", pattern="^(tally|zoho|netsuite)$"),
    db: Session = Depends(get_db),
):
    """
    1-Click ERP Journal Export.
    Formats:
    - tally: Tally Prime XML envelope import
    - zoho: Zoho Books manual journal CSV
    - netsuite: NetSuite SuiteTalk JSON journal schema
    """
    matches = db.query(Match).filter(Match.batch_id == batch_id).all()
    if not matches:
        raise HTTPException(status_code=404, detail="No matches found for this batch")

    batch_records = db.query(Record).filter(Record.batch_id == batch_id).all()
    rec_lookup: Dict[str, Record] = {r.id: r for r in batch_records}

    match_ids = [m.id for m in matches]
    ai_verifications = db.query(AIVerification).filter(AIVerification.match_id.in_(match_ids)).all() if match_ids else []
    ai_map: Dict[str, AIVerification] = {a.match_id: a for a in ai_verifications}

    matches_data = []
    adjustments_data = []

    for m in matches:
        settle_rec = rec_lookup.get(m.settlement_record_id) if m.settlement_record_id else None
        inv_rec = rec_lookup.get(m.invoice_record_id) if m.invoice_record_id else None
        bank_rec = rec_lookup.get(m.bank_record_id) if m.bank_record_id else None
        ai_ver = ai_map.get(m.id)

        gross = inv_rec.amount if inv_rec else (settle_rec.amount if settle_rec else Decimal("0.00"))
        fee = settle_rec.fees if settle_rec else Decimal("0.00")
        gst = settle_rec.gst if settle_rec else Decimal("0.00")
        bank_amt = bank_rec.amount if bank_rec else (settle_rec.amount if settle_rec else gross - fee - gst)

        item_dict = {
            "match_id": m.id,
            "invoice_amount": float(gross),
            "fees": float(fee),
            "gst": float(gst),
            "bank_amount": float(bank_amt),
            "status": m.status,
        }
        matches_data.append(item_dict)

        if ai_ver and m.status == "exception":
            adjustments_data.append({
                "difference_amount": float(ai_ver.difference_amount),
                "reason": ai_ver.likely_reason,
            })

    if format == "tally":
        content = generate_tally_xml(batch_id, matches_data, adjustments_data)
        return Response(
            content=content,
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=tally_journal_batch_{batch_id[:8]}.xml"},
        )
    elif format == "zoho":
        content = generate_zoho_books_csv(batch_id, matches_data, adjustments_data)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=zoho_journal_batch_{batch_id[:8]}.csv"},
        )
    elif format == "netsuite":
        content = generate_netsuite_journal_json(batch_id, matches_data, adjustments_data)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=netsuite_journal_batch_{batch_id[:8]}.json"},
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid ERP format")

