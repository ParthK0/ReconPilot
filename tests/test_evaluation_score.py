import os
import json
import pytest
from backend.evaluation.score import run_evaluation, EvaluationScoreResult


def test_evaluation_score_runs_and_produces_valid_metrics(tmp_path):
    """
    Asserts that backend.evaluation.score executes end-to-end against the synthetic data,
    computes accurate raw metrics, and exports a valid structured JSON output.
    """
    output_json = tmp_path / "test_evaluation_results.json"
    
    result = run_evaluation(
        data_dir="backend/synthetic-data",
        output_json_path=str(output_json),
        manual_min_per_record=3.0,
    )
    
    assert isinstance(result, EvaluationScoreResult)
    assert result.total_records == 100
    assert result.rule_matches_count == 86
    assert result.ai_verified_count == 6
    assert result.exceptions_count == 8
    
    # Assert confusion matrix counts
    assert result.true_positives == 92
    assert result.false_positives == 0
    assert result.true_negatives == 8
    assert result.false_negatives == 0
    assert len(result.false_positive_record_ids) == 0
    assert len(result.false_negative_record_ids) == 0
    
    # Assert exact unrounded percentages
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.match_rate == 0.92
    assert result.f1_score == 1.0
    
    # Assert Engine-touched subset (14 records)
    assert result.engine_touched_subset_count == 14
    assert result.engine_verified_matches == 6
    assert result.engine_correct_decisions == 14
    assert result.engine_accuracy == 1.0
    assert result.engine_reason_accuracy_on_matches == 1.0
    
    # Assert performance & ROI
    assert result.processing_time_seconds < 30.0
    assert result.manual_hours_saved > 4.5
    
    # Assert exported JSON is valid
    assert os.path.exists(str(output_json))
    with open(str(output_json), "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert data["batch_id"] == result.batch_id
    assert data["total_records"] == 100
    assert len(data["detailed_records"]) == 100
