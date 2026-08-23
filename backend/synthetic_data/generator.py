import csv
import json
import os
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Tuple


def round_curr(val: Decimal) -> Decimal:
    """Rounds to 2 decimal places using half-up standard."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Documented standard rate schedule for rule-based resolution
STANDARD_FEE_RATE = Decimal("0.02")  # 2.0% standard Razorpay MDR
STANDARD_GST_RATE = Decimal("0.18")  # 18.0% GST on fees
STANDARD_TDS_RATE = Decimal("0.01")  # 1.0% TDS under Section 194O


def generate_dataset() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generates exactly 100 invoices, 100 settlements, 100 bank statement rows,
    and a ground truth label for every record scenario.
    """
    invoices: List[Dict[str, Any]] = []
    settlements: List[Dict[str, Any]] = []
    bank_rows: List[Dict[str, Any]] = []
    ground_truth: List[Dict[str, Any]] = []

    base_date = date(2026, 8, 1)
    base_balance = Decimal("500000.00")
    running_balance = base_balance

    record_idx = 1

    # 1. EXACT MATCHES (70 records)
    # Order ID + UTR + Amount all agree directly
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

    # 2. STANDARD FEE DEDUCTIONS (8 records)
    # Follows fixed 2.0% standard formula: settlement_amount = invoice - fees
    for i in range(8):
        order_id = f"ORD-2026-FEE-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"

        inv_amount = round_curr(Decimal("5000.00") + Decimal(str(i * 300.00)))
        fees = round_curr(inv_amount * STANDARD_FEE_RATE)
        net_amount = round_curr(inv_amount - fees)
        txn_date = base_date + timedelta(days=(i % 15))
        settle_date = txn_date + timedelta(days=1)

        running_balance = round_curr(running_balance + net_amount)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{inv_amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{net_amount:.2f}",
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
            "amount": f"{net_amount:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "fee_deduction",
            "expected_resolution": "rule",
            "expected_rule": "fee_gst_tds_adjusted_amount:Fee",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{inv_amount:.2f}",
            "settlement_amount": f"{net_amount:.2f}",
            "bank_amount": f"{net_amount:.2f}",
            "explanation": f"Rule match: 2.0% standard fee (₹{fees:.2f}) deducted.",
        })
        record_idx += 1

    # 3. STANDARD GST DEDUCTIONS (5 records)
    # Follows fixed formula: fee = 2%, GST = 18% of fee, settlement = invoice - fee - GST
    for i in range(5):
        order_id = f"ORD-2026-GST-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"

        inv_amount = round_curr(Decimal("8000.00") + Decimal(str(i * 450.00)))
        fees = round_curr(inv_amount * STANDARD_FEE_RATE)
        gst = round_curr(fees * STANDARD_GST_RATE)
        net_amount = round_curr(inv_amount - fees - gst)
        txn_date = base_date + timedelta(days=(i % 15))
        settle_date = txn_date + timedelta(days=1)

        running_balance = round_curr(running_balance + net_amount)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{inv_amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{net_amount:.2f}",
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
            "amount": f"{net_amount:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "gst_deduction",
            "expected_resolution": "rule",
            "expected_rule": "fee_gst_tds_adjusted_amount:Fee+GST",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{inv_amount:.2f}",
            "settlement_amount": f"{net_amount:.2f}",
            "bank_amount": f"{net_amount:.2f}",
            "explanation": f"Rule match: standard 2% fee (₹{fees:.2f}) + 18% GST (₹{gst:.2f}) deducted.",
        })
        record_idx += 1

    # 4. STANDARD TDS DEDUCTIONS (3 records)
    # Follows fixed formula: fee = 2%, GST = 18% of fee, TDS = 1% on invoice
    for i in range(3):
        order_id = f"ORD-2026-TDS-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"

        inv_amount = round_curr(Decimal("15000.00") + Decimal(str(i * 1000.00)))
        fees = round_curr(inv_amount * STANDARD_FEE_RATE)
        gst = round_curr(fees * STANDARD_GST_RATE)
        tds = round_curr(inv_amount * STANDARD_TDS_RATE)
        net_amount = round_curr(inv_amount - fees - gst - tds)
        txn_date = base_date + timedelta(days=(i % 15))
        settle_date = txn_date + timedelta(days=1)

        running_balance = round_curr(running_balance + net_amount)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{inv_amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{net_amount:.2f}",
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
            "amount": f"{net_amount:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "tds_deduction",
            "expected_resolution": "rule",
            "expected_rule": "fee_gst_tds_adjusted_amount:Fee+GST+TDS",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{inv_amount:.2f}",
            "settlement_amount": f"{net_amount:.2f}",
            "bank_amount": f"{net_amount:.2f}",
            "explanation": f"Rule match: standard fee (₹{fees:.2f}) + GST (₹{gst:.2f}) + TDS (₹{tds:.2f}) deducted.",
        })
        record_idx += 1

    # 5. NON-STANDARD ONE-OFF ADJUSTMENTS (6 records - between 5 and 8)
    # DOES NOT match standard 2% formula, but is numerically explainable via custom manual fee override
    # Meant to require AI Verification Engine (e.g. ₹30 fee on ₹12,000, ₹45 flat fee, ₹75 manual adjustment)
    custom_adjustments = [
        (Decimal("12000.00"), Decimal("30.00")),   # Hero case from PRD/SRS: ₹12,000 - ₹30 = ₹11,970
        (Decimal("25000.00"), Decimal("45.00")),   # Custom flat fee override
        (Decimal("18500.00"), Decimal("50.00")),   # Enterprise discount manual fee
        (Decimal("32000.00"), Decimal("65.00")),   # Tiered pricing custom adjustment
        (Decimal("14200.00"), Decimal("35.00")),   # Custom promotional processing fee
        (Decimal("21000.00"), Decimal("40.00")),   # Special event settlement fee
    ]

    for inv_amount, custom_fee in custom_adjustments:
        order_id = f"ORD-2026-AI-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"

        net_amount = round_curr(inv_amount - custom_fee)
        txn_date = base_date + timedelta(days=2)
        settle_date = txn_date + timedelta(days=1)

        running_balance = round_curr(running_balance + net_amount)

        invoices.append({
            "invoice_id": inv_id,
            "order_id": order_id,
            "amount": f"{inv_amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}",
            "status": "paid",
        })
        # Note: fees is non-standard, so standard rule engine rate card check fails, requiring AI verification
        settlements.append({
            "settlement_id": set_id,
            "order_id": order_id,
            "amount": f"{net_amount:.2f}",
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
            "amount": f"{net_amount:.2f}",
            "balance": f"{running_balance:.2f}",
            "status": "credited",
        })
        ground_truth.append({
            "scenario_id": f"SCENARIO-{record_idx:04d}",
            "category": "non_standard_adjustment",
            "expected_resolution": "ai",
            "likely_reason": "processing_fee",
            "expected_value": f"{net_amount:.2f}",
            "evidence_field": "settlement.fees",
            "order_id": order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{inv_amount:.2f}",
            "settlement_amount": f"{net_amount:.2f}",
            "bank_amount": f"{net_amount:.2f}",
            "difference_amount": f"{custom_fee:.2f}",
            "explanation": f"Non-standard one-off adjustment of ₹{custom_fee:.2f}. Requires AI verification and Deterministic Validator check.",
        })
        record_idx += 1

    # 6. DELAYED SETTLEMENTS (2 records)
    # Invoice + bank or settlement exists, but settlement date is delayed / pending
    for i in range(2):
        order_id = f"ORD-2026-DELAY-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"

        amount = round_curr(Decimal("9500.00") + Decimal(str(i * 500.00)))
        txn_date = base_date + timedelta(days=12)
        # Delayed settlement date (T+6 days, beyond standard T+2 window)
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
        # Bank row has different batch settlement or pending credit
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
            "explanation": "Exception: Settlement delay beyond standard settlement window.",
        })
        record_idx += 1

    # 7. REFUNDS (2 records)
    # Negative bank entry / refund entry referencing previous transaction
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
            "explanation": "Exception: Refund transaction resulting in negative bank debit.",
        })
        record_idx += 1

    # 8. DUPLICATE INVOICES (2 records)
    # Invoices sharing order_id and amount with another invoice
    shared_dup_order_id = "ORD-2026-DUP-0097"
    for i in range(2):
        dup_order_id = shared_dup_order_id
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"


        amount = Decimal("6800.00")
        txn_date = base_date + timedelta(days=5)

        running_balance = round_curr(running_balance + amount)

        # Duplicate invoice: duplicate reference to same order
        invoices.append({
            "invoice_id": inv_id,
            "order_id": dup_order_id,
            "amount": f"{amount:.2f}",
            "invoice_date": txn_date.isoformat(),
            "customer_name": f"Customer_{record_idx}_DUP",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": set_id,
            "order_id": dup_order_id,
            "amount": f"{amount:.2f}",
            "settlement_date": txn_date.isoformat(),
            "reference_number": utr,
            "status": "settled",
            "fees": "0.00",
            "gst": "0.00",
            "tds": "0.00",
        })
        bank_rows.append({
            "bank_txn_id": bnk_id,
            "txn_date": txn_date.isoformat(),
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
            "order_id": dup_order_id,
            "invoice_id": inv_id,
            "settlement_id": set_id,
            "bank_txn_id": bnk_id,
            "reference_number": utr,
            "invoice_amount": f"{amount:.2f}",
            "settlement_amount": f"{amount:.2f}",
            "bank_amount": f"{amount:.2f}",
            "explanation": "Exception: Duplicate invoice detected for same order ID.",
        })
        record_idx += 1

    # 9. MISSING BANK CREDITS (1 record)
    # Settlement occurred, but bank statement did not credit the amount past delay window
    for i in range(1):
        order_id = f"ORD-2026-MISS-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR202608{record_idx:06d}"

        amount = round_curr(Decimal("11000.00") + Decimal(str(i * 750.00)))
        txn_date = base_date + timedelta(days=3)
        settle_date = txn_date + timedelta(days=1)

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
        # Bank row is missing the settlement credit, has an unrelated bank fee debit instead
        bank_rows.append({
            "bank_txn_id": bnk_id,
            "txn_date": settle_date.isoformat(),
            "description": f"MISC BANK CHARGES UNRELATED",
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
            "explanation": "Exception: Expected settlement credit not found in bank statement past delay window.",
        })
        record_idx += 1

    # 10. GENUINE UNKNOWNS (1 record)
    # Honestly does not fit any heuristic or formula (mismatched amount, unknown reference)
    for i in range(1):
        order_id = f"ORD-2026-UNK-{record_idx:04d}"
        inv_id = f"INV-{record_idx:04d}"
        set_id = f"SET-{record_idx:04d}"
        bnk_id = f"BNK-{record_idx:04d}"
        utr = f"UTR-UNKNOWN-{record_idx}"

        inv_amount = Decimal("7777.00")
        set_amount = Decimal("5432.10")  # Arbitrary unexplained gap
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
            "explanation": "Exception: Genuine unknown exception. Mismatched amounts and references with no mathematical explanation.",
        })
        record_idx += 1

    return invoices, settlements, bank_rows, ground_truth


def save_csv(data: List[Dict[str, Any]], filepath: str) -> None:
    """Saves list of dicts to a CSV file."""
    if not data:
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    # Collect all unique fieldnames in order of appearance
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


def generate_synthetic_data(output_dir: str = "backend/synthetic-data") -> Dict[str, str]:
    """
    Main generator entrypoint. Generates 100 invoices, 100 settlements,
    100 bank statements and ground truth files in output_dir.
    """
    invoices, settlements, bank_rows, ground_truth = generate_dataset()

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


if __name__ == "__main__":
    out = generate_synthetic_data()
    print("Generated synthetic files successfully:")
    for k, v in out.items():
        print(f"  {k}: {v}")
