import os
import json
from decimal import Decimal
from datetime import timedelta, date
import pytest

from backend.parser import InvoiceParser, SettlementParser, BankStatementParser
from backend.normalizer import normalize_dataframe
from backend.normalizer.normalizer import NormalizedRecord
from backend.rules import (
    match_exact_order_id,
    match_exact_reference_number,
    match_exact_amount,
    match_settlement_date_window,
    match_fee_gst_tds_adjusted_amount,
    match_tolerance_amount,
    match_fx_spread_tolerance,
    apply_rules_in_order,
    find_duplicate_order_ids,
)

SYNTHETIC_DATA_DIR = "backend/synthetic_data"


@pytest.fixture(scope="module")
def loaded_dataset():
    """Loads and normalizes the synthetic test fixture files and ground truth labels."""
    inv_df = InvoiceParser().parse(os.path.join(SYNTHETIC_DATA_DIR, "invoices.csv"))
    set_df = SettlementParser().parse(os.path.join(SYNTHETIC_DATA_DIR, "settlements.csv"))
    bnk_df = BankStatementParser().parse(os.path.join(SYNTHETIC_DATA_DIR, "bank_statements.csv"))

    invoices = normalize_dataframe(inv_df, "invoice")
    settlements = normalize_dataframe(set_df, "settlement")
    banks = normalize_dataframe(bnk_df, "bank")

    with open(os.path.join(SYNTHETIC_DATA_DIR, "ground_truth.json"), "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    inv_by_id = {rec.transaction_id: rec for rec in invoices}
    set_by_id = {rec.transaction_id: rec for rec in settlements}
    bnk_by_id = {rec.transaction_id: rec for rec in banks}

    return {
        "invoices": inv_by_id,
        "settlements": set_by_id,
        "banks": bnk_by_id,
        "ground_truth": ground_truth,
        "invoices_list": invoices,
        "settlements_list": settlements,
        "banks_list": banks,
        "duplicates": find_duplicate_order_ids(invoices),
    }


# ---------------------------------------------------------------------------
# 1. Rule 1: Exact Order ID Match
# ---------------------------------------------------------------------------

def test_rule_exact_order_id(loaded_dataset):
    exact_gt = [gt for gt in loaded_dataset["ground_truth"] if gt["category"] == "exact_match"]
    sample_gt = exact_gt[0]
    inv = loaded_dataset["invoices"][sample_gt["invoice_id"]]
    settle = loaded_dataset["settlements"][sample_gt["settlement_id"]]
    bank = loaded_dataset["banks"][sample_gt["bank_txn_id"]]

    result = match_exact_order_id(invoice=inv, settlement=settle, bank=bank)
    assert result.is_matched is True
    assert result.rule_name == "exact_order_id"
    assert result.confidence == Decimal("100.00")

    # Mismatched order ID should fail
    mismatched = settle.model_copy(update={"order_id": "ORD-MISMATCH-9999"})
    assert match_exact_order_id(invoice=inv, settlement=mismatched).is_matched is False


# ---------------------------------------------------------------------------
# 2. Rule 2: Exact Reference Number / UTR Match
# ---------------------------------------------------------------------------

def test_rule_exact_reference_number(loaded_dataset):
    exact_gt = [gt for gt in loaded_dataset["ground_truth"] if gt["category"] == "exact_match"]
    sample_gt = exact_gt[0]
    settle = loaded_dataset["settlements"][sample_gt["settlement_id"]]
    bank = loaded_dataset["banks"][sample_gt["bank_txn_id"]]

    result = match_exact_reference_number(settlement=settle, bank=bank)
    assert result.is_matched is True
    assert result.rule_name == "exact_reference_number"
    assert result.confidence == Decimal("100.00")

    # Mismatched UTR should fail
    mismatched = bank.model_copy(update={"reference_number": "UTR-WRONG"})
    assert match_exact_reference_number(settlement=settle, bank=mismatched).is_matched is False


# ---------------------------------------------------------------------------
# 3. Rule 3: Exact Amount Match
# ---------------------------------------------------------------------------

def test_rule_exact_amount(loaded_dataset):
    exact_gt = [gt for gt in loaded_dataset["ground_truth"] if gt["category"] == "exact_match"]
    sample_gt = exact_gt[0]
    inv = loaded_dataset["invoices"][sample_gt["invoice_id"]].model_copy(update={"order_id": None})
    settle = loaded_dataset["settlements"][sample_gt["settlement_id"]].model_copy(update={"order_id": None})

    result = match_exact_amount(invoice=inv, settlement=settle)
    assert result.is_matched is True
    assert result.rule_name == "exact_amount"
    assert result.confidence == Decimal("100.00")

    # Discrepant amounts should fail
    diff = settle.model_copy(update={"amount": Decimal("12345.67")})
    assert match_exact_amount(invoice=inv, settlement=diff).is_matched is False


# ---------------------------------------------------------------------------
# 4. Rule 4: Settlement-Date Window Match
# ---------------------------------------------------------------------------

def test_rule_settlement_date_window(loaded_dataset):
    exact_gt = [gt for gt in loaded_dataset["ground_truth"] if gt["category"] == "exact_match"][0]
    inv = loaded_dataset["invoices"][exact_gt["invoice_id"]]
    settle = loaded_dataset["settlements"][exact_gt["settlement_id"]]

    res_exact = match_settlement_date_window(invoice=inv, settlement=settle, max_days=2)
    assert res_exact.is_matched is True
    assert res_exact.rule_name == "settlement_date_window"

    # Delayed settlement (T+6 days) should fail T+2 window
    delayed_gt = [gt for gt in loaded_dataset["ground_truth"] if gt["category"] == "delayed_settlement"][0]
    inv_del = loaded_dataset["invoices"][delayed_gt["invoice_id"]]
    settle_del = loaded_dataset["settlements"][delayed_gt["settlement_id"]]

    assert match_settlement_date_window(invoice=inv_del, settlement=settle_del, max_days=2).is_matched is False

    # Settled transaction with T+5 days delay: fails strict T+2 Rule 3, but matches Rule 4 extended window (T+7)
    inv_t5 = inv.model_copy()
    settle_t5 = settle.model_copy(update={"txn_date": inv.txn_date + timedelta(days=5)})
    assert match_exact_amount(invoice=inv_t5, settlement=settle_t5, max_days=2).is_matched is False

    res_del = match_settlement_date_window(invoice=inv_t5, settlement=settle_t5, max_days=7)
    assert res_del.is_matched is True
    assert res_del.confidence == Decimal("98.00")
    assert res_del.rule_name == "settlement_date_window"


# ---------------------------------------------------------------------------
# 5. Rule 5: Fee / GST / TDS Adjusted Amount Match
# ---------------------------------------------------------------------------

def test_rule_fee_gst_tds_adjusted_amount_combination_naming(loaded_dataset):
    """
    Asserts that combinations (Fee, Fee+GST, Fee+GST+TDS) match at 100% confidence
    and explicitly name all charges in the rule name and breakdown.
    """
    # 1. Fee Only Record
    fee_gt = [gt for gt in loaded_dataset["ground_truth"] if gt["category"] == "fee_deduction"][0]
    inv_fee = loaded_dataset["invoices"][fee_gt["invoice_id"]]
    set_fee = loaded_dataset["settlements"][fee_gt["settlement_id"]]

    res_fee = match_fee_gst_tds_adjusted_amount(invoice=inv_fee, settlement=set_fee)
    assert res_fee.is_matched is True
    assert res_fee.rule_name == "fee_gst_tds_adjusted_amount"
    assert res_fee.confidence == Decimal("100.00")
    assert [c.charge for c in res_fee.charge_breakdown.charges] == ["fees"]
    assert "fees" in res_fee.notes

    # 2. Fee + GST Record (Combination test)
    gst_gt = [gt for gt in loaded_dataset["ground_truth"] if gt["category"] == "gst_deduction"][0]
    inv_gst = loaded_dataset["invoices"][gst_gt["invoice_id"]]
    set_gst = loaded_dataset["settlements"][gst_gt["settlement_id"]]

    res_gst = match_fee_gst_tds_adjusted_amount(invoice=inv_gst, settlement=set_gst)
    assert res_gst.is_matched is True
    assert res_gst.rule_name == "fee_gst_tds_adjusted_amount"
    assert [c.charge for c in res_gst.charge_breakdown.charges] == ["fees", "gst"]
    assert "fees" in res_gst.notes and "gst" in res_gst.notes

    # 3. Fee + GST + TDS Record (Combination test)
    tds_gt = [gt for gt in loaded_dataset["ground_truth"] if gt["category"] == "tds_deduction"][0]
    inv_tds = loaded_dataset["invoices"][tds_gt["invoice_id"]]
    set_tds = loaded_dataset["settlements"][tds_gt["settlement_id"]]

    res_tds = match_fee_gst_tds_adjusted_amount(invoice=inv_tds, settlement=set_tds)
    assert res_tds.is_matched is True
    assert res_tds.rule_name == "fee_gst_tds_adjusted_amount"
    assert [c.charge for c in res_tds.charge_breakdown.charges] == ["fees", "gst", "tds"]
    assert "fees" in res_tds.notes and "gst" in res_tds.notes and "tds" in res_tds.notes


def test_adjusted_amount_rule_rejects_non_standard_and_corrupt(loaded_dataset):
    """
    Asserts that:
    1. A non-standard one-off adjustment (e.g. Rs 30 fee on Rs 12,000) returns is_matched=False.
    2. A deliberately corrupted/wrong record returns is_matched=False.
    """
    # 1. Non-standard one-off record (e.g. Rs 30 fee on Rs 12,000)
    ai_gt = [gt for gt in loaded_dataset["ground_truth"] if gt["category"] == "non_standard_adjustment"][0]
    inv_ai = loaded_dataset["invoices"][ai_gt["invoice_id"]]
    set_ai = settlements_gt = loaded_dataset["settlements"][ai_gt["settlement_id"]]

    res_ai = match_fee_gst_tds_adjusted_amount(invoice=inv_ai, settlement=set_ai)
    assert res_ai.is_matched is False, "Non-standard one-off adjustment must not match standard rule"

    # 2. Deliberately wrong record (random unprovable delta)
    corrupt_settle = set_ai.model_copy(update={"amount": Decimal("1111.11"), "fees": Decimal("99.99")})
    res_corrupt = match_fee_gst_tds_adjusted_amount(invoice=inv_ai, settlement=corrupt_settle)
    assert res_corrupt.is_matched is False, "Corrupted record must return not-matched"


# ---------------------------------------------------------------------------
# 6. Full Batch Rule Engine Pipeline Breakdown
# ---------------------------------------------------------------------------

def test_full_batch_rule_engine_breakdown(loaded_dataset):
    """
    Runs the ordered rule engine against the whole 100-scenario synthetic dataset
    and asserts match counts match the expected funnel: ~85-90 matched, ~10-15 unmatched.
    """
    rule_counts = {}
    unmatched_count = 0
    duplicates = loaded_dataset["duplicates"]

    for gt in loaded_dataset["ground_truth"]:
        inv = loaded_dataset["invoices"][gt["invoice_id"]]
        settle = loaded_dataset["settlements"][gt["settlement_id"]]
        bank = loaded_dataset["banks"][gt["bank_txn_id"]]

        res = apply_rules_in_order(
            invoice=inv,
            settlement=settle,
            bank=bank,
            duplicate_order_ids=duplicates,
        )
        if res.is_matched:
            rule_counts[res.rule_name] = rule_counts.get(res.rule_name, 0) + 1
        else:
            unmatched_count += 1

    total_matched = sum(rule_counts.values())
    total_records = len(loaded_dataset["ground_truth"])

    assert total_records == 100
    assert 85 <= total_matched <= 90, f"Expected 85-90 rule matches, got {total_matched}"
    assert 10 <= unmatched_count <= 15, f"Expected 10-15 unmatched records for Phase 4, got {unmatched_count}"
    assert total_matched + unmatched_count == 100
    assert total_matched == 86
    assert unmatched_count == 14


# ---------------------------------------------------------------------------
# 7. Rule 6: Tolerance Amount Match
# ---------------------------------------------------------------------------

def test_tolerance_match_within_2_rupees():
    """Variance of Rs 1.50 with matching order ID must match Rule 6 at 95% confidence."""
    inv = NormalizedRecord(
        id="inv-1",
        batch_id="b-1",
        source_type="invoice",
        transaction_id="TXN-1",
        order_id="ORD-TOL-101",
        amount=Decimal("5000.00"),
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    settle = NormalizedRecord(
        id="set-1",
        batch_id="b-1",
        source_type="settlement",
        transaction_id="SET-1",
        order_id="ORD-TOL-101",
        amount=Decimal("4998.50"),  # Rs 1.50 delta
        txn_date=date(2026, 8, 2),
        status="settled",
    )

    res = match_tolerance_amount(invoice=inv, settlement=settle)
    assert res.is_matched is True
    assert res.rule_name == "tolerance_amount_match"
    assert res.confidence == Decimal("95.00")

    # Verify pipeline order
    pipe_res = apply_rules_in_order(invoice=inv, settlement=settle)
    assert pipe_res.is_matched is True
    assert pipe_res.rule_name == "tolerance_amount_match"


def test_tolerance_match_rejects_exceeding_tolerance():
    """Variance of Rs 5.00 exceeds Rs 2.00 tolerance and must fall through."""
    inv = NormalizedRecord(
        id="inv-2",
        batch_id="b-1",
        source_type="invoice",
        transaction_id="TXN-2",
        order_id="ORD-TOL-102",
        amount=Decimal("5000.00"),
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    settle = NormalizedRecord(
        id="set-2",
        batch_id="b-1",
        source_type="settlement",
        transaction_id="SET-2",
        order_id="ORD-TOL-102",
        amount=Decimal("4995.00"),  # Rs 5.00 delta
        txn_date=date(2026, 8, 2),
        status="settled",
    )

    res = match_tolerance_amount(invoice=inv, settlement=settle)
    assert res.is_matched is False


# ---------------------------------------------------------------------------
# 8. International FX Spread Corridor Match
# ---------------------------------------------------------------------------

def test_fx_spread_tolerance_matching():
    inv = NormalizedRecord(
        id="inv_fx_01",
        batch_id="batch_intl",
        source_type="invoice",
        transaction_id="TXN_USD_100",
        order_id="ORD_INTL_001",
        amount=Decimal("10000.00"),
        currency="INR",
        txn_date=date(2026, 8, 1),
        status="paid",
    )
    settle = NormalizedRecord(
        id="set_fx_01",
        batch_id="batch_intl",
        source_type="settlement",
        transaction_id="SET_INR_100",
        order_id="ORD_INTL_001",
        amount=Decimal("9750.00"),
        currency="INR",
        txn_date=date(2026, 8, 3),
        status="settled",
    )

    res = match_fx_spread_tolerance(invoice=inv, settlement=settle)
    assert res.is_matched is True
    assert res.rule_name == "fx_spread_tolerance"
    assert res.confidence == Decimal("94.00")
    assert "international FX spread corridor" in res.notes

