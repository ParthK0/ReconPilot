from decimal import Decimal
import os
import json
import time
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class EvaluationMetrics(BaseModel):
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
    ai_verification_accuracy: Optional[float] = None
    manual_hours_saved: float
    processing_time_seconds: float = 0.0


class MerchantEvaluationReport(BaseModel):
    merchant_type: str
    display_name: str
    total_records: int
    rule_matches: int
    ai_verified: int
    exceptions: int
    match_rate: float
    precision: float
    recall: float
    ai_accuracy: float
    processing_time_seconds: float
    schema_mapping_successful: bool = True


class CrossMerchantEvaluationResult(BaseModel):
    total_merchants: int
    total_records_evaluated: int
    aggregate_match_rate: float
    aggregate_precision: float
    aggregate_recall: float
    aggregate_ai_accuracy: float
    total_processing_time_seconds: float
    total_manual_hours_saved: float
    merchant_reports: Dict[str, MerchantEvaluationReport]


from backend.services.metrics import compute_batch_metrics


def calculate_metrics(
    total_records: int,
    true_positives: Optional[int] = None,
    false_positives: Optional[int] = None,
    false_negatives: Optional[int] = None,
    rule_matches: int = 0,
    ai_verified: int = 0,
    exceptions: int = 0,
    ai_correct: Optional[int] = None,
    ai_total: Optional[int] = None,
    processing_time_seconds: float = 14.5,
) -> EvaluationMetrics:
    """
    Computes standard reconciliation evaluation metrics matching 07-Evaluation-Plan.md.
    Delegates to canonical compute_batch_metrics service.
    """
    res = compute_batch_metrics(
        total_records=total_records,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        rule_matches=rule_matches,
        ai_verified=ai_verified,
        exceptions=exceptions,
        ai_correct=ai_correct,
        ai_total=ai_total,
        processing_time_seconds=processing_time_seconds,
    )
    return EvaluationMetrics(
        total_records=res.total_records,
        matched_count=res.matched_count,
        rule_matches_count=res.rule_matches_count,
        ai_verified_count=res.ai_verified_count,
        exceptions_count=res.exceptions_count,
        match_rate=res.match_rate,
        precision=res.precision,
        recall=res.recall,
        true_positives=res.true_positives,
        false_positives=res.false_positives,
        false_negatives=res.false_negatives,
        ai_verification_accuracy=res.ai_accuracy,
        manual_hours_saved=res.manual_hours_saved,
        processing_time_seconds=res.processing_time_seconds,
    )


