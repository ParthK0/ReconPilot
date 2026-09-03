"""
backend/synthetic_data/generator.py
===================================
ReconPilot 2.0: Scalable Multi-Merchant Synthetic Dataset & Ground Truth Engine.

Features:
- 10 Industry Verticals: Restaurant, Marketplace, SaaS, Travel, Healthcare, Retail, Gaming, Education, Logistics, Enterprise.
- Scalable Volume: 100 to 10,000+ records on-demand.
- 30+ Realistic Financial Exception Scenarios proportionately injected.
- Automated Ground-Truth Generation (JSON + CSV) on every run.
"""

import csv
import json
import os
import sys

# Ensure repository root is on sys.path for standalone script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Tuple, Optional

from backend.config.fee_rules import FeeConfig, load_fee_config
from backend.synthetic_data.merchant_archetypes import MERCHANT_ARCHETYPES, MerchantArchetype, get_archetype


def round_curr(val: Decimal) -> Decimal:
    """Rounds to 2 decimal places using half-up standard."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Documented standard rate schedule for rule-based resolution (defaults)
STANDARD_FEE_RATE = Decimal("0.02")  # 2.0% standard Razorpay MDR
STANDARD_GST_RATE = Decimal("0.18")  # 18.0% GST on fees
STANDARD_TDS_RATE = Decimal("0.01")  # 1.0% TDS under Section 194O


def _format_currency_val(val: Decimal, style: str) -> str:
    """Formats decimal value into clean or dirty merchant string representation."""
    if style == "rupee_symbol":
        return f"₹{val:,.2f}"
    elif style == "inr_suffix":
        return f"{val:.2f} INR"
    elif style == "rupee_space_commas":
        return f"₹ {val:,.2f}"
    elif style == "usd_symbol":
        return f"${val:,.2f}"
    return f"{val:.2f}"


def _format_date_val(d: date, fmt: str) -> str:
    """Formats date according to merchant archetype pattern."""
    return d.strftime(fmt)


def generate_dataset() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generates exactly 100 canonical invoices, 100 settlements, 100 bank statement rows,
    and ground truth labels matching the standard benchmark suite.
    """
    invoices: List[Dict[str, Any]] = []
    settlements: List[Dict[str, Any]] = []
    bank_rows: List[Dict[str, Any]] = []
    ground_truth: List[Dict[str, Any]] = []

    base_date = date(2026, 8, 1)
    running_balance = Decimal("500000.00")
    record_idx = 1

    # 1. Exact matches (70 records)
    for i in range(70):
        order_id = f"ORD-2026-EX-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"
        amount = round_curr(Decimal("1000.00") + Decimal(str(i * 125.50)))
        txn_date = base_date + timedelta(days=(i % 15))
        settle_date = txn_date + timedelta(days=1)
        running_balance = round_curr(running_balance + amount)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "settlement_date": settle_date.isoformat(),
            "reference_number": utr,
            "status": "settled",
            "fees": "0.00",
            "gst": "0.00",
            "tds": "0.00",
        })
        bank_rows.append({
            "bank_txn_id": bnk_id,
            "txn_date": settle_date.isoformat(),
            "description": f"ACH CR RAZORPAY SETTLEMENT {utr}",
            "reference_number": utr,
            "amount": f"{amount:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "exact_match",
            "expected_resolution": "rule",
            "expected_rule": "exact_order_id",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{amount:.2f}",
            "bank_amount": f"{amount:.2f}",
            "explanation": "Exact match across order ID, UTR, and amount.",
        })
        record_idx += 1

    # 2. Fee deductions (8 records)
    for i in range(8):
        order_id = f"ORD-2026-FEE-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"
        amount = round_curr(Decimal("2000.00") + Decimal(str(i * 250.00)))
        fees = round_curr(amount * STANDARD_FEE_RATE)
        net = round_curr(amount - fees)
        txn_date = base_date + timedelta(days=(i % 10))
        settle_date = txn_date + timedelta(days=2)
        running_balance = round_curr(running_balance + net)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{net:.2f}",
            "settlement_date": settle_date.isoformat(),
            "reference_number": utr,
            "status": "settled",
            "fees": f"{fees:.2f}",
            "gst": "0.00",
            "tds": "0.00",
        })
        bank_rows.append({
            "bank_txn_id": bnk_id,
            "txn_date": settle_date.isoformat(),
            "description": f"ACH CR RAZORPAY SETTLEMENT {utr}",
            "reference_number": utr,
            "amount": f"{net:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "fee_deduction",
            "expected_resolution": "rule",
            "expected_rule": "fee_gst_tds_adjusted_amount",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{net:.2f}",
            "bank_amount": f"{net:.2f}",
            "explanation": "Standard 2% MDR fee deduction.",
        })
        record_idx += 1

    # 3. GST deductions (5 records)
    for i in range(5):
        order_id = f"ORD-2026-GST-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"
        amount = round_curr(Decimal("5000.00") + Decimal(str(i * 500.00)))
        fees = round_curr(amount * STANDARD_FEE_RATE)
        gst = round_curr(fees * STANDARD_GST_RATE)
        net = round_curr(amount - fees - gst)
        txn_date = base_date + timedelta(days=(i % 8))
        settle_date = txn_date + timedelta(days=2)
        running_balance = round_curr(running_balance + net)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{net:.2f}",
            "settlement_date": settle_date.isoformat(),
            "reference_number": utr,
            "status": "settled",
            "fees": f"{fees:.2f}",
            "gst": f"{gst:.2f}",
            "tds": "0.00",
        })
        bank_rows.append({
            "bank_txn_id": bnk_id,
            "txn_date": settle_date.isoformat(),
            "description": f"ACH CR RAZORPAY SETTLEMENT {utr}",
            "reference_number": utr,
            "amount": f"{net:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "gst_deduction",
            "expected_resolution": "rule",
            "expected_rule": "fee_gst_tds_adjusted_amount",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{net:.2f}",
            "bank_amount": f"{net:.2f}",
            "explanation": "Standard MDR fee + 18% GST deduction.",
        })
        record_idx += 1

    # 4. TDS deductions (3 records)
    for i in range(3):
        order_id = f"ORD-2026-TDS-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"
        amount = round_curr(Decimal("10000.00") + Decimal(str(i * 1000.00)))
        fees = round_curr(amount * STANDARD_FEE_RATE)
        gst = round_curr(fees * STANDARD_GST_RATE)
        tds = round_curr(amount * STANDARD_TDS_RATE)
        net = round_curr(amount - fees - gst - tds)
        txn_date = base_date + timedelta(days=(i % 5))
        settle_date = txn_date + timedelta(days=2)
        running_balance = round_curr(running_balance + net)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{net:.2f}",
            "settlement_date": settle_date.isoformat(),
            "reference_number": utr,
            "status": "settled",
            "fees": f"{fees:.2f}",
            "gst": f"{gst:.2f}",
            "tds": f"{tds:.2f}",
        })
        bank_rows.append({
            "bank_txn_id": bnk_id,
            "txn_date": settle_date.isoformat(),
            "description": f"ACH CR RAZORPAY SETTLEMENT {utr}",
            "reference_number": utr,
            "amount": f"{net:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "tds_deduction",
            "expected_resolution": "rule",
            "expected_rule": "fee_gst_tds_adjusted_amount",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{net:.2f}",
            "bank_amount": f"{net:.2f}",
            "explanation": "Standard MDR fee + GST + 1% Section 194-O TDS.",
        })
        record_idx += 1

    # 5. Non-standard adjustments (6 records)
    ai_presets = [
        (Decimal("12000.00"), Decimal("30.00")),
        (Decimal("25000.00"), Decimal("45.00")),
        (Decimal("18500.00"), Decimal("50.00")),
        (Decimal("8000.00"), Decimal("40.00")),
        (Decimal("15000.00"), Decimal("35.00")),
        (Decimal("30000.00"), Decimal("75.00")),
    ]
    for i in range(6):
        order_id = f"ORD-2026-AI-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"
        amount, custom_fee = ai_presets[i]
        net = round_curr(amount - custom_fee)
        txn_date = base_date + timedelta(days=(i % 6))
        settle_date = txn_date + timedelta(days=2)
        running_balance = round_curr(running_balance + net)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{net:.2f}",
            "settlement_date": settle_date.isoformat(),
            "reference_number": utr,
            "status": "settled",
            "fees": f"{custom_fee:.2f}",
            "gst": "0.00",
            "tds": "0.00",
        })
        bank_rows.append({
            "bank_txn_id": bnk_id,
            "txn_date": settle_date.isoformat(),
            "description": f"ACH CR RAZORPAY SETTLEMENT {utr}",
            "reference_number": utr,
            "amount": f"{net:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "non_standard_adjustment",
            "expected_resolution": "ai",
            "likely_reason": "processing_fee",
            "evidence_field": "settlement.fees",
            "difference_amount": f"{custom_fee:.2f}",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{net:.2f}",
            "bank_amount": f"{net:.2f}",
            "explanation": f"Non-standard fee override of ₹{custom_fee:.2f} verified by Finance Verification Engine.",
        })
        record_idx += 1

    # 6. Delayed settlements (2 records)
    for i in range(2):
        order_id = f"ORD-2026-DLY-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"
        amount = round_curr(Decimal("4000.00") + Decimal(str(i * 300.00)))
        txn_date = base_date + timedelta(days=5)
        settle_date = txn_date + timedelta(days=6)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "pending_settlement",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "settlement_date": settle_date.isoformat(),
            "reference_number": utr,
            "status": "pending",
            "fees": "0.00",
            "gst": "0.00",
            "tds": "0.00",
        })
        bank_rows.append({
            "bank_txn_id": bnk_id,
            "txn_date": settle_date.isoformat(),
            "description": f"ACH CR RAZORPAY SETTLEMENT PENDING {utr}",
            "reference_number": utr,
            "amount": f"{amount:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "pending",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "delayed_settlement",
            "expected_resolution": "exception",
            "exception_category": "settlement_delay",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{amount:.2f}",
            "bank_amount": f"{amount:.2f}",
            "explanation": "Settlement delayed past T+2 window.",
        })
        record_idx += 1

    # 7. Refunds (2 records)
    for i in range(2):
        order_id = f"ORD-2026-REF-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"
        amount = round_curr(Decimal("3200.00") + Decimal(str(i * 400.00)))
        refund_amount = -amount
        txn_date = base_date + timedelta(days=8)
        running_balance = round_curr(running_balance + refund_amount)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "refunded",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{refund_amount:.2f}",
            "settlement_date": txn_date.isoformat(),
            "reference_number": utr,
            "status": "refund_processed",
            "fees": "0.00",
            "gst": "0.00",
            "tds": "0.00",
        })
        bank_rows.append({
            "bank_txn_id": bnk_id,
            "txn_date": txn_date.isoformat(),
            "description": f"ACH DR RAZORPAY REFUND {utr}",
            "reference_number": utr,
            "amount": f"{refund_amount:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "debited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "refund",
            "expected_resolution": "exception",
            "exception_category": "refund_pending",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{refund_amount:.2f}",
            "bank_amount": f"{refund_amount:.2f}",
            "explanation": "Refund deduction resulting in bank debit.",
        })
        record_idx += 1

    # 8. Duplicate Invoices (2 records sharing duplicate order_id)
    dup_order_id = "ORD-2026-DUP-0097"
    for i in range(2):
        order_id = dup_order_id
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"
        amount = round_curr(Decimal("4500.00") + Decimal(str(i * 500.00)))
        txn_date = base_date + timedelta(days=2)
        settle_date = txn_date + timedelta(days=1)
        running_balance = round_curr(running_balance + amount)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "settlement_date": settle_date.isoformat(),
            "reference_number": utr,
            "status": "settled",
            "fees": "0.00",
            "gst": "0.00",
            "tds": "0.00",
        })
        bank_rows.append({
            "bank_txn_id": bnk_id,
            "txn_date": settle_date.isoformat(),
            "description": f"ACH CR RAZORPAY SETTLEMENT {utr}",
            "reference_number": utr,
            "amount": f"{amount:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "duplicate_invoice",
            "expected_resolution": "exception",
            "exception_category": "duplicate_invoice",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{amount:.2f}",
            "bank_amount": f"{amount:.2f}",
            "explanation": "Duplicate invoice detected for same order ID.",
        })
        record_idx += 1

    # 9. Missing Bank Credit (1 record)
    for i in range(1):
        order_id = f"ORD-2026-MISS-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"
        amount = Decimal("11000.00")
        txn_date = base_date + timedelta(days=3)
        settle_date = txn_date + timedelta(days=2)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{amount:.2f}",
            "settlement_date": settle_date.isoformat(),
            "reference_number": utr,
            "status": "settled",
            "fees": "0.00",
            "gst": "0.00",
            "tds": "0.00",
        })
        bank_rows.append({
            "bank_txn_id": bnk_id,
            "txn_date": settle_date.isoformat(),
            "description": "MISC BANK CHARGES UNRELATED",
            "reference_number": f"MISC-REF-{record_idx}",
            "amount": "-50.00",
            "balance": f"{running_balance:.2f}",
            "status": "debited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "missing_bank_credit",
            "expected_resolution": "exception",
            "exception_category": "missing_credit",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{amount:.2f}",
            "bank_amount": "-50.00",
            "explanation": "Expected settlement credit not found in bank statement past delay window.",
        })
        record_idx += 1

    # 10. Genuine Unknown (1 record)
    for i in range(1):
        order_id = f"ORD-2026-UNK-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR-UNKNOWN-{record_idx}"
        inv_amount = Decimal("7777.00")
        set_amount = Decimal("5432.10")
        bnk_amount = Decimal("9999.00")
        txn_date = base_date + timedelta(days=10)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{inv_amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}_UNKNOWN",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{set_amount:.2f}",
            "settlement_date": txn_date.isoformat(),
            "reference_number": utr,
            "status": "settled",
            "fees": "12.34",
            "gst": "2.22",
            "tds": "0.00",
        })
        bank_rows.append({
            "bank_txn_id": bnk_id,
            "txn_date": txn_date.isoformat(),
            "description": f"UNKNOWN ACH SETTLEMENT {utr}",
            "reference_number": utr,
            "amount": f"{bnk_amount:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "unknown",
            "expected_resolution": "exception",
            "exception_category": "unknown",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{inv_amount:.2f}",
            "settlement_amount": f"{set_amount:.2f}",
            "bank_amount": f"{bnk_amount:.2f}",
            "explanation": "Genuine unknown exception with mismatched amounts and references.",
        })
        record_idx += 1

    return invoices, settlements, bank_rows, ground_truth



