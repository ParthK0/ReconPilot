import pandas as pd
import pytest

from backend.schema_mapper.mapper import SchemaMapper, default_schema_mapper, map_schema, remap_dataframe
from backend.parser.csv_parser import SmartCSVParser, SchemaValidationError


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
