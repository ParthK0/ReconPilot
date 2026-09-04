"""
generate_verification_batch.py — Generates a 1,000-entry verification dataset matching ReconPilot's
exact 86% / 6% / 8% architecture, with two side-by-side variants:
  1. Clean Variant (Canonical Schema for Phase 1 direct ingestion)
  2. Messy Variant (Wild Real-World Schema: aliased headers, mixed dates, dirty currency, buried UTRs)

Categories (1,000 records total):
  - 86% Rule Matches (860 records):
      * Exact match (immediate T+2): 500
      * Fee/GST/TDS-adjusted match: 230
      * Extended window (T+3–T+7 delay): 60
      * Penny-tolerance (±₹2 rounding): 40
      * FX spread corridor: 30
  - 6% AI Residual Matches (60 records):
      * Non-standard fee override (chargebacks, manual gateway adjustments): 60
  - 8% Honest Exceptions (80 records):
      * Duplicate invoice (2 invoice rows for same order_id): 15
      * Partial refund (debit/reduced amount): 15
      * Orphan invoice (abandoned checkout, invoice only): 20
      * Orphan settlement (escrow/held funds, invoice + settlement, no bank): 15
      * Orphan bank credit (direct tax, interest, bank fees, bank only): 15
"""

import argparse
import csv
import hashlib
import json
import os
import random
import sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repository root is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))


def round_curr(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def make_rzp_id(prefix: str, idx: int) -> str:
    """Generate authentic 14-character alphanumeric Razorpay identifier (e.g. order_BpeXOOhGKxA448)."""
    h = hashlib.sha256(f"{prefix}-{idx}".encode()).hexdigest()
    body = "".join(CHARS[int(h[i * 2 : i * 2 + 2], 16) % len(CHARS)] for i in range(14))
    return f"{prefix}_{body}"


def make_utr(d: date, idx: int) -> str:
    """Generate authentic Indian banking nodal UTR from Axis, HDFC, or ICICI."""
    prefixes = ["UTIB00026", "HDFCR52026", "ICICR42026"]
    pfx = prefixes[idx % len(prefixes)]
    return f"{pfx}{d.strftime('%m%d')}{idx:06d}"


def make_bank_narration(utr: str, idx: int, messy: bool = False) -> str:
    """Authentic Indian bank statement narrations for Razorpay nodal disbursements."""
    if messy and (idx % 3 == 0):
        # Bury UTR in complex string
        return f"NEFT/CMS/000987654321/RAZORPAY NODAL/{utr}/MUMBAI"
    narrations = [
        f"NEFT CR-RAZORPAY SOFTWARE PRIVATE LIMITED-{utr}-CMS",
        f"ACH CR-RAZORPAY SOFTWARE PVT LTD-{utr}-SETTLEMENT",
        f"RTGS CR-RAZORPAY NODAL A/C-{utr}-PAYOUT",
        f"CMS/000987654321/RAZORPAY SOFTWARE/{utr}",
    ]
    return narrations[idx % len(narrations)]


FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
    "Diya", "Saanvi", "Ananya", "Aadhya", "Pari", "Chiara", "Riya", "Myra", "Anushka", "Navya",
    "Rohan", "Kabir", "Meera", "Pooja", "Vikram", "Suresh", "Kavita", "Deepak", "Sneha", "Tanvi"
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Mehta", "Iyer", "Nair", "Reddy", "Rao", "Gupta", "Deshmukh",
    "Kulkarni", "Singh", "Chopra", "Malhotra", "Kapoor", "Bhatt", "Joshi", "Bose", "Chatterjee", "Menon",
    "Agrawal", "Bansal", "Saxena", "Choudhury", "Pillai", "Shetty", "Hebbar", "Dubey", "Tiwari", "Yadav"
]


