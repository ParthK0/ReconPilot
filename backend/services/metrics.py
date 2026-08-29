"""
backend/services/metrics.py
===========================
Metrics computation service for reconciliation batches and honest evaluation.
"""

from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.models import MetricsSnapshot, Match, ExceptionRecord, Record


class BatchMetricsResult(BaseModel):
    total_records: int
    matched_count: int
    rule_matches_count: int
    ai_verified_count: int
    exceptions_count: int
    match_rate: float
    precision: Optional[float] = None
    recall: Optional[float] = None
    true_positives: Optional[int] = None
    false_positives: Optional[int] = None
    false_negatives: Optional[int] = None
    ai_accuracy: Optional[float] = None
    processing_time_seconds: float = 0.0
    manual_hours_saved: float = 0.0


def compute_batch_metrics(
    total_records: int,
    true_positives: Optional[int] = None,
    false_positives: Optional[int] = None,
    false_negatives: Optional[int] = None,
    rule_matches: int = 0,
    ai_verified: int = 0,
    exceptions: int = 0,
    ai_correct: Optional[int] = None,
    ai_total: Optional[int] = None,
    processing_time_seconds: float = 0.0,
) -> BatchMetricsResult:
    """
    Computes standard reconciliation evaluation metrics:
    - If ground truth is provided: computes precision, recall, and AI accuracy.
    - If ground truth is absent: precision/recall/ai_accuracy remain None.
    - Honest manual hours saved calculation (3 min/txn baseline minus exception review).
    """
    matched = rule_matches + ai_verified
    match_rate = (matched / total_records * 100.0) if total_records > 0 else 0.0

    if true_positives is not None and false_positives is not None:
        total_eval_matched = true_positives + false_positives
        precision = (true_positives / total_eval_matched * 100.0) if total_eval_matched > 0 else 100.0
    else:
        precision = None

    if true_positives is not None and false_negatives is not None:
        total_actual_positives = true_positives + false_negatives
        recall = (true_positives / total_actual_positives * 100.0) if total_actual_positives > 0 else 100.0
    else:
        recall = None

    if ai_correct is not None and ai_total is not None and ai_total > 0:
        ai_accuracy = (ai_correct / ai_total * 100.0)
    elif ai_total == 0:
        ai_accuracy = 100.0
    else:
        ai_accuracy = None

    # Assumed 3 minutes per manual reconciliation record baseline
    manual_minutes_baseline = total_records * 3.0
    residual_review_minutes = exceptions * 3.0 + (processing_time_seconds / 60.0)
    manual_hours_saved = max(0.0, (manual_minutes_baseline - residual_review_minutes) / 60.0)

    return BatchMetricsResult(
        total_records=total_records,
        matched_count=matched,
        rule_matches_count=rule_matches,
        ai_verified_count=ai_verified,
        exceptions_count=exceptions,
        match_rate=round(match_rate, 2),
        precision=round(precision, 2) if precision is not None else None,
        recall=round(recall, 2) if recall is not None else None,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        ai_accuracy=round(ai_accuracy, 2) if ai_accuracy is not None else None,
        processing_time_seconds=round(processing_time_seconds, 2),
        manual_hours_saved=round(manual_hours_saved, 2),
    )
