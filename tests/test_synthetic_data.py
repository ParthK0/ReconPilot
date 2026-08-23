import os
import json
import pandas as pd
import pytest
from decimal import Decimal

from backend.synthetic_data.generator import (
    generate_dataset,
    generate_synthetic_data,
    STANDARD_FEE_RATE,
    STANDARD_GST_RATE,
    STANDARD_TDS_RATE,
)
from backend.parser.csv_parser import parse_csv_content, validate_csv_schema, EXPECTED_COLUMNS
from backend.normalizer.normalizer import normalize_dataframe


def test_generator_produces_all_categories_at_least_once():
    """
    Asserts that the generator produces all 9 categories from 08-Roadmap.md Phase 1 at least once:
    1. Exact matches (exact_match)
    2. Fee deductions (fee_deduction)
    3. GST deductions (gst_deduction)
    4. TDS deductions (tds_deduction)
    5. Non-standard one-off adjustments (non_standard_adjustment / AI verification)
    6. Delayed settlements (delayed_settlement)
    7. Refunds (refund)
    8. Duplicate invoices (duplicate_invoice)
    9. Missing bank credits (missing_bank_credit)
    10. Genuine unknowns (unknown)
    """
    invoices, settlements, bank_rows, ground_truth = generate_dataset()

    categories_present = {item["category"] for item in ground_truth}

    required_roadmap_categories = [
        "exact_match",
        "fee_deduction",
        "gst_deduction",
        "tds_deduction",
        "non_standard_adjustment",
        "delayed_settlement",
        "refund",
        "duplicate_invoice",
        "missing_bank_credit",
        "unknown",
    ]

    for cat in required_roadmap_categories:
        assert cat in categories_present, f"Missing required category in ground truth: {cat}"
        count = sum(1 for item in ground_truth if item["category"] == cat)
        assert count >= 1, f"Category '{cat}' must appear at least once (found {count})"


def test_dataset_row_counts_and_structure():
    """
    Asserts that exactly 100 invoices, 100 settlements, and 100 bank rows are produced.
    """
    invoices, settlements, bank_rows, ground_truth = generate_dataset()

    assert len(invoices) == 100, f"Expected exactly 100 invoice rows, got {len(invoices)}"
    assert len(settlements) == 100, f"Expected exactly 100 settlement rows, got {len(settlements)}"
    assert len(bank_rows) == 100, f"Expected exactly 100 bank rows, got {len(bank_rows)}"
    assert len(ground_truth) == 100, f"Expected exactly 100 ground truth items, got {len(ground_truth)}"


def test_non_standard_adjustments_count():
    """
    Asserts that non-standard one-off adjustments (meant for AI verification)
    are a small handful between 5 and 8 records.
    """
    invoices, settlements, bank_rows, ground_truth = generate_dataset()
    ai_records = [item for item in ground_truth if item["category"] == "non_standard_adjustment"]

    assert 5 <= len(ai_records) <= 8, f"Expected 5-8 non-standard AI adjustment records, got {len(ai_records)}"
    
    # Assert they have expected AI resolution attributes
    for item in ai_records:
        assert item["expected_resolution"] == "ai"
        assert item.get("likely_reason") == "processing_fee"
        assert "evidence_field" in item
        assert "difference_amount" in item


def test_generated_csv_files_and_ground_truth_saving(tmp_path):
    """
    Tests that generate_synthetic_data writes valid CSVs and ground truth JSON/CSV.
    """
    out_dir = str(tmp_path / "synthetic_test")
    file_map = generate_synthetic_data(output_dir=out_dir)

    for key, path in file_map.items():
        assert os.path.exists(path), f"Generated file does not exist: {path}"
        assert os.path.getsize(path) > 0, f"Generated file is empty: {path}"

    # Verify CSV rows in saved files
    df_inv = pd.read_csv(file_map["invoices_csv"])
    df_set = pd.read_csv(file_map["settlements_csv"])
    df_bnk = pd.read_csv(file_map["bank_statements_csv"])

    assert len(df_inv) == 100
    assert len(df_set) == 100
    assert len(df_bnk) == 100

    # Verify ground truth JSON structure
    with open(file_map["ground_truth_json"], "r", encoding="utf-8") as f:
        gt_data = json.load(f)
    assert len(gt_data) == 100


def test_parser_and_normalizer_roundtrip():
    """
    Tests that generated CSVs strictly pass CSV parser schema validation and
    normalize into NormalizedRecord models without data loss.
    """
    invoices, settlements, bank_rows, ground_truth = generate_dataset()

    df_inv = pd.DataFrame(invoices)
    df_set = pd.DataFrame(settlements)
    df_bnk = pd.DataFrame(bank_rows)

    validate_csv_schema(df_inv, "invoice")
    validate_csv_schema(df_set, "settlement")
    validate_csv_schema(df_bnk, "bank")

    norm_inv = normalize_dataframe(df_inv, "invoice")
    norm_set = normalize_dataframe(df_set, "settlement")
    norm_bnk = normalize_dataframe(df_bnk, "bank")

    assert len(norm_inv) == 100
    assert len(norm_set) == 100
    assert len(norm_bnk) == 100

    # Spot check normalization fields
    assert norm_inv[0].source_type == "invoice"
    assert norm_inv[0].amount > Decimal("0.00")
    assert norm_set[0].source_type == "settlement"
    assert norm_bnk[0].source_type == "bank"
