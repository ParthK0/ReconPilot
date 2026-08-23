from decimal import Decimal
from typing import Dict, List, Any
from pydantic import BaseModel, Field


class EvaluationMetrics(BaseModel):
    total_records: int
    matched_count: int
    rule_matches_count: int
    ai_verified_count: int
    exceptions_count: int
    match_rate: float
    precision: float
    recall: float
    true_positives: int
    false_positives: int
    false_negatives: int
    ai_verification_accuracy: float
    manual_hours_saved: float
    processing_time_seconds: float = 0.0


def calculate_metrics(
    total_records: int,
    true_positives: int,
    false_positives: int,
    false_negatives: int,
    rule_matches: int,
    ai_verified: int,
    exceptions: int,
    ai_correct: int,
    ai_total: int,
    processing_time_seconds: float = 14.5,
) -> EvaluationMetrics:
    """
    Computes standard reconciliation evaluation metrics matching 07-Evaluation-Plan.md.
    """
    matched = true_positives + false_positives
    match_rate = (matched / total_records * 100.0) if total_records > 0 else 0.0
    
    precision = (true_positives / (true_positives + false_positives) * 100.0) if (true_positives + false_positives) > 0 else 100.0
    recall = (true_positives / (true_positives + false_negatives) * 100.0) if (true_positives + false_negatives) > 0 else 100.0
    
    ai_accuracy = (ai_correct / ai_total * 100.0) if ai_total > 0 else 100.0
    
    # Assumed 3 minutes per manual reconciliation record baseline
    manual_minutes_baseline = total_records * 3.0
    residual_review_minutes = exceptions * 3.0 + (processing_time_seconds / 60.0)
    manual_hours_saved = max(0.0, (manual_minutes_baseline - residual_review_minutes) / 60.0)

    return EvaluationMetrics(
        total_records=total_records,
        matched_count=matched,
        rule_matches_count=rule_matches,
        ai_verified_count=ai_verified,
        exceptions_count=exceptions,
        match_rate=round(match_rate, 2),
        precision=round(precision, 2),
        recall=round(recall, 2),
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        ai_verification_accuracy=round(ai_accuracy, 2),
        manual_hours_saved=round(manual_hours_saved, 2),
        processing_time_seconds=round(processing_time_seconds, 2),
    )
