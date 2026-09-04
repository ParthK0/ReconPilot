"""
tests/test_merchant_archetypes.py
=================================
Tests for the 10 industry merchant archetypes in ReconPilot 2.0.
"""

from datetime import date
from decimal import Decimal
import pytest
from backend.synthetic_data.merchant_archetypes import MERCHANT_ARCHETYPES, get_archetype
from backend.config.fee_rules import load_fee_config
from backend.synthetic_data.generator import generate_merchant_dataset
from backend.evaluation.evaluator import evaluate_cross_merchant
from backend.rules.rule_engine import match_fee_gst_tds_adjusted_amount
from backend.normalizer.normalizer import NormalizedRecord


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
        "cross_border_saas",
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


def test_cross_border_archetype_registration():
    arch = get_archetype("cross_border_saas")
    assert arch.merchant_type == "cross_border_saas"
    assert "CloudMatrix Global" in arch.display_name
    assert "fx_markup_fee" in arch.settlement_columns.values()


def test_rule_matching_with_merchant_fee_config():
    # Marketplace: 1.8% MDR, 18% GST on MDR = 0.324%, TDS 1.0%
    marketplace_cfg = load_fee_config("marketplace")
    inv_amount = Decimal("10000.00")
    mdr = Decimal("180.00")  # 1.8% of 10000
    gst = Decimal("32.40")   # 18% of 180
    tds = Decimal("100.00")  # 1.0% of 10000
    net = inv_amount - mdr - gst - tds

    inv = NormalizedRecord(
        source_type="invoice",
        transaction_id="inv-1",
        order_id="ORD-101",
        amount=inv_amount,
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    settle = NormalizedRecord(
        source_type="settlement",
        transaction_id="set-1",
        order_id="ORD-101",
        amount=net,
        txn_date=date(2026, 8, 3),
        status="settled",
        fees=mdr,
        gst=gst,
        tds=tds,
    )

    res = match_fee_gst_tds_adjusted_amount(invoice=inv, settlement=settle, fee_config=marketplace_cfg)
    assert res.is_matched
    assert res.rule_name == "fee_gst_tds_adjusted_amount"


def test_generate_and_evaluate_cross_merchant():
    result = evaluate_cross_merchant()
    assert result.total_merchants >= 5
    assert result.total_records_evaluated >= 500
    assert result.aggregate_match_rate >= 90.0
    assert result.aggregate_precision == 100.0
    assert result.aggregate_recall == 100.0
    for m_type in ("retail", "marketplace", "restaurant", "enterprise"):
        if m_type in result.merchant_reports:
            rep = result.merchant_reports[m_type]
            assert rep.schema_mapping_successful is True
            assert rep.match_rate >= 90.0


