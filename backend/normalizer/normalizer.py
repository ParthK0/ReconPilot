import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional, Union
import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.db.models import Record
from backend.normalizer.data_cleaners import (
    clean_currency,
    clean_date,
    clean_reference,
    clean_order_id,
    clean_status,
)


class NormalizedRecord(BaseModel):
    """
    Unified record schema matching FR-3 and docs/04-Database-Design.md (`records` table).
    """
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    batch_id: Optional[str] = None
    source_type: str  # 'invoice', 'settlement', 'bank'
    transaction_id: str
    order_id: Optional[str] = None
    amount: Decimal
    txn_date: date
    reference_number: Optional[str] = None
    status: str
    fees: Decimal = Decimal("0.00")
    gst: Decimal = Decimal("0.00")
    tds: Decimal = Decimal("0.00")
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


def parse_date_str(val: Any) -> date:
    """Robust date parsing for varied date string formats (delegates to clean_date)."""
    return clean_date(val)


def _clean_decimal(val: Any, default: Decimal = Decimal("0.00")) -> Decimal:
    """Safely converts arbitrary values to Decimal (delegates to clean_currency)."""
    return clean_currency(val, default=default)


def _clean_str(val: Any) -> Optional[str]:
    """Cleans strings, returning None for empty / NaN values."""
    if val is None or pd.isna(val):
        return None
    val_str = str(val).strip()
    return val_str if val_str else None


def normalize_invoice_row(row: Dict[str, Any], batch_id: Optional[str] = None) -> NormalizedRecord:
    """Normalizes a single invoice CSV row into the unified record schema."""
    raw = {k: (None if pd.isna(v) else v) for k, v in row.items()}
    # Resolve invoice date from invoice_date or generic date/created_at
    inv_date_val = row.get("invoice_date") or row.get("date") or row.get("created_at") or row.get("txn_date")
    return NormalizedRecord(
        batch_id=batch_id,
        source_type="invoice",
        transaction_id=str(row.get("invoice_id") or row.get("transaction_id") or uuid.uuid4()).strip(),
        order_id=clean_order_id(row.get("order_id")),
        amount=clean_currency(row["amount"]),
        txn_date=clean_date(inv_date_val),
        reference_number=None,
        status=clean_status(row.get("status"), default="paid"),
        fees=Decimal("0.00"),
        gst=Decimal("0.00"),
        tds=Decimal("0.00"),
        raw_payload=raw,
    )


def normalize_settlement_row(row: Dict[str, Any], batch_id: Optional[str] = None) -> NormalizedRecord:
    """Normalizes a single Razorpay settlement CSV row into the unified record schema."""
    raw = {k: (None if pd.isna(v) else v) for k, v in row.items()}
    set_date_val = row.get("settlement_date") or row.get("date") or row.get("payout_date") or row.get("txn_date")
    return NormalizedRecord(
        batch_id=batch_id,
        source_type="settlement",
        transaction_id=str(row.get("settlement_id") or row.get("transaction_id") or uuid.uuid4()).strip(),
        order_id=clean_order_id(row.get("order_id")),
        amount=clean_currency(row["amount"]),
        txn_date=clean_date(set_date_val),
        reference_number=clean_reference(row.get("reference_number")),
        status=clean_status(row.get("status"), default="settled"),
        fees=clean_currency(row.get("fees", 0)),
        gst=clean_currency(row.get("gst", 0)),
        tds=clean_currency(row.get("tds", 0)),
        raw_payload=raw,
    )


def normalize_bank_row(row: Dict[str, Any], batch_id: Optional[str] = None) -> NormalizedRecord:
    """Normalizes a single bank statement CSV row into the unified record schema."""
    raw = {k: (None if pd.isna(v) else v) for k, v in row.items()}
    bnk_date_val = row.get("txn_date") or row.get("date") or row.get("posting_date")
    return NormalizedRecord(
        batch_id=batch_id,
        source_type="bank",
        transaction_id=str(row.get("bank_txn_id") or row.get("transaction_id") or uuid.uuid4()).strip(),
        order_id=None,
        amount=clean_currency(row["amount"]),
        txn_date=clean_date(bnk_date_val),
        reference_number=clean_reference(row.get("reference_number")),
        status=clean_status(row.get("status"), default="credited"),
        fees=Decimal("0.00"),
        gst=Decimal("0.00"),
        tds=Decimal("0.00"),
        raw_payload=raw,
    )


def normalize_record(row: Dict[str, Any], source_type: str, batch_id: Optional[str] = None) -> NormalizedRecord:
    """
    FR-3: Normalizes a single dictionary row from any source type into the unified record schema.
    """
    source_lower = source_type.strip().lower()
    if source_lower == "invoice":
        return normalize_invoice_row(row, batch_id=batch_id)
    elif source_lower == "settlement":
        return normalize_settlement_row(row, batch_id=batch_id)
    elif source_lower in ("bank", "bank_statement", "bank_statements"):
        return normalize_bank_row(row, batch_id=batch_id)
    else:
        raise ValueError(f"Unknown source_type '{source_type}'. Expected 'invoice', 'settlement', or 'bank'.")


def normalize_dataframe(
    df: pd.DataFrame,
    source_type: str,
    batch_id: Optional[str] = None,
) -> List[NormalizedRecord]:
    """
    Normalizes an entire DataFrame of a specific source type into a list of NormalizedRecord objects.
    """
    records: List[NormalizedRecord] = []
    for _, row in df.iterrows():
        records.append(normalize_record(row.to_dict(), source_type, batch_id=batch_id))
    return records


def persist_normalized_records(
    db: Session,
    records: List[NormalizedRecord],
    batch_id: str,
) -> List[Record]:
    """
    Writes normalized records into the PostgreSQL `records` table tagged with batch_id and source_type.
    """
    db_records: List[Record] = []
    for rec in records:
        record_id = rec.id or str(uuid.uuid4())
        db_rec = Record(
            id=record_id,
            batch_id=batch_id,
            source_type=rec.source_type,
            transaction_id=rec.transaction_id,
            order_id=rec.order_id,
            amount=rec.amount,
            txn_date=rec.txn_date,
            reference_number=rec.reference_number,
            status=rec.status,
            fees=rec.fees,
            gst=rec.gst,
            tds=rec.tds,
            raw_payload=rec.raw_payload,
        )
        db_records.append(db_rec)
        db.add(db_rec)
    
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ValueError(
            f"Duplicate record detected for batch '{batch_id}'. A record with the same transaction ID and source type already exists."
        ) from e

    for db_rec in db_records:
        db.refresh(db_rec)
    return db_records


def normalize_and_persist(
    db: Session,
    df: pd.DataFrame,
    source_type: str,
    batch_id: str,
) -> List[Record]:
    """
    Combines normalization and database persistence into a single atomic operation.
    """
    normalized_list = normalize_dataframe(df, source_type, batch_id=batch_id)
    return persist_normalized_records(db, normalized_list, batch_id=batch_id)