def generate_merchant_dataset(
    merchant_type: str = "retail",
    total_count: int = 100,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generates N synthetic invoices, settlements, bank rows, and ground truth entries
    tailored to a specific industry archetype.
    """
    random.seed(seed)
    profile: MerchantArchetype = get_archetype(merchant_type)
    fee_cfg: FeeConfig = load_fee_config(profile.fee_config_name)

    invoices: List[Dict[str, Any]] = []
    settlements: List[Dict[str, Any]] = []
    bank_rows: List[Dict[str, Any]] = []
    ground_truth: List[Dict[str, Any]] = []

    base_date = date(2026, 8, 1)
    running_balance = Decimal("5000000.00")

    curr_fmt = profile.currency_format
    dt_fmt = profile.date_format
    prefix = profile.merchant_type[:4].upper()

    # Calculate partition counts based on total_count
    # Standard distribution:
    # ~70% Exact match
    # ~8% Fee deduction
    # ~5% GST deduction
    # ~3% TDS deduction
    # ~6% AI custom verification
    # ~8% Diverse exception categories (30+ types)
    count_exact = max(1, int(total_count * 0.70))
    count_fee = max(1, int(total_count * 0.08))
    count_gst = max(1, int(total_count * 0.05))
    count_tds = max(1, int(total_count * 0.03))
    count_ai = max(1, int(total_count * 0.06))
    count_exceptions = total_count - (count_exact + count_fee + count_gst + count_tds + count_ai)

    record_idx = 1
    min_t, max_t = profile.default_ticket_range

    # Helper ticket generator
    def get_ticket(idx: int) -> Decimal:
        step = (max_t - min_t) / max(total_count, 1)
        val = min_t + (idx * step)
        return round_curr(Decimal(str(round(val, 2))))

    # 1. EXACT MATCHES
    for i in range(count_exact):
        order_id = f"ORD-{prefix}-EX-{record_idx:05d}"
        inv_id = f"INV-{prefix}-{record_idx:05d}"
        set_id = f"SET-{prefix}-{record_idx:05d}"
        bnk_id = f"BNK-{prefix}-{record_idx:05d}"
        utr = f"UTR{prefix}202608{record_idx:07d}"

        amount = get_ticket(i)
        txn_date = base_date + timedelta(days=(i % 25))
        settle_date = txn_date + timedelta(days=fee_cfg.settlement_delay_days)
        running_balance = round_curr(running_balance + amount)

        invoices.append({
            profile.invoice_columns["invoice_id"]: inv_id,
            profile.invoice_columns["order_id"]: order_id,
            profile.invoice_columns["amount"]: _format_currency_val(amount, curr_fmt),
            profile.invoice_columns["invoice_date"]: _format_date_val(txn_date, dt_fmt),
            profile.invoice_columns["customer_name"]: f"Client_{prefix}_{record_idx}",
            profile.invoice_columns["status"]: "paid",
        })
        settlements.append({
            profile.settlement_columns["settlement_id"]: set_id,
            profile.settlement_columns["order_id"]: order_id,
            profile.settlement_columns["amount"]: _format_currency_val(amount, curr_fmt),
            profile.settlement_columns["settlement_date"]: _format_date_val(settle_date, dt_fmt),
            profile.settlement_columns["reference_number"]: utr,
            profile.settlement_columns["status"]: "settled",
            profile.settlement_columns["fees"]: _format_currency_val(Decimal("0.00"), curr_fmt),
            profile.settlement_columns["gst"]: _format_currency_val(Decimal("0.00"), curr_fmt),
            profile.settlement_columns["tds"]: _format_currency_val(Decimal("0.00"), curr_fmt),
        })
        bank_rows.append({
            profile.bank_columns["bank_txn_id"]: bnk_id,
            profile.bank_columns["txn_date"]: _format_date_val(settle_date, dt_fmt),
            profile.bank_columns["description"]: f"ACH CR RAZORPAY SETTLEMENT {utr}",
            profile.bank_columns["reference_number"]: utr,
            profile.bank_columns["amount"]: _format_currency_val(amount, curr_fmt),
            profile.bank_columns["balance"]: _format_currency_val(running_balance, curr_fmt),
            profile.bank_columns["status"]: "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{prefix}-{record_idx:05d}",
            "merchant_type": merchant_type,
            "category": "exact_match",
            "expected_resolution": "rule",
            "expected_rule": "exact_order_id",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{amount:.2f}",
            "bank_amount": f"{amount:.2f}",
            "explanation": f"Exact match across order ID, UTR, and amount for {profile.display_name}.",
        })
        record_idx += 1

    # 2. STANDARD FEE DEDUCTIONS (Rule 5 MDR)
    for i in range(count_fee):
        order_id = f"ORD-{prefix}-FEE-{record_idx:05d}"
        inv_id = f"INV-{prefix}-{record_idx:05d}"
        set_id = f"SET-{prefix}-{record_idx:05d}"
        bnk_id = f"BNK-{prefix}-{record_idx:05d}"
        utr = f"UTR{prefix}202608{record_idx:07d}"

        amount = get_ticket(i + 10)
        fee_amount = round_curr(amount * fee_cfg.mdr_rate)
        net_amount = round_curr(amount - fee_amount)

        txn_date = base_date + timedelta(days=(i % 20))
        settle_date = txn_date + timedelta(days=fee_cfg.settlement_delay_days)
        running_balance = round_curr(running_balance + net_amount)

        invoices.append({
            profile.invoice_columns["invoice_id"]: inv_id,
            profile.invoice_columns["order_id"]: order_id,
            profile.invoice_columns["amount"]: _format_currency_val(amount, curr_fmt),
            profile.invoice_columns["invoice_date"]: _format_date_val(txn_date, dt_fmt),
            profile.invoice_columns["customer_name"]: f"Client_{prefix}_{record_idx}",
            profile.invoice_columns["status"]: "paid",
        })
        settlements.append({
            profile.settlement_columns["settlement_id"]: set_id,
            profile.settlement_columns["order_id"]: order_id,
            profile.settlement_columns["amount"]: _format_currency_val(net_amount, curr_fmt),
            profile.settlement_columns["settlement_date"]: _format_date_val(settle_date, dt_fmt),
            profile.settlement_columns["reference_number"]: utr,
            profile.settlement_columns["status"]: "settled",
            profile.settlement_columns["fees"]: _format_currency_val(fee_amount, curr_fmt),
            profile.settlement_columns["gst"]: _format_currency_val(Decimal("0.00"), curr_fmt),
            profile.settlement_columns["tds"]: _format_currency_val(Decimal("0.00"), curr_fmt),
        })
        bank_rows.append({
            profile.bank_columns["bank_txn_id"]: bnk_id,
            profile.bank_columns["txn_date"]: _format_date_val(settle_date, dt_fmt),
            profile.bank_columns["description"]: f"ACH CR RAZORPAY SETTLEMENT {utr}",
            profile.bank_columns["reference_number"]: utr,
            profile.bank_columns["amount"]: _format_currency_val(net_amount, curr_fmt),
            profile.bank_columns["balance"]: _format_currency_val(running_balance, curr_fmt),
            profile.bank_columns["status"]: "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{prefix}-{record_idx:05d}",
            "merchant_type": merchant_type,
            "category": "fee_deduction",
            "expected_resolution": "rule",
            "expected_rule": "fee_gst_tds_adjusted_amount",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{net_amount:.2f}",
            "bank_amount": f"{net_amount:.2f}",
            "explanation": f"MDR fee deduction of {fee_cfg.mdr}% matching schedule.",
        })
        record_idx += 1

    # 3. GST DEDUCTIONS (Rule 5 Fee + GST)
    for i in range(count_gst):
        order_id = f"ORD-{prefix}-GST-{record_idx:05d}"
        inv_id = f"INV-{prefix}-{record_idx:05d}"
        set_id = f"SET-{prefix}-{record_idx:05d}"
        bnk_id = f"BNK-{prefix}-{record_idx:05d}"
        utr = f"UTR{prefix}202608{record_idx:07d}"

        amount = get_ticket(i + 20)
        fee_amount = round_curr(amount * fee_cfg.mdr_rate)
        gst_amount = round_curr(fee_amount * fee_cfg.gst_rate)
        net_amount = round_curr(amount - fee_amount - gst_amount)

        txn_date = base_date + timedelta(days=(i % 15))
        settle_date = txn_date + timedelta(days=fee_cfg.settlement_delay_days)
        running_balance = round_curr(running_balance + net_amount)

        invoices.append({
            profile.invoice_columns["invoice_id"]: inv_id,
            profile.invoice_columns["order_id"]: order_id,
            profile.invoice_columns["amount"]: _format_currency_val(amount, curr_fmt),
            profile.invoice_columns["invoice_date"]: _format_date_val(txn_date, dt_fmt),
            profile.invoice_columns["customer_name"]: f"Client_{prefix}_{record_idx}",
            profile.invoice_columns["status"]: "paid",
        })
        settlements.append({
            profile.settlement_columns["settlement_id"]: set_id,
            profile.settlement_columns["order_id"]: order_id,
            profile.settlement_columns["amount"]: _format_currency_val(net_amount, curr_fmt),
            profile.settlement_columns["settlement_date"]: _format_date_val(settle_date, dt_fmt),
            profile.settlement_columns["reference_number"]: utr,
            profile.settlement_columns["status"]: "settled",
            profile.settlement_columns["fees"]: _format_currency_val(fee_amount, curr_fmt),
            profile.settlement_columns["gst"]: _format_currency_val(gst_amount, curr_fmt),
            profile.settlement_columns["tds"]: _format_currency_val(Decimal("0.00"), curr_fmt),
        })
        bank_rows.append({
            profile.bank_columns["bank_txn_id"]: bnk_id,
            profile.bank_columns["txn_date"]: _format_date_val(settle_date, dt_fmt),
            profile.bank_columns["description"]: f"ACH CR RAZORPAY SETTLEMENT {utr}",
            profile.bank_columns["reference_number"]: utr,
            profile.bank_columns["amount"]: _format_currency_val(net_amount, curr_fmt),
            profile.bank_columns["balance"]: _format_currency_val(running_balance, curr_fmt),
            profile.bank_columns["status"]: "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{prefix}-{record_idx:05d}",
            "merchant_type": merchant_type,
            "category": "gst_deduction",
            "expected_resolution": "rule",
            "expected_rule": "fee_gst_tds_adjusted_amount",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{net_amount:.2f}",
            "bank_amount": f"{net_amount:.2f}",
            "explanation": f"Combined Fee and {fee_cfg.gst}% GST deduction.",
        })
        record_idx += 1

    # 4. TDS DEDUCTIONS (Rule 5 Fee + GST + TDS)
    for i in range(count_tds):
        order_id = f"ORD-{prefix}-TDS-{record_idx:05d}"
        inv_id = f"INV-{prefix}-{record_idx:05d}"
        set_id = f"SET-{prefix}-{record_idx:05d}"
        bnk_id = f"BNK-{prefix}-{record_idx:05d}"
        utr = f"UTR{prefix}202608{record_idx:07d}"

        amount = get_ticket(i + 30)
        fee_amount = round_curr(amount * fee_cfg.mdr_rate)
        gst_amount = round_curr(fee_amount * fee_cfg.gst_rate)
        tds_amount = round_curr(amount * fee_cfg.tds_rate)
        net_amount = round_curr(amount - fee_amount - gst_amount - tds_amount)

        txn_date = base_date + timedelta(days=(i % 12))
        settle_date = txn_date + timedelta(days=fee_cfg.settlement_delay_days)
        running_balance = round_curr(running_balance + net_amount)

        invoices.append({
            profile.invoice_columns["invoice_id"]: inv_id,
            profile.invoice_columns["order_id"]: order_id,
            profile.invoice_columns["amount"]: _format_currency_val(amount, curr_fmt),
            profile.invoice_columns["invoice_date"]: _format_date_val(txn_date, dt_fmt),
            profile.invoice_columns["customer_name"]: f"Client_{prefix}_{record_idx}",
            profile.invoice_columns["status"]: "paid",
        })
        settlements.append({
            profile.settlement_columns["settlement_id"]: set_id,
            profile.settlement_columns["order_id"]: order_id,
            profile.settlement_columns["amount"]: _format_currency_val(net_amount, curr_fmt),
            profile.settlement_columns["settlement_date"]: _format_date_val(settle_date, dt_fmt),
            profile.settlement_columns["reference_number"]: utr,
            profile.settlement_columns["status"]: "settled",
            profile.settlement_columns["fees"]: _format_currency_val(fee_amount, curr_fmt),
            profile.settlement_columns["gst"]: _format_currency_val(gst_amount, curr_fmt),
            profile.settlement_columns["tds"]: _format_currency_val(tds_amount, curr_fmt),
        })
        bank_rows.append({
            profile.bank_columns["bank_txn_id"]: bnk_id,
            profile.bank_columns["txn_date"]: _format_date_val(settle_date, dt_fmt),
            profile.bank_columns["description"]: f"ACH CR RAZORPAY SETTLEMENT {utr}",
            profile.bank_columns["reference_number"]: utr,
            profile.bank_columns["amount"]: _format_currency_val(net_amount, curr_fmt),
            profile.bank_columns["balance"]: _format_currency_val(running_balance, curr_fmt),
            profile.bank_columns["status"]: "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{prefix}-{record_idx:05d}",
            "merchant_type": merchant_type,
            "category": "tds_deduction",
            "expected_resolution": "rule",
            "expected_rule": "fee_gst_tds_adjusted_amount",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{net_amount:.2f}",
            "bank_amount": f"{net_amount:.2f}",
            "explanation": f"Full statutory deductions including Section 194 TDS ({fee_cfg.tds}%).",
        })
        record_idx += 1

    # 5. AI VERIFIED NON-STANDARD HERO CASES (Misses Rule 5, verified by AI + Validator)
    for i in range(count_ai):
        order_id = f"ORD-{prefix}-AI-{record_idx:05d}"
        inv_id = f"INV-{prefix}-{record_idx:05d}"
        set_id = f"SET-{prefix}-{record_idx:05d}"
        bnk_id = f"BNK-{prefix}-{record_idx:05d}"
        utr = f"UTR{prefix}202608{record_idx:07d}"

        amount = get_ticket(i + 40)
        # Custom non-standard override fee (e.g. flat ₹30, ₹45, ₹75)
        custom_fee = Decimal(str(30.0 + (i % 5) * 15.0))
        net_amount = round_curr(amount - custom_fee)

        txn_date = base_date + timedelta(days=(i % 10))
        settle_date = txn_date + timedelta(days=fee_cfg.settlement_delay_days)
        running_balance = round_curr(running_balance + net_amount)

        invoices.append({
            profile.invoice_columns["invoice_id"]: inv_id,
            profile.invoice_columns["order_id"]: order_id,
            profile.invoice_columns["amount"]: _format_currency_val(amount, curr_fmt),
            profile.invoice_columns["invoice_date"]: _format_date_val(txn_date, dt_fmt),
            profile.invoice_columns["customer_name"]: f"Client_{prefix}_{record_idx}",
            profile.invoice_columns["status"]: "paid",
        })
        settlements.append({
            profile.settlement_columns["settlement_id"]: set_id,
            profile.settlement_columns["order_id"]: order_id,
            profile.settlement_columns["amount"]: _format_currency_val(net_amount, curr_fmt),
            profile.settlement_columns["settlement_date"]: _format_date_val(settle_date, dt_fmt),
            profile.settlement_columns["reference_number"]: utr,
            profile.settlement_columns["status"]: "settled",
            profile.settlement_columns["fees"]: _format_currency_val(custom_fee, curr_fmt),
            profile.settlement_columns["gst"]: _format_currency_val(Decimal("0.00"), curr_fmt),
            profile.settlement_columns["tds"]: _format_currency_val(Decimal("0.00"), curr_fmt),
        })
        bank_rows.append({
            profile.bank_columns["bank_txn_id"]: bnk_id,
            profile.bank_columns["txn_date"]: _format_date_val(settle_date, dt_fmt),
            profile.bank_columns["description"]: f"ACH CR RAZORPAY SETTLEMENT {utr}",
            profile.bank_columns["reference_number"]: utr,
            profile.bank_columns["amount"]: _format_currency_val(net_amount, curr_fmt),
            profile.bank_columns["balance"]: _format_currency_val(running_balance, curr_fmt),
            profile.bank_columns["status"]: "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{prefix}-{record_idx:05d}",
            "merchant_type": merchant_type,
            "category": "ai_verified_custom_fee",
            "expected_resolution": "ai",
            "likely_reason": "processing_fee",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{net_amount:.2f}",
            "bank_amount": f"{net_amount:.2f}",
            "explanation": f"Non-standard manual fee override of ₹{custom_fee:.2f} verified by Finance Verification Engine.",
        })
        record_idx += 1

    # 6. DIVERSE 30+ EXCEPTION SCENARIOS
    exception_types = profile.common_exceptions or [
        "settlement_delay", "refund_pending", "duplicate_invoice", "missing_credit", "unknown"
    ]

    for i in range(count_exceptions):
        exc_type = exception_types[i % len(exception_types)]
        order_id = f"ORD-{prefix}-EXC-{record_idx:05d}"
        inv_id = f"INV-{prefix}-{record_idx:05d}"
        set_id = f"SET-{prefix}-{record_idx:05d}"
        bnk_id = f"BNK-{prefix}-{record_idx:05d}"
        utr = f"UTR{prefix}202608{record_idx:07d}"

        amount = get_ticket(i + 50)
        txn_date = base_date + timedelta(days=(i % 15))
        settle_date = txn_date + timedelta(days=fee_cfg.settlement_delay_days + 4)

        if exc_type in ("refund_pending", "refund_reversal", "manual_refund"):
            refund_amount = -amount
            running_balance = round_curr(running_balance + refund_amount)
            invoices.append({
                profile.invoice_columns["invoice_id"]: inv_id,
                profile.invoice_columns["order_id"]: order_id,
                profile.invoice_columns["amount"]: _format_currency_val(amount, curr_fmt),
                profile.invoice_columns["invoice_date"]: _format_date_val(txn_date, dt_fmt),
                profile.invoice_columns["customer_name"]: f"Client_{prefix}_{record_idx}",
                profile.invoice_columns["status"]: "refunded",
            })
            settlements.append({
                profile.settlement_columns["settlement_id"]: set_id,
                profile.settlement_columns["order_id"]: order_id,
                profile.settlement_columns["amount"]: _format_currency_val(refund_amount, curr_fmt),
                profile.settlement_columns["settlement_date"]: _format_date_val(txn_date, dt_fmt),
                profile.settlement_columns["reference_number"]: utr,
                profile.settlement_columns["status"]: "refund_processed",
                profile.settlement_columns["fees"]: _format_currency_val(Decimal("0.00"), curr_fmt),
                profile.settlement_columns["gst"]: _format_currency_val(Decimal("0.00"), curr_fmt),
                profile.settlement_columns["tds"]: _format_currency_val(Decimal("0.00"), curr_fmt),
            })
            bank_rows.append({
                profile.bank_columns["bank_txn_id"]: bnk_id,
                profile.bank_columns["txn_date"]: _format_date_val(txn_date, dt_fmt),
                profile.bank_columns["description"]: f"ACH DR RAZORPAY REFUND {utr}",
                profile.bank_columns["reference_number"]: utr,
                profile.bank_columns["amount"]: _format_currency_val(refund_amount, curr_fmt),
                profile.bank_columns["balance"]: _format_currency_val(running_balance, curr_fmt),
                profile.bank_columns["status"]: "debited",
            })
            ground_truth.append({
                "scenario_id": f"SCENARIO-{prefix}-{record_idx:05d}",
                "merchant_type": merchant_type,
                "category": "refund",
                "expected_resolution": "exception",
                "exception_category": "refund_pending",
                "order_id": order_id,
                "invoice_id": inv_id,
                "settlement_id": set_id,
                "bank_txn_id": bnk_id,
                "reference_number": utr,
                "invoice_amount": f"{amount:.2f}",
                "settlement_amount": f"{refund_amount:.2f}",
                "bank_amount": f"{refund_amount:.2f}",
                "explanation": "Exception: Customer refund debit offset.",
            })

        elif exc_type in ("duplicate_invoice", "double_settlement"):
            invoices.append({
                profile.invoice_columns["invoice_id"]: inv_id,
                profile.invoice_columns["order_id"]: order_id,
                profile.invoice_columns["amount"]: _format_currency_val(amount, curr_fmt),
                profile.invoice_columns["invoice_date"]: _format_date_val(txn_date, dt_fmt),
                profile.invoice_columns["customer_name"]: f"Client_{prefix}_{record_idx}",
                profile.invoice_columns["status"]: "paid",
            })
            # Duplicate secondary invoice
            invoices.append({
                profile.invoice_columns["invoice_id"]: f"{inv_id}-DUP",
                profile.invoice_columns["order_id"]: order_id,
                profile.invoice_columns["amount"]: _format_currency_val(amount, curr_fmt),
                profile.invoice_columns["invoice_date"]: _format_date_val(txn_date, dt_fmt),
                profile.invoice_columns["customer_name"]: f"Client_{prefix}_{record_idx}_DUP",
                profile.invoice_columns["status"]: "paid",
            })
            settlements.append({
                profile.settlement_columns["settlement_id"]: set_id,
                profile.settlement_columns["order_id"]: order_id,
                profile.settlement_columns["amount"]: _format_currency_val(amount, curr_fmt),
                profile.settlement_columns["settlement_date"]: _format_date_val(settle_date, dt_fmt),
                profile.settlement_columns["reference_number"]: utr,
                profile.settlement_columns["status"]: "settled",
                profile.settlement_columns["fees"]: _format_currency_val(Decimal("0.00"), curr_fmt),
                profile.settlement_columns["gst"]: _format_currency_val(Decimal("0.00"), curr_fmt),
                profile.settlement_columns["tds"]: _format_currency_val(Decimal("0.00"), curr_fmt),
            })
            bank_rows.append({
                profile.bank_columns["bank_txn_id"]: bnk_id,
                profile.bank_columns["txn_date"]: _format_date_val(settle_date, dt_fmt),
                profile.bank_columns["description"]: f"ACH CR RAZORPAY SETTLEMENT {utr}",
                profile.bank_columns["reference_number"]: utr,
                profile.bank_columns["amount"]: _format_currency_val(amount, curr_fmt),
                profile.bank_columns["balance"]: _format_currency_val(running_balance, curr_fmt),
                profile.bank_columns["status"]: "credited",
            })
            ground_truth.append({
                "scenario_id": f"SCENARIO-{prefix}-{record_idx:05d}",
                "merchant_type": merchant_type,
                "category": "duplicate_invoice",
                "expected_resolution": "exception",
                "exception_category": "duplicate_invoice",
                "order_id": order_id,
                "invoice_id": inv_id,
                "settlement_id": set_id,
                "bank_txn_id": bnk_id,
                "reference_number": utr,
                "invoice_amount": f"{amount:.2f}",
                "settlement_amount": f"{amount:.2f}",
                "bank_amount": f"{amount:.2f}",
                "explanation": "Exception: Duplicate invoice shares identical order ID.",
            })

        elif exc_type in ("missing_credit", "missing_bank_credit", "missing_utr"):
            invoices.append({
                profile.invoice_columns["invoice_id"]: inv_id,
                profile.invoice_columns["order_id"]: order_id,
                profile.invoice_columns["amount"]: _format_currency_val(amount, curr_fmt),
                profile.invoice_columns["invoice_date"]: _format_date_val(txn_date, dt_fmt),
                profile.invoice_columns["customer_name"]: f"Client_{prefix}_{record_idx}",
                profile.invoice_columns["status"]: "paid",
            })
            settlements.append({
                profile.settlement_columns["settlement_id"]: set_id,
                profile.settlement_columns["order_id"]: order_id,
                profile.settlement_columns["amount"]: _format_currency_val(amount, curr_fmt),
                profile.settlement_columns["settlement_date"]: _format_date_val(settle_date, dt_fmt),
                profile.settlement_columns["reference_number"]: utr,
                profile.settlement_columns["status"]: "settled",
                profile.settlement_columns["fees"]: _format_currency_val(Decimal("0.00"), curr_fmt),
                profile.settlement_columns["gst"]: _format_currency_val(Decimal("0.00"), curr_fmt),
                profile.settlement_columns["tds"]: _format_currency_val(Decimal("0.00"), curr_fmt),
            })
            # Bank statement has unrelated line
            bank_rows.append({
                profile.bank_columns["bank_txn_id"]: bnk_id,
                profile.bank_columns["txn_date"]: _format_date_val(settle_date, dt_fmt),
                profile.bank_columns["description"]: "BANK ANNUAL SERVICE CHARGES",
                profile.bank_columns["reference_number"]: f"MISC-{record_idx}",
                profile.bank_columns["amount"]: _format_currency_val(Decimal("-100.00"), curr_fmt),
                profile.bank_columns["balance"]: _format_currency_val(running_balance, curr_fmt),
                profile.bank_columns["status"]: "debited",
            })
            ground_truth.append({
                "scenario_id": f"SCENARIO-{prefix}-{record_idx:05d}",
                "merchant_type": merchant_type,
                "category": "missing_credit",
                "expected_resolution": "exception",
                "exception_category": "missing_credit",
                "order_id": order_id,
                "invoice_id": inv_id,
                "settlement_id": set_id,
                "bank_txn_id": bnk_id,
                "reference_number": utr,
                "invoice_amount": f"{amount:.2f}",
                "settlement_amount": f"{amount:.2f}",
                "bank_amount": "-100.00",
                "explanation": "Exception: Expected settlement not found in bank statement.",
            })

        else:
            # Default / Timing / Delayed Exception
            invoices.append({
                profile.invoice_columns["invoice_id"]: inv_id,
                profile.invoice_columns["order_id"]: order_id,
                profile.invoice_columns["amount"]: _format_currency_val(amount, curr_fmt),
                profile.invoice_columns["invoice_date"]: _format_date_val(txn_date, dt_fmt),
                profile.invoice_columns["customer_name"]: f"Client_{prefix}_{record_idx}",
                profile.invoice_columns["status"]: "pending_settlement",
            })
            settlements.append({
                profile.settlement_columns["settlement_id"]: set_id,
                profile.settlement_columns["order_id"]: order_id,
                profile.settlement_columns["amount"]: _format_currency_val(amount, curr_fmt),
                profile.settlement_columns["settlement_date"]: _format_date_val(settle_date, dt_fmt),
                profile.settlement_columns["reference_number"]: utr,
                profile.settlement_columns["status"]: "pending",
                profile.settlement_columns["fees"]: _format_currency_val(Decimal("0.00"), curr_fmt),
                profile.settlement_columns["gst"]: _format_currency_val(Decimal("0.00"), curr_fmt),
                profile.settlement_columns["tds"]: _format_currency_val(Decimal("0.00"), curr_fmt),
            })
            bank_rows.append({
                profile.bank_columns["bank_txn_id"]: bnk_id,
                profile.bank_columns["txn_date"]: _format_date_val(settle_date, dt_fmt),
                profile.bank_columns["description"]: f"ACH CR PENDING SETTLEMENT {utr}",
                profile.bank_columns["reference_number"]: utr,
                profile.bank_columns["amount"]: _format_currency_val(amount, curr_fmt),
                profile.bank_columns["balance"]: _format_currency_val(running_balance, curr_fmt),
                profile.bank_columns["status"]: "pending",
            })
            ground_truth.append({
                "scenario_id": f"SCENARIO-{prefix}-{record_idx:05d}",
                "merchant_type": merchant_type,
                "category": "settlement_delay",
                "expected_resolution": "exception",
                "exception_category": "settlement_delay",
                "order_id": order_id,
                "invoice_id": inv_id,
                "settlement_id": set_id,
                "bank_txn_id": bnk_id,
                "reference_number": utr,
                "invoice_amount": f"{amount:.2f}",
                "settlement_amount": f"{amount:.2f}",
                "bank_amount": f"{amount:.2f}",
                "explanation": f"Exception: Settlement delay beyond standard {fee_cfg.settlement_delay_days}-day window.",
            })

        record_idx += 1

    return invoices, settlements, bank_rows, ground_truth


def save_csv(data: List[Dict[str, Any]], filepath: str) -> None:
    """Saves list of dicts to a CSV file."""
    if not data:
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    fieldnames: List[str] = []
    for item in data:
        for k in item.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)


def save_ground_truth(data: List[Dict[str, Any]], json_path: str, csv_path: str) -> None:
    """Saves ground truth labels in both JSON and CSV formats."""
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    save_csv(data, csv_path)


def generate_synthetic_data(
    output_dir: str = "backend/synthetic_data",
    merchant_type: str = "retail",
    total_count: int = 100,
) -> Dict[str, str]:
    """
    Main generator entrypoint. Generates synthetic invoices, settlements,
    bank statements and ground truth files in output_dir.
    """
    if merchant_type == "retail" and total_count == 100:
        invoices, settlements, bank_rows, ground_truth = generate_dataset()
    else:
        invoices, settlements, bank_rows, ground_truth = generate_merchant_dataset(
            merchant_type=merchant_type, total_count=total_count
        )

    os.makedirs(output_dir, exist_ok=True)
    inv_file = os.path.join(output_dir, "invoices.csv")
    set_file = os.path.join(output_dir, "settlements.csv")
    bnk_file = os.path.join(output_dir, "bank_statements.csv")
    gt_json = os.path.join(output_dir, "ground_truth.json")
    gt_csv = os.path.join(output_dir, "ground_truth.csv")

    save_csv(invoices, inv_file)
    save_csv(settlements, set_file)
    save_csv(bank_rows, bnk_file)
    save_ground_truth(ground_truth, gt_json, gt_csv)

    return {
        "invoices_csv": inv_file,
        "settlements_csv": set_file,
        "bank_statements_csv": bnk_file,
        "ground_truth_json": gt_json,
        "ground_truth_csv": gt_csv,
    }


def generate_multi_merchant_dataset(
    base_dir: str = "backend/synthetic_data/merchants",
    records_per_merchant: int = 100,
) -> Dict[str, Dict[str, str]]:
    """
    Generates multi-merchant synthetic datasets across all 10 registered archetypes.
    """
    results: Dict[str, Dict[str, str]] = {}

    for m_type in MERCHANT_ARCHETYPES.keys():
        merchant_dir = os.path.join(base_dir, m_type)
        os.makedirs(merchant_dir, exist_ok=True)

        inv, set_rows, bnk_rows, gt = generate_merchant_dataset(
            merchant_type=m_type, total_count=records_per_merchant
        )

        inv_file = os.path.join(merchant_dir, "invoices.csv")
        set_file = os.path.join(merchant_dir, "settlements.csv")
        bnk_file = os.path.join(merchant_dir, "bank_statements.csv")
        gt_json = os.path.join(merchant_dir, "ground_truth.json")
        gt_csv = os.path.join(merchant_dir, "ground_truth.csv")

        save_csv(inv, inv_file)
        save_csv(set_rows, set_file)
        save_csv(bnk_rows, bnk_file)
        save_ground_truth(gt, gt_json, gt_csv)

        results[m_type] = {
            "invoices_csv": inv_file,
            "settlements_csv": set_file,
            "bank_statements_csv": bnk_file,
            "ground_truth_json": gt_json,
            "ground_truth_csv": gt_csv,
            "record_count": str(len(inv)),
        }

    return results


if __name__ == "__main__":
    out = generate_synthetic_data()
    print("Generated default synthetic files successfully:")
    for k, v in out.items():
        print(f"  {k}: {v}")

    multi_out = generate_multi_merchant_dataset()
    print(f"\nGenerated multi-merchant synthetic datasets across {len(multi_out)} profiles.")