def random_customer(idx: int) -> str:
    fn = FIRST_NAMES[idx % len(FIRST_NAMES)]
    ln = LAST_NAMES[(idx // len(FIRST_NAMES)) % len(LAST_NAMES)]
    return f"{fn} {ln}"


def format_messy_date(d: date, idx: int) -> str:
    """Randomly format date in varied real-world Indian formats."""
    styles = [
        "%d/%m/%Y",       # 12/08/2026 (standard Indian bank format)
        "%Y-%m-%d",       # 2026-08-12 (ISO)
        "%d-%b-%Y",       # 12-Aug-2026 (ERP Tally format)
        "%Y/%m/%d",       # 2026/08/12 (POS machine format)
        "%d-%m-%Y",       # 12-08-2026
    ]
    fmt = styles[idx % len(styles)]
    return d.strftime(fmt)


def format_messy_currency(amount: Decimal, idx: int) -> str:
    """Add realistic Indian merchant currency formatting: ₹, commas, INR suffixes."""
    style_num = idx % 5
    if style_num == 0:
        return f"₹ {amount:,.2f}"
    elif style_num == 1:
        return f"₹{amount:,.2f}"
    elif style_num == 2:
        return f"{amount:,.2f} INR"
    elif style_num == 3:
        return f" {amount:,.2f} "  # trailing whitespace
    else:
        return f"{amount:.2f}"


def build_raw_data(seed: int = 42) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generates the master 1,000-record dataset according to the 86/6/8 split."""
    random.seed(seed)

    invoices: List[Dict[str, Any]] = []
    settlements: List[Dict[str, Any]] = []
    bank_statements: List[Dict[str, Any]] = []
    ground_truth: List[Dict[str, Any]] = []

    base_date = date(2026, 8, 1)
    running_balance = Decimal("2500000.00")
    rec_id = 1

    MDR_RATE = Decimal("0.02")
    GST_RATE = Decimal("0.18")
    TDS_RATE = Decimal("0.01")

    def get_amount(idx: int) -> Decimal:
        base = Decimal("850.00") + Decimal(str((idx * 47) % 84150))
        return round_curr(base)

    # 1. Exact match (500 records)
    for i in range(500):
        order_id = make_rzp_id("order", rec_id)
        payment_id = make_rzp_id("pay", rec_id)
        inv_id = f"INV/2026-27/{rec_id:06d}"
        bnk_id = f"TXN202608{rec_id:06d}"
        txn_date = base_date + timedelta(days=(i % 25))
        settle_date = txn_date + timedelta(days=2)
        utr = make_utr(settle_date, rec_id)
        amount = get_amount(rec_id)
        running_balance = round_curr(running_balance + amount)

        invoices.append({
            "invoice_id": inv_id, "order_id": order_id, "amount": amount,
            "invoice_date": txn_date, "customer_name": random_customer(rec_id), "status": "paid",
        })
        settlements.append({
            "settlement_id": payment_id, "order_id": order_id, "amount": amount,
            "settlement_date": settle_date, "reference_number": utr, "status": "settled",
            "fees": Decimal("0.00"), "gst": Decimal("0.00"), "tds": Decimal("0.00"),
        })
        bank_statements.append({
            "bank_txn_id": bnk_id, "txn_date": settle_date, "description": make_bank_narration(utr, rec_id),
            "reference_number": utr, "amount": amount, "balance": running_balance, "status": "credited",
        })
        ground_truth.append({
            "type": "exact_match", "order_id": order_id, "payment_id": payment_id, "amount": str(amount), "rule": "exact_order_id",
        })
        rec_id += 1

    # 2. Fee / GST / TDS adjusted (230 records)
    for i in range(230):
        order_id = make_rzp_id("order", rec_id)
        payment_id = make_rzp_id("pay", rec_id)
        inv_id = f"INV/2026-27/{rec_id:06d}"
        bnk_id = f"TXN202608{rec_id:06d}"
        txn_date = base_date + timedelta(days=(i % 25))
        settle_date = txn_date + timedelta(days=2)
        utr = make_utr(settle_date, rec_id)
        gross_amount = get_amount(rec_id)
        fee = round_curr(gross_amount * MDR_RATE)
        gst = round_curr(fee * GST_RATE)
        tds = round_curr(gross_amount * TDS_RATE) if (i % 2 == 0) else Decimal("0.00")
        net_amount = round_curr(gross_amount - fee - gst - tds)
        running_balance = round_curr(running_balance + net_amount)

        invoices.append({
            "invoice_id": inv_id, "order_id": order_id, "amount": gross_amount,
            "invoice_date": txn_date, "customer_name": random_customer(rec_id), "status": "paid",
        })
        settlements.append({
            "settlement_id": payment_id, "order_id": order_id, "amount": net_amount,
            "settlement_date": settle_date, "reference_number": utr, "status": "settled",
            "fees": fee, "gst": gst, "tds": tds,
        })
        bank_statements.append({
            "bank_txn_id": bnk_id, "txn_date": settle_date, "description": make_bank_narration(utr, rec_id),
            "reference_number": utr, "amount": net_amount, "balance": running_balance, "status": "credited",
        })
        ground_truth.append({
            "type": "fee_gst_tds_adjusted", "order_id": order_id, "payment_id": payment_id,
            "gross": str(gross_amount), "net": str(net_amount), "rule": "fee_gst_tds_adjusted_amount",
        })
        rec_id += 1

    # 3. Extended window (T+3 to T+7 delay) (60 records)
    for i in range(60):
        order_id = make_rzp_id("order", rec_id)
        payment_id = make_rzp_id("pay", rec_id)
        inv_id = f"INV/2026-27/{rec_id:06d}"
        bnk_id = f"TXN202608{rec_id:06d}"
        txn_date = base_date + timedelta(days=(i % 20))
        delay_days = 3 + (i % 5)  # 3, 4, 5, 6, 7 days
        settle_date = txn_date + timedelta(days=delay_days)
        utr = make_utr(settle_date, rec_id)
        amount = get_amount(rec_id)
        running_balance = round_curr(running_balance + amount)

        invoices.append({
            "invoice_id": inv_id, "order_id": order_id, "amount": amount,
            "invoice_date": txn_date, "customer_name": random_customer(rec_id), "status": "paid",
        })
        settlements.append({
            "settlement_id": payment_id, "order_id": order_id, "amount": amount,
            "settlement_date": settle_date, "reference_number": utr, "status": "settled",
            "fees": Decimal("0.00"), "gst": Decimal("0.00"), "tds": Decimal("0.00"),
        })
        bank_statements.append({
            "bank_txn_id": bnk_id, "txn_date": settle_date, "description": make_bank_narration(utr, rec_id),
            "reference_number": utr, "amount": amount, "balance": running_balance, "status": "credited",
        })
        ground_truth.append({
            "type": "extended_window", "order_id": order_id, "delay_days": delay_days, "rule": "extended_window_tolerance",
        })
        rec_id += 1

    # 4. Penny tolerance (±₹0.50 to ±₹2.00 rounding) (40 records)
    for i in range(40):
        order_id = make_rzp_id("order", rec_id)
        payment_id = make_rzp_id("pay", rec_id)
        inv_id = f"INV/2026-27/{rec_id:06d}"
        bnk_id = f"TXN202608{rec_id:06d}"
        txn_date = base_date + timedelta(days=(i % 25))
        settle_date = txn_date + timedelta(days=2)
        utr = make_utr(settle_date, rec_id)
        amount = get_amount(rec_id)
        diff = Decimal("0.50") if (i % 2 == 0) else Decimal("-1.25")
        settle_amount = round_curr(amount + diff)
        running_balance = round_curr(running_balance + settle_amount)

        invoices.append({
            "invoice_id": inv_id, "order_id": order_id, "amount": amount,
            "invoice_date": txn_date, "customer_name": random_customer(rec_id), "status": "paid",
        })
        settlements.append({
            "settlement_id": payment_id, "order_id": order_id, "amount": settle_amount,
            "settlement_date": settle_date, "reference_number": utr, "status": "settled",
            "fees": Decimal("0.00"), "gst": Decimal("0.00"), "tds": Decimal("0.00"),
        })
        bank_statements.append({
            "bank_txn_id": bnk_id, "txn_date": settle_date, "description": make_bank_narration(utr, rec_id),
            "reference_number": utr, "amount": settle_amount, "balance": running_balance, "status": "credited",
        })
        ground_truth.append({
            "type": "penny_tolerance", "order_id": order_id, "diff": str(diff), "rule": "penny_tolerance",
        })
        rec_id += 1

    # 5. FX spread corridor (30 records)
    for i in range(30):
        order_id = make_rzp_id("order", rec_id)
        payment_id = make_rzp_id("pay", rec_id)
        inv_id = f"INV/2026-27/{rec_id:06d}"
        bnk_id = f"TXN202608{rec_id:06d}"
        txn_date = base_date + timedelta(days=(i % 25))
        settle_date = txn_date + timedelta(days=3)
        utr = make_utr(settle_date, rec_id)
        amount = get_amount(rec_id)
        # 1.5% FX corridor conversion buffer
        fx_deduction = round_curr(amount * Decimal("0.015"))
        settle_amount = round_curr(amount - fx_deduction)
        running_balance = round_curr(running_balance + settle_amount)

        invoices.append({
            "invoice_id": inv_id, "order_id": order_id, "amount": amount,
            "invoice_date": txn_date, "customer_name": random_customer(rec_id), "status": "paid",
        })
        settlements.append({
            "settlement_id": payment_id, "order_id": order_id, "amount": settle_amount,
            "settlement_date": settle_date, "reference_number": utr, "status": "settled",
            "fees": fx_deduction, "gst": Decimal("0.00"), "tds": Decimal("0.00"),
        })
        bank_statements.append({
            "bank_txn_id": bnk_id, "txn_date": settle_date, "description": make_bank_narration(utr, rec_id),
            "reference_number": utr, "amount": settle_amount, "balance": running_balance, "status": "credited",
        })
        ground_truth.append({
            "type": "fx_spread_corridor", "order_id": order_id, "fx_spread": str(fx_deduction), "rule": "fx_conversion_corridor",
        })
        rec_id += 1

    # 6. Non-standard fee override (AI-residual — 60 records)
    for i in range(60):
        order_id = make_rzp_id("order", rec_id)
        payment_id = make_rzp_id("pay", rec_id)
        inv_id = f"INV/2026-27/{rec_id:06d}"
        bnk_id = f"TXN202608{rec_id:06d}"
        txn_date = base_date + timedelta(days=(i % 25))
        settle_date = txn_date + timedelta(days=2)
        utr = make_utr(settle_date, rec_id)
        gross_amount = get_amount(rec_id)
        # Non-standard manual flat override (₹45, ₹75, ₹120)
        custom_fee = Decimal(str(45.0 + (i % 6) * 15.0))
        net_amount = round_curr(gross_amount - custom_fee)
        running_balance = round_curr(running_balance + net_amount)

        invoices.append({
            "invoice_id": inv_id, "order_id": order_id, "amount": gross_amount,
            "invoice_date": txn_date, "customer_name": random_customer(rec_id), "status": "paid",
        })
        settlements.append({
            "settlement_id": payment_id, "order_id": order_id, "amount": net_amount,
            "settlement_date": settle_date, "reference_number": utr, "status": "settled",
            "fees": custom_fee, "gst": Decimal("0.00"), "tds": Decimal("0.00"),
        })
        bank_statements.append({
            "bank_txn_id": bnk_id, "txn_date": settle_date, "description": make_bank_narration(utr, rec_id),
            "reference_number": utr, "amount": net_amount, "balance": running_balance, "status": "credited",
        })
        ground_truth.append({
            "type": "non_standard_fee_override", "order_id": order_id, "custom_fee": str(custom_fee), "resolution": "ai_verification",
        })
        rec_id += 1

    # 7. Duplicate invoice (15 records) - 2 invoices, 1 settlement, 1 bank
    for i in range(15):
        order_id = make_rzp_id("order", rec_id)
        payment_id = make_rzp_id("pay", rec_id)
        inv_id1 = f"INV/2026-27/{rec_id:06d}"
        inv_id2 = f"INV/2026-27/{rec_id:06d}-DUP"
        bnk_id = f"TXN202608{rec_id:06d}"
        txn_date = base_date + timedelta(days=(i % 25))
        settle_date = txn_date + timedelta(days=2)
        utr = make_utr(settle_date, rec_id)
        amount = get_amount(rec_id)
        running_balance = round_curr(running_balance + amount)

        # 2 Invoice rows
        invoices.append({
            "invoice_id": inv_id1, "order_id": order_id, "amount": amount,
            "invoice_date": txn_date, "customer_name": random_customer(rec_id), "status": "paid",
        })
        invoices.append({
            "invoice_id": inv_id2, "order_id": order_id, "amount": amount,
            "invoice_date": txn_date, "customer_name": f"{random_customer(rec_id)} (DUP)", "status": "paid",
        })
        settlements.append({
            "settlement_id": payment_id, "order_id": order_id, "amount": amount,
            "settlement_date": settle_date, "reference_number": utr, "status": "settled",
            "fees": Decimal("0.00"), "gst": Decimal("0.00"), "tds": Decimal("0.00"),
        })
        bank_statements.append({
            "bank_txn_id": bnk_id, "txn_date": settle_date, "description": make_bank_narration(utr, rec_id),
            "reference_number": utr, "amount": amount, "balance": running_balance, "status": "credited",
        })
        ground_truth.append({
            "type": "duplicate_invoice", "order_id": order_id, "resolution": "exception",
        })
        rec_id += 1

    # 8. Partial refund (15 records)
    for i in range(15):
        order_id = make_rzp_id("order", rec_id)
        payment_id = make_rzp_id("pay", rec_id)
        inv_id = f"INV/2026-27/{rec_id:06d}"
        bnk_id = f"TXN202608{rec_id:06d}"
        txn_date = base_date + timedelta(days=(i % 25))
        settle_date = txn_date + timedelta(days=2)
        utr = make_utr(settle_date, rec_id)
        gross_amount = get_amount(rec_id)
        refund_amount = round_curr(gross_amount * Decimal("0.50"))
        net_credit = round_curr(gross_amount - refund_amount)
        running_balance = round_curr(running_balance + net_credit)

        invoices.append({
            "invoice_id": inv_id, "order_id": order_id, "amount": gross_amount,
            "invoice_date": txn_date, "customer_name": random_customer(rec_id), "status": "refunded",
        })
        settlements.append({
            "settlement_id": payment_id, "order_id": order_id, "amount": net_credit,
            "settlement_date": settle_date, "reference_number": utr, "status": "refund_processed",
            "fees": Decimal("0.00"), "gst": Decimal("0.00"), "tds": Decimal("0.00"),
        })
        bank_statements.append({
            "bank_txn_id": bnk_id, "txn_date": settle_date, "description": f"ACH DR RAZORPAY PARTIAL REFUND {utr}",
            "reference_number": utr, "amount": net_credit, "balance": running_balance, "status": "credited",
        })
        ground_truth.append({
            "type": "partial_refund", "order_id": order_id, "refund_amount": str(refund_amount), "resolution": "exception",
        })
        rec_id += 1

    # 9. Orphan invoice (20 records) - Invoices only
    for i in range(20):
        order_id = make_rzp_id("order", rec_id)
        inv_id = f"INV/2026-27/{rec_id:06d}"
        txn_date = base_date + timedelta(days=(i % 25))
        amount = get_amount(rec_id)

        invoices.append({
            "invoice_id": inv_id, "order_id": order_id, "amount": amount,
            "invoice_date": txn_date, "customer_name": random_customer(rec_id), "status": "unpaid",
        })
        ground_truth.append({
            "type": "orphan_invoice", "order_id": order_id, "resolution": "exception", "notes": "Abandoned checkout",
        })
        rec_id += 1

    # 10. Orphan settlement (15 records) - Invoice + Settlement, missing Bank
    for i in range(15):
        order_id = make_rzp_id("order", rec_id)
        payment_id = make_rzp_id("pay", rec_id)
        inv_id = f"INV/2026-27/{rec_id:06d}"
        txn_date = base_date + timedelta(days=(i % 25))
        settle_date = txn_date + timedelta(days=2)
        utr = make_utr(settle_date, rec_id)
        amount = get_amount(rec_id)

        invoices.append({
            "invoice_id": inv_id, "order_id": order_id, "amount": amount,
            "invoice_date": txn_date, "customer_name": random_customer(rec_id), "status": "paid",
        })
        settlements.append({
            "settlement_id": payment_id, "order_id": order_id, "amount": amount,
            "settlement_date": settle_date, "reference_number": utr, "status": "settled",
            "fees": Decimal("0.00"), "gst": Decimal("0.00"), "tds": Decimal("0.00"),
        })
        ground_truth.append({
            "type": "orphan_settlement", "order_id": order_id, "resolution": "exception", "notes": "Chargeback / held funds",
        })
        rec_id += 1

    # 11. Orphan bank credit (15 records) - Bank only
    bank_reasons = [
        ("CHG: CONSOLIDATED ACCOUNT MAINTENANCE CHARGES", False),
        ("INT.PD: 01-07-2026 TO 30-09-2026 ACCRUED INTEREST", True),
        ("NEFT DR-DIRECT TAXES CHALLAN 281 TDS PAYMENT", False),
        ("ECS/NACH DR-OFFICE LEASE AUTOMATED DEBIT", False),
    ]
    for i in range(15):
        bnk_id = f"TXN202608{rec_id:06d}"
        desc, is_credit = bank_reasons[i % len(bank_reasons)]
        amount = round_curr(Decimal(str(random.randint(500, 45000))))
        if not is_credit:
            running_balance = round_curr(running_balance - amount)
            status = "debited"
            amt_dec = -amount
        else:
            running_balance = round_curr(running_balance + amount)
            status = "credited"
            amt_dec = amount

        bank_statements.append({
            "bank_txn_id": bnk_id, "txn_date": (base_date + timedelta(days=i * 2)),
            "description": desc, "reference_number": f"CHG-{rec_id:06d}",
            "amount": amt_dec, "balance": running_balance, "status": status,
        })
        ground_truth.append({
            "type": "orphan_bank_credit", "resolution": "exception", "notes": f"Bank only: {desc}",
        })
        rec_id += 1

    return invoices, settlements, bank_statements, ground_truth


def save_clean_variant(
    invoices: List[Dict[str, Any]],
    settlements: List[Dict[str, Any]],
    bank_statements: List[Dict[str, Any]],
    ground_truth: List[Dict[str, Any]],
    output_dir: Path,
):
    """Saves clean variant with exact canonical schema matching EXPECTED_COLUMNS."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Shuffled copies
    shuffled_inv = list(invoices)
    shuffled_set = list(settlements)
    shuffled_bnk = list(bank_statements)
    random.shuffle(shuffled_inv)
    random.shuffle(shuffled_set)
    random.shuffle(shuffled_bnk)

    # Invoices
    with open(output_dir / "invoices.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["invoice_id", "order_id", "amount", "invoice_date", "customer_name", "status"])
        w.writeheader()
        for r in shuffled_inv:
            w.writerow({
                "invoice_id": r["invoice_id"],
                "order_id": r["order_id"],
                "amount": f"{r['amount']:.2f}",
                "invoice_date": r["invoice_date"].isoformat(),
                "customer_name": r["customer_name"],
                "status": r["status"],
            })

    # Settlements
    with open(output_dir / "settlements.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["settlement_id", "order_id", "amount", "settlement_date", "reference_number", "status", "fees", "gst", "tds"])
        w.writeheader()
        for r in shuffled_set:
            w.writerow({
                "settlement_id": r["settlement_id"],
                "order_id": r["order_id"],
                "amount": f"{r['amount']:.2f}",
                "settlement_date": r["settlement_date"].isoformat(),
                "reference_number": r["reference_number"],
                "status": r["status"],
                "fees": f"{r['fees']:.2f}",
                "gst": f"{r['gst']:.2f}",
                "tds": f"{r['tds']:.2f}",
            })

    # Bank Statements
    with open(output_dir / "bank_statements.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["bank_txn_id", "txn_date", "description", "reference_number", "amount", "balance", "status"])
        w.writeheader()
        for r in shuffled_bnk:
            w.writerow({
                "bank_txn_id": r["bank_txn_id"],
                "txn_date": r["txn_date"].isoformat(),
                "description": r["description"],
                "reference_number": r["reference_number"],
                "amount": f"{r['amount']:.2f}",
                "balance": f"{r['balance']:.2f}",
                "status": r["status"],
            })

    with open(output_dir / "verification_guide.json", "w", encoding="utf-8") as f:
        json.dump({
            "variant": "clean",
            "counts": {"invoices": len(invoices), "settlements": len(settlements), "bank": len(bank_statements)},
            "ground_truth": ground_truth,
        }, f, indent=2)


def save_messy_variant(
    invoices: List[Dict[str, Any]],
    settlements: List[Dict[str, Any]],
    bank_statements: List[Dict[str, Any]],
    ground_truth: List[Dict[str, Any]],
    output_dir: Path,
):
    """
    Saves messy variant with:
    - Aliased headers: (bill_no, order_number, billed_amount, bill_date; payout_id, net_payout, payout_date; entry_id, posting_date, txn_amount)
    - Mixed date formats: DD/MM/YYYY, YYYY-MM-DD, DD-Mon-YYYY
    - Dirty currency amounts: ₹ 12,499.00, 12499.00 INR, extra commas/whitespace
    - Buried UTRs in description
    - Mixed status casing: PAID, Settled, Credited
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    shuffled_inv = list(invoices)
    shuffled_set = list(settlements)
    shuffled_bnk = list(bank_statements)
    random.shuffle(shuffled_inv)
    random.shuffle(shuffled_set)
    random.shuffle(shuffled_bnk)

    # Invoices (Aliased headers: bill_no, order_number, billed_amount, bill_date, customer_name, order_status)
    with open(output_dir / "invoices.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["bill_no", "order_number", "billed_amount", "bill_date", "customer_name", "order_status"])
        w.writeheader()
        for idx, r in enumerate(shuffled_inv):
            w.writerow({
                "bill_no": r["invoice_id"],
                "order_number": r["order_id"],
                "billed_amount": format_messy_currency(r["amount"], idx),
                "bill_date": format_messy_date(r["invoice_date"], idx),
                "customer_name": r["customer_name"],
                "order_status": r["status"].upper() if (idx % 2 == 0) else r["status"].capitalize(),
            })

    # Settlements (Aliased headers: payout_id, order_number, net_payout, payout_date, utr_number, state, mdr, service_tax, tds_deducted)
    with open(output_dir / "settlements.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["payout_id", "order_number", "net_payout", "payout_date", "utr_number", "state", "mdr", "service_tax", "tds_deducted"])
        w.writeheader()
        for idx, r in enumerate(shuffled_set):
            w.writerow({
                "payout_id": r["settlement_id"],
                "order_number": r["order_id"],
                "net_payout": format_messy_currency(r["amount"], idx + 1),
                "payout_date": format_messy_date(r["settlement_date"], idx + 1),
                "utr_number": r["reference_number"],
                "state": r["status"].upper() if (idx % 2 == 0) else r["status"].capitalize(),
                "mdr": format_messy_currency(r["fees"], idx),
                "service_tax": format_messy_currency(r["gst"], idx),
                "tds_deducted": format_messy_currency(r["tds"], idx),
            })

    # Bank Statements (Aliased headers: entry_id, posting_date, memo, utr_number, txn_amount, account_balance, state)
    with open(output_dir / "bank_statements.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["entry_id", "posting_date", "memo", "utr_number", "txn_amount", "account_balance", "state"])
        w.writeheader()
        for idx, r in enumerate(shuffled_bnk):
            # Bury UTR in description for 30% of rows (and leave utr column empty or messy)
            buried = (idx % 3 == 0)
            utr_val = "" if buried else r["reference_number"]
            w.writerow({
                "entry_id": r["bank_txn_id"],
                "posting_date": format_messy_date(r["txn_date"], idx + 2),
                "memo": make_bank_narration(r["reference_number"], idx, messy=True),
                "utr_number": utr_val,
                "txn_amount": format_messy_currency(r["amount"], idx + 2),
                "account_balance": format_messy_currency(r["balance"], idx),
                "state": r["status"].upper() if (idx % 2 == 0) else r["status"].capitalize(),
            })

    with open(output_dir / "verification_guide.json", "w", encoding="utf-8") as f:
        json.dump({
            "variant": "messy_real_world",
            "counts": {"invoices": len(invoices), "settlements": len(settlements), "bank": len(bank_statements)},
            "ground_truth": ground_truth,
        }, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Generate 1,000-entry verification datasets matching 86/6/8 architecture.")
    args = parser.parse_args()

    clean_dir = PROJECT_ROOT / "backend/verification_batch_clean"
    messy_dir = PROJECT_ROOT / "backend/verification_batch_messy"

    print("=" * 72)
    print("Generating ReconPilot 86/6/8 Verification Datasets (1,000 Records)")
    print("=" * 72)

    inv, setts, bnk, gt = build_raw_data(seed=42)

    print("\n1. Saving Clean Variant -> backend/verification_batch_clean/")
    save_clean_variant(inv, setts, bnk, gt, clean_dir)
    print(f"   * Invoices:        {len(inv):,} rows (Canonical schema)")
    print(f"   * Settlements:     {len(setts):,} rows (Canonical schema)")
    print(f"   * Bank Statements: {len(bnk):,} rows (Canonical schema)")

    print("\n2. Saving Real-World Messy Variant -> backend/verification_batch_messy/")
    save_messy_variant(inv, setts, bnk, gt, messy_dir)
    print(f"   * Invoices:        {len(inv):,} rows (Aliased headers, mixed dates, Rs. symbols)")
    print(f"   * Settlements:     {len(setts):,} rows (Aliased headers, mixed dates, Rs. symbols)")
    print(f"   * Bank Statements: {len(bnk):,} rows (Aliased headers, buried UTRs in memo, Rs. symbols)")

    print("\n" + "=" * 72)
    print("Architecture Summary (Exact 86/6/8 Split):")
    print("  - Rule Matches (86.0%):")
    print("      * Exact Matches (T+2)            : 500")
    print("      * Fee / GST / TDS Matches        : 230")
    print("      * Extended Window (T+3..T+7)     :  60")
    print("      * Penny Tolerance (+/- Rs 2)     :  40")
    print("      * FX Spread Corridor (1.5%)      :  30")
    print("  - AI-Verified Residuals (6.0%):")
    print("      * Non-standard manual fees       :  60")
    print("  - Honest Exceptions (8.0%):")
    print("      * Duplicate Invoices             :  15")
    print("      * Partial Refunds                :  15")
    print("      * Orphan Invoices (abandoned)    :  20")
    print("      * Orphan Settlements (held/escrow):  15")
    print("      * Orphan Bank Credits (taxes/fees): 15")
    print("  Total Volume: 1,000 transaction flows")
    print("=" * 72)


if __name__ == "__main__":
    main()
