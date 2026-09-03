import pandas as pd
import pytest

from backend.schema_mapper.mapper import SchemaMapper, default_schema_mapper, map_schema, remap_dataframe
from backend.parser.csv_parser import SmartCSVParser, SchemaValidationError


@pytest.fixture(autouse=True)
def force_offline_mode(monkeypatch):
    monkeypatch.setenv("RECONPILOT_AI_MODE", "offline")


def test_schema_mapper_exact_matching():
    cols = ["invoice_id", "order_id", "amount", "invoice_date", "customer_name", "status"]
    mapping = map_schema(cols, "invoice")
    assert mapping.is_valid
    assert len(mapping.missing_required) == 0
    assert all(m.method == "exact" for m in mapping.column_mappings)


def test_schema_mapper_alias_matching():
    # Columns from a custom merchant format
    cols = ["inv_id", "order_no", "invoice_value", "bill_date", "customer", "state"]
    mapping = map_schema(cols, "invoice")
    assert mapping.is_valid
    assert len(mapping.missing_required) == 0
    assert mapping.rename_dict["invoice_value"] == "amount"
    assert mapping.rename_dict["inv_id"] == "invoice_id"
    assert mapping.rename_dict["bill_date"] == "invoice_date"


def test_schema_mapper_settlement_aliases():
    cols = ["payout_id", "order_number", "settlement_amount", "settled_at", "bank_ref_no", "status", "processing_fees", "tax_amount", "withholding_tax"]
    mapping = map_schema(cols, "settlement")
    assert mapping.is_valid
    assert mapping.rename_dict["processing_fees"] == "fees"
    assert mapping.rename_dict["tax_amount"] == "gst"
    assert mapping.rename_dict["withholding_tax"] == "tds"


def test_smart_csv_parser_with_dirty_columns():
    csv_data = """invoice_number,order_no,gross_value,bill_date,customer_name,status
INV-01,ORD-01,12000.00,2026-08-01,Alice,paid
INV-02,ORD-02,15000.00,2026-08-02,Bob,paid
"""
    parser = SmartCSVParser("invoice")
    df, mapping = parser.parse(csv_data)
    assert mapping.is_valid
    assert "amount" in df.columns
    assert "invoice_id" in df.columns
    assert "order_id" in df.columns
    assert "invoice_date" in df.columns
    assert len(df) == 2



def test_schema_mapper_ambiguity_handling():
    # Test A: Both "order_number" and "order_no" are plausible candidates for canonical "order_id"
    cols = ["order_number", "order_no", "invoice_id", "amount", "invoice_date", "customer_name", "status"]
    mapping = map_schema(cols, "invoice")
    assert mapping.is_valid is False
    assert mapping.requires_user_confirmation is True
    # Neither should be silently force-picked into rename_dict
    assert "order_number" not in mapping.rename_dict
    assert "order_no" not in mapping.rename_dict
    assert "order_id" not in mapping.rename_dict.values()
    # Both appear in suggested_mappings
    assert "order_id" in mapping.suggested_mappings
    assert "order_number" in mapping.suggested_mappings["order_id"]["candidates"]
    assert "order_no" in mapping.suggested_mappings["order_id"]["candidates"]
    # Both appear in column_mappings
    mapped_orig_names = [m.original_name for m in mapping.column_mappings]
    assert "order_number" in mapped_orig_names
    assert "order_no" in mapped_orig_names


def test_schema_mapper_sub_threshold_heuristic_not_auto_accepted():
    # Test B: Only candidate for "amount" is a heuristic substring match (confidence 0.85)
    cols = ["invoice_id", "order_id", "custom_payment_amt_col", "invoice_date", "customer_name", "status"]
    mapping = map_schema(cols, "invoice")
    assert mapping.is_valid is False
    assert mapping.requires_user_confirmation is True
    assert "custom_payment_amt_col" not in mapping.rename_dict
    assert "amount" not in mapping.rename_dict.values()
    assert "amount" in mapping.suggested_mappings
    assert mapping.suggested_mappings["amount"]["source_column"] == "custom_payment_amt_col"
    assert mapping.suggested_mappings["amount"]["confidence"] == 0.85
    assert mapping.suggested_mappings["amount"]["method"] == "heuristic"


def test_smart_csv_parser_genuine_failure_path():
    # Test C: Headers that cannot match any rule, alias, AI, or heuristic
    csv_data = """col_a,col_b,field_1,field_2
val1,val2,val3,val4
"""
    parser = SmartCSVParser("invoice")
    with pytest.raises(SchemaValidationError) as exc_info:
        parser.parse(csv_data)
    
    err_msg = str(exc_info.value)
    # Assert the exception message names the specific unmapped required fields
    assert "invoice_id" in err_msg
    assert "order_id" in err_msg
    assert "amount" in err_msg
    assert "invoice_date" in err_msg

