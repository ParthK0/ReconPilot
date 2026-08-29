"""
backend/api/schemas.py
======================
Typed Pydantic request and response schemas for ReconPilot REST API.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ReviewMatchRequest(BaseModel):
    """Request payload for manual review of a match or exception."""
    resolved: bool = Field(default=True, description="Whether the discrepancy is marked resolved.")
    reviewer_note: str = Field(
        default="Reviewed and resolved manually.",
        description="Audit note detailing reason for approval or resolution."
    )
    corrected_reason: str = Field(
        default="manual_fee_adjustment",
        description="Category classification for the human-approved precedent."
    )


class ReviewMatchResponse(BaseModel):
    """Response returned after processing a match review."""
    match_id: str
    status: str
    confidence: float
    resolved: bool


class BatchStatusResponse(BaseModel):
    """Response returned for batch metadata status check."""
    batch_id: str
    status: str
    records_processed: int
    settlement_filename: Optional[str] = None
    bank_filename: Optional[str] = None
    invoice_filename: Optional[str] = None
    uploaded_at: str


class GeneratedBatchResponse(BaseModel):
    """Response returned after on-demand synthetic batch generation."""
    batch_id: str
    merchant_type: str
    records_processed: int
    match_rate: float
    precision: Optional[float] = None
    recall: Optional[float] = None
    processing_time_seconds: float
    manual_hours_saved: float
    status: str


class BatchUploadResponse(BaseModel):
    """Response returned when 3 CSV files are uploaded."""
    batch_id: str
    status: str
    uploaded_at: str
    merchant_type: str


class MatchSummaryItem(BaseModel):
    """Summary record for paginated match lists."""
    match_id: str
    status: str
    match_method: str
    rule_name: Optional[str] = None
    confidence: float
    settlement_record_id: Optional[str] = None
    invoice_record_id: Optional[str] = None
    bank_record_id: Optional[str] = None
    order_id: Optional[str] = None
    amount: float
    settlement_amount: Optional[float] = None
    invoice_amount: Optional[float] = None
    bank_amount: Optional[float] = None
    reference_number: Optional[str] = None
    created_at: str


class PaginatedMatchesResponse(BaseModel):
    """Paginated matches wrapper."""
    page: int
    page_size: int
    total: int
    matches: List[MatchSummaryItem]


class MerchantMetadataResponse(BaseModel):
    """Metadata for a registered industry archetype."""
    merchant_type: str
    display_name: str
    description: str
    primary_payment_mode: str
    typical_settlement_window_days: int
    common_exceptions: List[str]
    currency_format: str
    date_format: str
