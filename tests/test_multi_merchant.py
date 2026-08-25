from decimal import Decimal
import pytest

from backend.config.fee_rules import FeeConfig, load_fee_config
from backend.synthetic_data.merchant_profiles import MERCHANT_PROFILES, get_merchant_profile
from backend.synthetic_data.generator import generate_merchant_dataset, generate_multi_merchant_dataset
from backend.evaluation.evaluator import evaluate_cross_merchant
from backend.rules.rule_engine import match_fee_gst_tds_adjusted_amount
from backend.normalizer.normalizer import NormalizedRecord
from datetime import date


def test_load_fee_config_profiles():
    retail_cfg = load_fee_config("retail")
    assert retail_cfg.merchant_type == "retail"
    assert retail_cfg.mdr == Decimal("2.0")

    marketplace_cfg = load_fee_config("marketplace")
    assert marketplace_cfg.merchant_type == "marketplace"
    assert marketplace_cfg.mdr == Decimal("1.8")
    assert marketplace_cfg.platform_fee == Decimal("0.5")

    enterprise_cfg = load_fee_config("enterprise")
    assert enterprise_cfg.merchant_type == "enterprise"
    assert enterprise_cfg.mdr == Decimal("1.5")


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
    assert result.total_merchants == 5
    assert result.total_records_evaluated == 500
    assert result.aggregate_match_rate >= 90.0
    assert result.aggregate_precision == 100.0
    assert result.aggregate_recall == 100.0
    for m_type in ("retail", "marketplace", "subscription", "restaurant", "enterprise"):
        assert m_type in result.merchant_reports
        rep = result.merchant_reports[m_type]
        assert rep.schema_mapping_successful is True
        assert rep.match_rate >= 90.0
