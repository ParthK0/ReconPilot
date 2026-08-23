import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional, Union
import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.models import Record


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
    """Robust date parsing for varied date string formats."""
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date string: '{val_str}'")


def _clean_decimal(val: Any, default: Decimal = Decimal("0.00")) -> Decimal:
    """Safely converts arbitrary values to Decimal."""
    if val is None or pd.isna(val) or str(val).strip() == "":
        return default
    try:
        return Decimal(str(val).strip())
    except Exception:
        return default


def _clean_str(val: Any) -> Optional[str]:
    """Cleans strings, returning None for empty / NaN values."""
    if val is None or pd.isna(val):
        return None
    val_str = str(val).strip()
    return val_str if val_str else None


def normalize_invoice_row(row: Dict[str, Any], batch_id: Optional[str] = None) -> NormalizedRecord:
    """Normalizes a single invoice CSV row into the unified record schema."""
    raw = {k: (None if pd.isna(v) else v) for k, v in row.items()}
    return NormalizedRecord(
        batch_id=batch_id,
        source_type="invoice",
        transaction_id=str(row["invoice_id"]).strip(),
        order_id=_clean_str(row.get("order_id")),
        amount=_clean_decimal(row["amount"]),
        txn_date=parse_date_str(row["invoice_date"]),
        reference_number=None,
        status=str(row.get("status", "paid")).strip(),
        fees=Decimal("0.00"),
        gst=Decimal("0.00"),
        tds=Decimal("0.00"),
        raw_payload=raw,
    )


def normalize_settlement_row(row: Dict[str, Any], batch_id: Optional[str] = None) -> NormalizedRecord:
    """Normalizes a single Razorpay settlement CSV row into the unified record schema."""
    raw = {k: (None if pd.isna(v) else v) for k, v in row.items()}
    return NormalizedRecord(
        batch_id=batch_id,
        source_type="settlement",
        transaction_id=str(row["settlement_id"]).strip(),
        order_id=_clean_str(row.get("order_id")),
        amount=_clean_decimal(row["amount"]),
        txn_date=parse_date_str(row["settlement_date"]),
        reference_number=_clean_str(row.get("reference_number")),
        status=str(row.get("status", "settled")).strip(),
        fees=_clean_decimal(row.get("fees", 0)),
        gst=_clean_decimal(row.get("gst", 0)),
        tds=_clean_decimal(row.get("tds", 0)),
        raw_payload=raw,
    )


def normalize_bank_row(row: Dict[str, Any], batch_id: Optional[str] = None) -> NormalizedRecord:
    """Normalizes a single bank statement CSV row into the unified record schema."""
    raw = {k: (None if pd.isna(v) else v) for k, v in row.items()}
    return NormalizedRecord(
        batch_id=batch_id,
        source_type="bank",
        transaction_id=str(row["bank_txn_id"]).strip(),
        order_id=None,
        amount=_clean_decimal(row["amount"]),
        txn_date=parse_date_str(row["txn_date"]),
        reference_number=_clean_str(row.get("reference_number")),
        status=str(row.get("status", "credited")).strip(),
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
    
    db.commit()
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
