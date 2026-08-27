"""
backend/ai/feedback_memory.py
==============================
ReconPilot 2.0: Feedback Memory Store (Learning via Retrieval).

Enables the Finance Verification Engine to remember and retrieve human reviewer
corrections and approvals. When an ambiguous discrepancy is encountered:
1. Engine queries Feedback Memory for similar historical cases (matching merchant_type, delta, pattern).
2. If a trusted historical precedent exists (e.g. human confirmed "processing_fee waiver"),
   the engine cites the historical case in its evidence drawer and boosts confidence.
3. When a human reviews an exception via POST /matches/{id}/review, the decision
   is immutably stored in the Feedback Memory table.
"""

import os
import uuid
import time
from decimal import Decimal
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.db.models import FeedbackMemoryRecord


class HistoricalPrecedent(BaseModel):
    precedent_id: str
    merchant_type: str
    corrected_reason: str
    amount_delta: Decimal
    reviewer_notes: str
    reviewer_action: str
    created_at: str
    similarity_score: float = Field(ge=0.0, le=1.0)


class FeedbackMemoryStore:
    """
    Retrieval-based memory interface for financial reconciliation corrections.
    """

    def record_feedback(
        self,
        db: Session,
        merchant_type: str,
        corrected_reason: str,
        amount_delta: Decimal,
        order_id: Optional[str] = None,
        discrepancy_pattern: Optional[str] = None,
        original_ai_reason: Optional[str] = None,
        evidence_field: Optional[str] = None,
        reviewer_notes: Optional[str] = None,
        reviewer_action: str = "approved",
    ) -> FeedbackMemoryRecord:
        """
        Stores a human reconciliation correction or approval in the persistent memory table.
        """
        pattern = discrepancy_pattern or f"delta_{round(float(amount_delta), 2)}"
        
        record = FeedbackMemoryRecord(
            id=str(uuid.uuid4()),
            merchant_type=merchant_type.strip().lower(),
            order_id=order_id,
            discrepancy_pattern=pattern,
            original_ai_reason=original_ai_reason,
            corrected_reason=corrected_reason,
            amount_delta=amount_delta,
            evidence_field=evidence_field,
            reviewer_notes=reviewer_notes,
            reviewer_action=reviewer_action,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def find_similar_cases(
        self,
        db: Session,
        merchant_type: str,
        amount_delta: Decimal,
        candidate_reason: Optional[str] = None,
        limit: int = 3,
    ) -> List[HistoricalPrecedent]:
        """
        Retrieves past human reviewer decisions for similar delta/merchant patterns.
        """
        m_type = merchant_type.strip().lower()
        query = db.query(FeedbackMemoryRecord).filter(
            (FeedbackMemoryRecord.merchant_type == m_type) | (FeedbackMemoryRecord.merchant_type == "global")
        )
        
        records = query.order_by(FeedbackMemoryRecord.created_at.desc()).limit(50).all()
        results: List[HistoricalPrecedent] = []

        for rec in records:
            # Compute heuristic similarity score
            delta_diff = abs(rec.amount_delta - amount_delta)
            if delta_diff == Decimal("0.00"):
                score = 1.0
            elif delta_diff <= Decimal("5.00"):
                score = 0.90
            elif delta_diff <= Decimal("50.00"):
                score = 0.75
            else:
                score = 0.50

            if candidate_reason and rec.corrected_reason == candidate_reason:
                score = min(1.0, score + 0.1)

            results.append(
                HistoricalPrecedent(
                    precedent_id=rec.id,
                    merchant_type=rec.merchant_type,
                    corrected_reason=rec.corrected_reason,
                    amount_delta=rec.amount_delta,
                    reviewer_notes=rec.reviewer_notes or "Verified by finance controller.",
                    reviewer_action=rec.reviewer_action,
                    created_at=rec.created_at.strftime("%Y-%m-%d %H:%M UTC") if rec.created_at else "Earlier Batch",
                    similarity_score=score,
                )
            )

        # Sort by similarity and return top matches
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:limit]


# Global singleton
feedback_store = FeedbackMemoryStore()
