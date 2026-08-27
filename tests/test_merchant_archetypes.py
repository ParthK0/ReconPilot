"""
tests/test_merchant_archetypes.py
=================================
Tests for the 10 industry merchant archetypes in ReconPilot 2.0.
"""

import pytest
from backend.synthetic_data.merchant_archetypes import MERCHANT_ARCHETYPES, get_archetype
from backend.config.fee_rules import load_fee_config
from backend.synthetic_data.generator import generate_merchant_dataset


def test_all_10_archetypes_registered():
    expected_types = {
        "restaurant",
        "marketplace",
        "saas",
        "travel",
        "healthcare",
        "retail",
        "gaming",
        "education",
        "logistics",
        "enterprise",
    }
    assert set(MERCHANT_ARCHETYPES.keys()) == expected_types
    for m_type in expected_types:
        archetype = get_archetype(m_type)
        assert archetype.merchant_type == m_type
        assert len(archetype.invoice_columns) >= 5
        assert len(archetype.settlement_columns) >= 5
        assert len(archetype.bank_columns) >= 5
        assert archetype.fee_config_name != ""


def test_merchant_dataset_generation_all_archetypes():
    for m_type in MERCHANT_ARCHETYPES.keys():
        inv, set_rows, bnk_rows, gt = generate_merchant_dataset(m_type, total_count=20, seed=101)
        assert len(inv) >= 20
        assert len(set_rows) == 20
        assert len(bnk_rows) == 20
        assert len(gt) == 20
        
        # Verify ground truth schema
        for item in gt:
            assert "scenario_id" in item
            assert "merchant_type" in item
            assert item["merchant_type"] == m_type
            assert "expected_resolution" in item
            assert item["expected_resolution"] in ("rule", "ai", "exception")


def test_fee_configs_load_for_all_archetypes():
    for m_type in MERCHANT_ARCHETYPES.keys():
        cfg = load_fee_config(m_type)
        assert cfg is not None
        assert cfg.mdr >= 0
        assert cfg.gst >= 0
        assert cfg.tds >= 0
