import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy import (
    Column,
    String,
    Text,
    Numeric,
    Date,
    DateTime,
    Boolean,
    Integer,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def get_uuid_column(is_pk: bool = False, fk_target: Optional[str] = None, nullable: bool = False):
    """
    Returns a UUID column compatible with both PostgreSQL and SQLite (fallback).
    """
    col_type = String(36)
    if is_pk:
        return Column(col_type, primary_key=True, default=lambda: str(uuid.uuid4()))
    if fk_target:
        return Column(col_type, ForeignKey(fk_target), nullable=nullable)
    return Column(col_type, nullable=nullable)


class Batch(Base):
    __tablename__ = "batches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(100), nullable=False, default="org_default", index=True)
    settlement_filename = Column(Text, nullable=True)
    bank_filename = Column(Text, nullable=True)
    invoice_filename = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="uploaded")  # uploaded, processing, done, failed
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    records = relationship("Record", back_populates="batch", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="batch", cascade="all, delete-orphan")
    metrics_snapshots = relationship("MetricsSnapshot", back_populates="batch", cascade="all, delete-orphan")


class Record(Base):
    __tablename__ = "records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(100), nullable=False, default="org_default", index=True)
    batch_id = Column(String(36), ForeignKey("batches.id"), nullable=False)
    source_type = Column(String(50), nullable=False)  # settlement, bank, invoice
    transaction_id = Column(String(100), nullable=False)
    order_id = Column(String(100), nullable=True)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    fx_rate = Column(Numeric(10, 4), nullable=False, default=Decimal("1.0000"))
    txn_date = Column(Date, nullable=False)
    reference_number = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False)
    fees = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    gst = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    tds = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    raw_payload = Column(JSON, nullable=True)

    batch = relationship("Batch", back_populates="records")
    exceptions = relationship("ExceptionRecord", back_populates="record", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_records_batch_source", "batch_id", "source_type"),
        Index("idx_records_order_id", "order_id"),
        Index("idx_records_reference_number", "reference_number"),
        Index("idx_records_org_id", "org_id"),
    )


class Match(Base):
    __tablename__ = "matches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(100), nullable=False, default="org_default", index=True)
    batch_id = Column(String(36), ForeignKey("batches.id"), nullable=False)
    settlement_record_id = Column(String(36), ForeignKey("records.id"), nullable=True)
    bank_record_id = Column(String(36), ForeignKey("records.id"), nullable=True)
    invoice_record_id = Column(String(36), ForeignKey("records.id"), nullable=True)
    match_method = Column(String(50), nullable=False)  # rule, ai
    rule_name = Column(String(100), nullable=True)
    confidence = Column(Numeric(5, 2), nullable=False, default=Decimal("100.00"))
    status = Column(String(50), nullable=False, default="matched")  # matched, exception
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    batch = relationship("Batch", back_populates="matches")
    settlement_record = relationship("Record", foreign_keys=[settlement_record_id])
    bank_record = relationship("Record", foreign_keys=[bank_record_id])
    invoice_record = relationship("Record", foreign_keys=[invoice_record_id])
    ai_verification = relationship("AIVerification", back_populates="match", uselist=False, cascade="all, delete-orphan")
    exceptions = relationship("ExceptionRecord", back_populates="match", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_matches_batch_status", "batch_id", "status"),
        Index("idx_matches_org_id", "org_id"),
    )


class AIVerification(Base):
    __tablename__ = "ai_verifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    match_id = Column(String(36), ForeignKey("matches.id"), nullable=False, unique=True)
    difference_amount = Column(Numeric(14, 2), nullable=False)
    likely_reason = Column(String(100), nullable=False)
    reasoning_explanation = Column(Text, nullable=False)
    expected_value = Column(Numeric(14, 2), nullable=False)
    ai_confidence = Column(Numeric(5, 2), nullable=False)
    adjusted_confidence = Column(Numeric(5, 2), nullable=False)
    evidence_field = Column(String(100), nullable=False)
    model_used = Column(String(100), nullable=False, default="gpt-5.6-terra")
    prompt_tokens = Column(Integer, nullable=True, default=0)
    completion_tokens = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    match = relationship("Match", back_populates="ai_verification")


class ExceptionRecord(Base):
    __tablename__ = "exceptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(100), nullable=False, default="org_default", index=True)
    match_id = Column(String(36), ForeignKey("matches.id"), nullable=True)
    record_id = Column(String(36), ForeignKey("records.id"), nullable=False)
    category = Column(String(100), nullable=False)  # 30+ categories from exception_taxonomy
    notes = Column(Text, nullable=True)
    resolved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    match = relationship("Match", back_populates="exceptions")
    record = relationship("Record", back_populates="exceptions")

    __table_args__ = (
        Index("idx_exceptions_category", "category"),
        Index("idx_exceptions_org_id", "org_id"),
    )


class MetricsSnapshot(Base):
    __tablename__ = "metrics_snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(100), nullable=False, default="org_default", index=True)
    batch_id = Column(String(36), ForeignKey("batches.id"), nullable=False)
    records_processed = Column(Integer, nullable=False)
    rule_matches = Column(Integer, nullable=False)
    ai_verified = Column(Integer, nullable=False)
    needs_review = Column(Integer, nullable=False)
    match_rate = Column(Numeric(5, 2), nullable=False)
    precision = Column(Numeric(5, 2), nullable=True)
    recall = Column(Numeric(5, 2), nullable=True)
    true_positives = Column(Integer, nullable=True)
    false_positives = Column(Integer, nullable=True)
    false_negatives = Column(Integer, nullable=True)
    ai_accuracy = Column(Numeric(5, 2), nullable=True)
    processing_time_seconds = Column(Numeric(8, 2), nullable=False)
    manual_hours_saved = Column(Numeric(6, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    batch = relationship("Batch", back_populates="metrics_snapshots")

    __table_args__ = (
        Index("idx_metrics_snapshots_org_id", "org_id"),
    )


class FeedbackMemoryRecord(Base):
    __tablename__ = "feedback_memory"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(100), nullable=False, default="org_default", index=True)
    merchant_type = Column(String(50), nullable=False)
    order_id = Column(String(100), nullable=True)
    discrepancy_pattern = Column(String(100), nullable=False)
    original_ai_reason = Column(String(100), nullable=True)
    corrected_reason = Column(String(100), nullable=False)
    amount_delta = Column(Numeric(14, 2), nullable=False)
    evidence_field = Column(String(100), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    reviewer_action = Column(String(50), nullable=False, default="approved")
    confidence_boost = Column(Numeric(5, 2), nullable=False, default=Decimal("5.00"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_feedback_merchant_pattern", "merchant_type", "discrepancy_pattern"),
        Index("idx_feedback_corrected_reason", "corrected_reason"),
        Index("idx_feedback_org_id", "org_id"),
    )
