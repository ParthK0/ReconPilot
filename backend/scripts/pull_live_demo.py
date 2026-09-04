"""
pull_live_demo.py — CLI Runner that utilizes the RazorpayAdapter to synchronize
transactions from Razorpay Sandbox into canonical reconciliation batches.

Usage:
    python backend/scripts/pull_live_demo.py [--use-actual-fees] [--dry-run]

Outputs:
    backend/live_demo_data/settlements.csv
    backend/live_demo_data/invoices.csv
    backend/live_demo_data/bank_statements.csv
    backend/live_demo_data/live_demo_manifest.json
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Ensure paths relative to project root
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

SEED_OUTPUT_FILE = SCRIPT_DIR / "seed_output.json"
DATA_DIR = BACKEND_DIR / "live_demo_data"

# Load environment variables
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")

from backend.integrations.gateways.razorpay import RazorpayAdapter
from backend.integrations.base import IntegrationMode


def main():
    parser = argparse.ArgumentParser(description="Synchronize Razorpay sandbox transactions via RazorpayAdapter.")
    parser.add_argument(
        "--use-actual-fees",
        action="store_true",
        help="Use raw fees from Razorpay API instead of standard 2.0% MDR + 18% GST formula",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate captured payments for all seeded orders without waiting for manual checkout",
    )
    args = parser.parse_args()

    if not SEED_OUTPUT_FILE.exists():
        print(f"[ERROR] Seed output file not found: {SEED_OUTPUT_FILE}")
        print("Please run `python backend/scripts/seed_live_demo.py` first.")
        sys.exit(1)

    with open(SEED_OUTPUT_FILE, "r", encoding="utf-8") as f:
        seed_data = json.load(f)

    orders = seed_data.get("orders", [])
    if not orders:
        print("[ERROR] No orders found in seed_output.json.")
        sys.exit(1)

    adapter = RazorpayAdapter()

    print("=" * 72)
    print("ReconPilot -- Razorpay Transaction Synchronizer (Adapter Layer)")
    print(f"Provider:    {adapter.provider_name.upper()}")
    print(f"Mode:        {adapter.mode.value.upper()} MODE")
    print(f"Key ID:      {adapter.key_id}")
    print(f"Orders:      {len(orders)}")
    print("-" * 72)
    print("ARCHITECTURAL NOTICE:")
    print("  Demo bank statement generator for Razorpay Test Mode.")
    print("  Production deployments import actual bank statements via BankAdapter.")
    print("=" * 72)

    sync_result = adapter.sync_sandbox_batch(
        orders=orders,
        simulate_if_unpaid=args.dry_run,
        use_actual_fees=args.use_actual_fees,
    )

    if sync_result.status == "no_payments_found":
        print("\n[NOTICE] No captured payments found on Razorpay.")
        print("Please open the checkout URLs and complete payment with test card 4111 1111 1111 1111.")
        print("Or run with `--dry-run` to preview the synchronization.")
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    records = sync_result.records

    # Write CSVs
    settlements_path = DATA_DIR / "settlements.csv"
    with open(settlements_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "settlement_id", "order_id", "amount", "settlement_date", "reference_number", "status", "fees", "gst", "tds"
        ])
        w.writeheader()
        w.writerows(records["settlements"])

    invoices_path = DATA_DIR / "invoices.csv"
    with open(invoices_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "invoice_id", "order_id", "amount", "invoice_date", "customer_name", "status"
        ])
        w.writeheader()
        w.writerows(records["invoices"])

    bank_path = DATA_DIR / "bank_statements.csv"
    with open(bank_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "bank_txn_id", "txn_date", "description", "reference_number", "amount", "balance", "status"
        ])
        w.writeheader()
        w.writerows(records["bank_statements"])

    manifest = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "adapter": "RazorpayAdapter",
        "provider": "razorpay",
        "mode": adapter.mode.value,
        "is_dry_run": args.dry_run,
        "records_count": len(records["settlements"]),
        "notes": sync_result.notes,
    }
    manifest_path = DATA_DIR / "live_demo_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 72)
    print("SYNC SUCCESSFUL:")
    print(f"  * Settlements:     {len(records['settlements'])} records ({settlements_path.name})")
    print(f"  * Invoices:        {len(records['invoices'])} records ({invoices_path.name})")
    print(f"  * Bank Statements: {len(records['bank_statements'])} records ({bank_path.name})")
    print(f"  * Mode:            {adapter.mode.value.upper()}")
    print("=" * 72)


if __name__ == "__main__":
    main()