def evaluate_cross_merchant(
    base_dir: str = "backend/synthetic_data/merchants",
) -> CrossMerchantEvaluationResult:
    """
    Evaluates the entire schema-agnostic ReconPilot pipeline across all merchant profiles:
    1. Schema detection & column mapping
    2. Data normalization (dirty currencies, dates, references)
    3. Configurable rule engine matching
    4. AI verification on residuals
    5. Scoring against ground truth per merchant profile
    """
    from backend.parser import SmartCSVParser
    from backend.normalizer import normalize_dataframe
    from backend.rules import apply_rules_in_order, find_duplicate_order_ids
    from backend.ai.engine import verify_discrepancy
    from backend.synthetic_data.merchant_archetypes import MERCHANT_ARCHETYPES
    from backend.config.fee_rules import load_fee_config

    merchant_reports: Dict[str, MerchantEvaluationReport] = {}
    total_records_all = 0
    total_tp_all = 0
    total_fp_all = 0
    total_fn_all = 0
    total_ai_correct_all = 0
    total_ai_total_all = 0
    total_time_all = 0.0

    for m_type, profile in MERCHANT_ARCHETYPES.items():
        m_dir = os.path.join(base_dir, m_type)
        inv_path = os.path.join(m_dir, "invoices.csv")
        set_path = os.path.join(m_dir, "settlements.csv")
        bnk_path = os.path.join(m_dir, "bank_statements.csv")
        gt_path = os.path.join(m_dir, "ground_truth.json")

        if not (os.path.exists(inv_path) and os.path.exists(set_path) and os.path.exists(gt_path)):
            continue

        start_t = time.time()

        # 1. Smart Parse (Auto Schema Mapping)
        inv_df, inv_map = SmartCSVParser("invoice").parse(inv_path)
        set_df, set_map = SmartCSVParser("settlement").parse(set_path)
        bnk_df, bnk_map = SmartCSVParser("bank").parse(bnk_path)

        # 2. Normalize
        inv_recs = normalize_dataframe(inv_df, "invoice")
        set_recs = normalize_dataframe(set_df, "settlement")
        bnk_recs = normalize_dataframe(bnk_df, "bank")

        inv_by_order = {r.order_id: r for r in inv_recs if r.order_id}
        bank_by_utr = {r.reference_number: r for r in bnk_recs if r.reference_number}
        duplicates = find_duplicate_order_ids(inv_recs)

        with open(gt_path, "r", encoding="utf-8") as f:
            gt_data = json.load(f)
        gt_by_order = {item["order_id"]: item for item in gt_data}

        rule_matches = 0
        ai_verified = 0
        exceptions = 0
        tp = 0
        fp = 0
        fn = 0
        ai_correct = 0
        ai_total = 0

        # 3. Match & Verify using merchant's fee config
        for settle in set_recs:
            inv = inv_by_order.get(settle.order_id)
            bank = bank_by_utr.get(settle.reference_number)
            gt_item = gt_by_order.get(settle.order_id, {})
            expected_res = gt_item.get("expected_resolution")

            if len(bnk_recs) > 0 and bank is None:
                is_rule_match = False
            else:
                rule_res = apply_rules_in_order(
                    invoice=inv,
                    settlement=settle,
                    bank=bank,
                    duplicate_order_ids=duplicates,
                    fee_config=load_fee_config(m_type),
                )
                is_rule_match = rule_res.is_matched

            if is_rule_match:
                rule_matches += 1
                if expected_res in ("rule", "exact", "fee_deduction", "gst_deduction", "tds_deduction"):
                    tp += 1
                else:
                    fp += 1
            else:
                # Ambiguous miss -> AI verification
                ai_res = verify_discrepancy(
                    invoice=inv,
                    settlement=settle,
                    bank=bank,
                    fee_schedule={"merchant_type": m_type},
                )
                if ai_res.is_validated and not ai_res.requires_human_review:
                    ai_verified += 1
                    ai_total += 1
                    if expected_res == "ai":
                        tp += 1
                        ai_correct += 1
                    else:
                        fp += 1
                else:
                    exceptions += 1
                    if expected_res == "ai":
                        ai_total += 1
                        fn += 1
                    elif expected_res == "exception":
                        pass  # Correctly routed to exceptions

        elapsed = time.time() - start_t
        total_time_all += elapsed

        m_total = len(set_recs)
        total_records_all += m_total
        total_tp_all += tp
        total_fp_all += fp
        total_fn_all += fn
        total_ai_correct_all += ai_correct
        total_ai_total_all += ai_total

        m_matched = tp + fp
        m_rate = (m_matched / m_total * 100.0) if m_total > 0 else 0.0
        m_prec = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else 100.0
        m_rec = (tp / (tp + fn) * 100.0) if (tp + fn) > 0 else 100.0
        m_ai_acc = (ai_correct / ai_total * 100.0) if ai_total > 0 else 100.0

        merchant_reports[m_type] = MerchantEvaluationReport(
            merchant_type=m_type,
            display_name=profile.display_name,
            total_records=m_total,
            rule_matches=rule_matches,
            ai_verified=ai_verified,
            exceptions=exceptions,
            match_rate=round(m_rate, 2),
            precision=round(m_prec, 2),
            recall=round(m_rec, 2),
            ai_accuracy=round(m_ai_acc, 2),
            processing_time_seconds=round(elapsed, 2),
            schema_mapping_successful=(inv_map.is_valid and set_map.is_valid and bnk_map.is_valid),
        )

    agg_matched = total_tp_all + total_fp_all
    agg_rate = (agg_matched / total_records_all * 100.0) if total_records_all > 0 else 0.0
    agg_prec = (total_tp_all / (total_tp_all + total_fp_all) * 100.0) if (total_tp_all + total_fp_all) > 0 else 100.0
    agg_rec = (total_tp_all / (total_tp_all + total_fn_all) * 100.0) if (total_tp_all + total_fn_all) > 0 else 100.0
    agg_ai_acc = (total_ai_correct_all / total_ai_total_all * 100.0) if total_ai_total_all > 0 else 100.0

    manual_minutes_baseline = total_records_all * 3.0
    total_exceptions = sum(r.exceptions for r in merchant_reports.values())
    residual_review_minutes = total_exceptions * 3.0 + (total_time_all / 60.0)
    manual_hours_saved = max(0.0, (manual_minutes_baseline - residual_review_minutes) / 60.0)

    return CrossMerchantEvaluationResult(
        total_merchants=len(merchant_reports),
        total_records_evaluated=total_records_all,
        aggregate_match_rate=round(agg_rate, 2),
        aggregate_precision=round(agg_prec, 2),
        aggregate_recall=round(agg_rec, 2),
        aggregate_ai_accuracy=round(agg_ai_acc, 2),
        total_processing_time_seconds=round(total_time_all, 2),
        total_manual_hours_saved=round(manual_hours_saved, 2),
        merchant_reports=merchant_reports,
    )

