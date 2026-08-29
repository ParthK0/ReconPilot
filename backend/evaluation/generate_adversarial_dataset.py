"""
backend/evaluation/generate_adversarial_dataset.py
==================================================
Generates an independent adversarial evaluation dataset matching ground_truth schema.
"""

import os
import json
import random
from decimal import Decimal
from datetime import date, timedelta
import pandas as pd


def generate_adversarial_data(output_dir: str = "backend/evaluation/adversarial_dataset", count: int = 100):
    os.makedirs(output_dir, exist_ok=True)
    random.seed(42)

    invoices = []
    settlements = []
    bank_rows = []
    ground_truth = []

    base_date = date(2026, 8, 1)

    for i in range(1, count + 1):
        order_id = f"ORD-ADV-{i:04d}"
        inv_id = f"INV-ADV-{i:04d}"
        settle_id = f"SET-ADV-{i:04d}"
        bank_id = f"BNK-ADV-{i:04d}"
        utr = f"UTR-ADV-{i:04d}{random.randint(1000, 9999)}"

        gross_amount = Decimal(str(random.randint(1000, 50000))) + Decimal("0.00")
        txn_date = base_date + timedelta(days=(i % 15))

        if i <= 60:
            # 1. Exact Match
            invoices.append({
                "invoice_id": inv_id,
                "order_id": order_id,
                "amount": float(gross_amount),
                "invoice_date": txn_date.isoformat(),
                "customer_name": f"Enterprise Client {i}",
                "status": "paid",
            })
            settlements.append({
                "settlement_id": settle_id,
                "order_id": order_id,
                "amount": float(gross_amount),
                "settlement_date": (txn_date + timedelta(days=1)).isoformat(),
                "reference_number": utr,
                "status": "settled",
                "fees": 0.0,
                "gst": 0.0,
                "tds": 0.0,
            })
            bank_rows.append({
                "bank_txn_id": bank_id,
                "txn_date": (txn_date + timedelta(days=1)).isoformat(),
                "description": f"NEFT CR - RAZORPAY - {utr}",
                "reference_number": utr,
                "amount": float(gross_amount),
                "balance": 1500000.00,
                "status": "credited",
            })
            ground_truth.append({
                "scenario_id": f"SCENARIO-ADV-{i:04d}",
                "category": "exact_match",
                "expected_resolution": "rule",
                "expected_rule": "exact_order_id",
                "order_id": order_id,
                "invoice_id": inv_id,
                "settlement_id": settle_id,
                "bank_txn_id": bank_id,
                "reference_number": utr,
                "invoice_amount": str(gross_amount),
                "settlement_amount": str(gross_amount),
                "bank_amount": str(gross_amount),
                "explanation": "Exact match across order ID and amount.",
            })

        elif i <= 75:
            # 2. Fee Adjusted Match (2% MDR + 18% GST + 1% TDS)
            fees = (gross_amount * Decimal("0.02")).quantize(Decimal("0.01"))
            gst = (fees * Decimal("0.18")).quantize(Decimal("0.01"))
            tds = (gross_amount * Decimal("0.01")).quantize(Decimal("0.01"))
            net_amount = gross_amount - fees - gst - tds

            invoices.append({
                "invoice_id": inv_id,
                "order_id": order_id,
                "amount": float(gross_amount),
                "invoice_date": txn_date.isoformat(),
                "customer_name": f"Retail Buyer {i}",
                "status": "paid",
            })
            settlements.append({
                "settlement_id": settle_id,
                "order_id": order_id,
                "amount": float(net_amount),
                "settlement_date": (txn_date + timedelta(days=1)).isoformat(),
                "reference_number": utr,
                "status": "settled",
                "fees": float(fees),
                "gst": float(gst),
                "tds": float(tds),
            })
            bank_rows.append({
                "bank_txn_id": bank_id,
                "txn_date": (txn_date + timedelta(days=1)).isoformat(),
                "description": f"CMS CR - RAZORPAY - {utr}",
                "reference_number": utr,
                "amount": float(net_amount),
                "balance": 1500000.00,
                "status": "credited",
            })
            ground_truth.append({
                "scenario_id": f"SCENARIO-ADV-{i:04d}",
                "category": "fee_gst_tds_adjusted",
                "expected_resolution": "rule",
                "expected_rule": "fee_gst_tds_adjusted_amount",
                "order_id": order_id,
                "invoice_id": inv_id,
                "settlement_id": settle_id,
                "bank_txn_id": bank_id,
                "reference_number": utr,
                "invoice_amount": str(gross_amount),
                "settlement_amount": str(net_amount),
                "bank_amount": str(net_amount),
                "explanation": "Standard MDR fee and statutory tax deduction schedule.",
            })

        elif i <= 85:
            # 3. Tolerance Match (+/- Rs 0.50 to Rs 1.80)
            noise = Decimal(str(random.choice([-1.50, -0.75, 0.50, 1.25, -1.80])))
            settle_amt = gross_amount + noise

            invoices.append({
                "invoice_id": inv_id,
                "order_id": order_id,
                "amount": float(gross_amount),
                "invoice_date": txn_date.isoformat(),
                "customer_name": f"Subscriber {i}",
                "status": "paid",
            })
            settlements.append({
                "settlement_id": settle_id,
                "order_id": order_id,
                "amount": float(settle_amt),
                "settlement_date": (txn_date + timedelta(days=1)).isoformat(),
                "reference_number": utr,
                "status": "settled",
                "fees": 0.0,
                "gst": 0.0,
                "tds": 0.0,
            })
            bank_rows.append({
                "bank_txn_id": bank_id,
                "txn_date": (txn_date + timedelta(days=1)).isoformat(),
                "description": f"NEFT CR - RAZORPAY - {utr}",
                "reference_number": utr,
                "amount": float(settle_amt),
                "balance": 1500000.00,
                "status": "credited",
            })
            ground_truth.append({
                "scenario_id": f"SCENARIO-ADV-{i:04d}",
                "category": "tolerance_match",
                "expected_resolution": "rule",
                "expected_rule": "tolerance_amount_match",
                "order_id": order_id,
                "invoice_id": inv_id,
                "settlement_id": settle_id,
                "bank_txn_id": bank_id,
                "reference_number": utr,
                "invoice_amount": str(gross_amount),
                "settlement_amount": str(settle_amt),
                "bank_amount": str(settle_amt),
                "explanation": "Matched within penny tolerance band.",
            })

        elif i <= 92:
            # 4. AI Edge Case (One-off fee Rs 30)
            one_off_fee = Decimal("30.00")
            settle_amt = gross_amount - one_off_fee

            invoices.append({
                "invoice_id": inv_id,
                "order_id": order_id,
                "amount": float(gross_amount),
                "invoice_date": txn_date.isoformat(),
                "customer_name": f"VIP Merchant {i}",
                "status": "paid",
            })
            settlements.append({
                "settlement_id": settle_id,
                "order_id": order_id,
                "amount": float(settle_amt),
                "settlement_date": (txn_date + timedelta(days=2)).isoformat(),
                "reference_number": utr,
                "status": "settled",
                "fees": float(one_off_fee),
                "gst": 0.0,
                "tds": 0.0,
            })
            bank_rows.append({
                "bank_txn_id": bank_id,
                "txn_date": (txn_date + timedelta(days=2)).isoformat(),
                "description": f"NEFT CR - RAZORPAY - {utr}",
                "reference_number": utr,
                "amount": float(settle_amt),
                "balance": 1500000.00,
                "status": "credited",
            })
            ground_truth.append({
                "scenario_id": f"SCENARIO-ADV-{i:04d}",
                "category": "non_standard_fee",
                "expected_resolution": "ai",
                "expected_rule": None,
                "order_id": order_id,
                "invoice_id": inv_id,
                "settlement_id": settle_id,
                "bank_txn_id": bank_id,
                "reference_number": utr,
                "invoice_amount": str(gross_amount),
                "settlement_amount": str(settle_amt),
                "bank_amount": str(settle_amt),
                "explanation": "One-off commercial fee adjustment verified by AI reasoning.",
            })

        elif i <= 96:
            # 5. Missing Settlement Gap Exception
            invoices.append({
                "invoice_id": inv_id,
                "order_id": order_id,
                "amount": float(gross_amount),
                "invoice_date": txn_date.isoformat(),
                "customer_name": f"Unsettled Buyer {i}",
                "status": "paid",
            })
            ground_truth.append({
                "scenario_id": f"SCENARIO-ADV-{i:04d}",
                "category": "missing_settlement",
                "expected_resolution": "exception",
                "expected_rule": None,
                "order_id": order_id,
                "invoice_id": inv_id,
                "settlement_id": None,
                "bank_txn_id": None,
                "reference_number": None,
                "invoice_amount": str(gross_amount),
                "settlement_amount": None,
                "bank_amount": None,
                "explanation": "Invoice marked paid without gateway settlement.",
            })

        else:
            # 6. Unmatched Bank Credit Gap Exception
            bank_rows.append({
                "bank_txn_id": bank_id,
                "txn_date": txn_date.isoformat(),
                "description": f"DIRECT IMPS CR - {utr}",
                "reference_number": utr,
                "amount": float(gross_amount),
                "balance": 1500000.00,
                "status": "credited",
            })
            ground_truth.append({
                "scenario_id": f"SCENARIO-ADV-{i:04d}",
                "category": "unmatched_bank_credit",
                "expected_resolution": "exception",
                "expected_rule": None,
                "order_id": None,
                "invoice_id": None,
                "settlement_id": None,
                "bank_txn_id": bank_id,
                "reference_number": utr,
                "invoice_amount": None,
                "settlement_amount": None,
                "bank_amount": str(gross_amount),
                "explanation": "Mystery bank credit without settlement tranche.",
            })

    # Export CSVs and ground truth
    pd.DataFrame(invoices).to_csv(os.path.join(output_dir, "invoices.csv"), index=False)
    pd.DataFrame(settlements).to_csv(os.path.join(output_dir, "settlements.csv"), index=False)
    pd.DataFrame(bank_rows).to_csv(os.path.join(output_dir, "bank_statements.csv"), index=False)

    with open(os.path.join(output_dir, "ground_truth.json"), "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"Generated adversarial dataset at '{output_dir}' with {len(invoices)} invoices, {len(settlements)} settlements, {len(bank_rows)} bank rows.")


if __name__ == "__main__":
    generate_adversarial_data()
