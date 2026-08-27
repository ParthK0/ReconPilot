"""
tests/test_safe_schema.py
=========================
Tests for Safe Schema Mapping & Threshold Gating (>=95% auto, 80-95% suggest, <80% reject).
"""

import pytest
from backend.schema_mapper.mapper import map_schema


def test_safe_schema_exact_match_threshold():
    cols = ["invoice_id", "order_id", "amount", "invoice_date", "customer_name", "status"]
    mapping = map_schema(cols, source_type="invoice")
    assert mapping.is_valid is True
    assert mapping.requires_user_confirmation is False
    assert len(mapping.suggested_mappings) == 0
    assert len(mapping.rejected_mappings) == 0
    for col_res in mapping.column_mappings:
        assert col_res.tier == "auto_map"
        assert col_res.confidence >= 0.95


def test_safe_schema_alias_threshold():
    cols = ["bill_no", "order_number", "gross_amount", "billing_date", "buyer_name", "state"]
    mapping = map_schema(cols, source_type="invoice")
    assert mapping.is_valid is True
    # All are verified dictionary aliases with confidence >= 0.95
    for col_res in mapping.column_mappings:
        assert col_res.tier == "auto_map"
        assert col_res.confidence >= 0.95


def test_safe_schema_unmapped_rejection():
    cols = ["random_gibberish_column_1", "mystery_field_xyz", "amount"]
    mapping = map_schema(cols, source_type="invoice")
    assert mapping.is_valid is False
    assert len(mapping.rejected_mappings) >= 2
    assert mapping.requires_user_confirmation is True
