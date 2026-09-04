"""
seed_live_demo.py — One-off script to seed live Razorpay Test Mode with SaaS subscription orders & payment links.

Usage:
    python backend/scripts/seed_live_demo.py [--force]

Outputs:
    backend/scripts/seed_output.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv

# Ensure paths relative to project root
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
OUTPUT_FILE = SCRIPT_DIR / "seed_output.json"

# Load environment variables
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"

# 5 realistic SaaS subscription tiers (amounts in paisa and INR)
SAAS_TIERS = [
    {
        "receipt": "RCPT-SAAS-001",
        "product": "ReconPilot Starter Monthly",
        "amount_paisa": 499900,
        "amount_inr": "4999.00",
        "customer_name": "Priya Sharma",
        "customer_email": "priya.sharma@cloudserve.in",
        "customer_phone": "+919876543210",
    },
    {
        "receipt": "RCPT-SAAS-002",
        "product": "ReconPilot Pro Monthly",
        "amount_paisa": 1249900,
        "amount_inr": "12499.00",
        "customer_name": "Vikram Malhotra",
        "customer_email": "vikram@finscale.io",
        "customer_phone": "+919812345678",
    },
    {
        "receipt": "RCPT-SAAS-003",
        "product": "ReconPilot Business Monthly",
        "amount_paisa": 2999900,
        "amount_inr": "29999.00",
        "customer_name": "Ananya Deshmukh",
        "customer_email": "ananya@datadrive.co",
        "customer_phone": "+919823456789",
    },
    {
        "receipt": "RCPT-SAAS-004",
        "product": "ReconPilot Enterprise Quarterly",
        "amount_paisa": 7499900,
        "amount_inr": "74999.00",
        "customer_name": "Rajesh Nambiar",
        "customer_email": "rajesh.n@apollologistics.in",
        "customer_phone": "+919834567890",
    },
    {
        "receipt": "RCPT-SAAS-005",
        "product": "ReconPilot Enterprise Annual",
        "amount_paisa": 14999900,
        "amount_inr": "149999.00",
        "customer_name": "Sunita Agarwal",
        "customer_email": "sunita.agarwal@zenithcorp.org",
        "customer_phone": "+919845678901",
    },
]


def create_order_and_link(
    client: httpx.Client,
    auth: tuple,
    tier: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a Razorpay Order and corresponding Payment Link."""
    # 1. Create Order
    order_payload = {
        "amount": tier["amount_paisa"],
        "currency": "INR",
        "receipt": tier["receipt"],
        "notes": {
            "product": tier["product"],
            "customer_name": tier["customer_name"],
            "customer_email": tier["customer_email"],
        },
    }
    order_resp = client.post(
        f"{RAZORPAY_API_BASE}/orders",
        json=order_payload,
        auth=auth,
        timeout=15.0,
    )
    if order_resp.status_code != 200:
        raise RuntimeError(
            f"Failed to create order for {tier['receipt']}: "
            f"{order_resp.status_code} {order_resp.text}"
        )
    order_data = order_resp.json()
    order_id = order_data["id"]

    # 2. Create Payment Link referencing this order
    link_payload = {
        "amount": tier["amount_paisa"],
        "currency": "INR",
        "accept_partial": False,
        "reference_id": order_id,
        "description": f"Subscription: {tier['product']}",
        "customer": {
            "name": tier["customer_name"],
            "email": tier["customer_email"],
            "contact": tier["customer_phone"],
        },
        "notify": {
            "sms": False,
            "email": False,
        },
        "reminder_enable": False,
        "notes": {
            "order_id": order_id,
            "receipt": tier["receipt"],
            "product": tier["product"],
        },
    }
    link_resp = client.post(
        f"{RAZORPAY_API_BASE}/payment_links",
        json=link_payload,
        auth=auth,
        timeout=15.0,
    )
    if link_resp.status_code != 200:
        raise RuntimeError(
            f"Failed to create payment link for {order_id}: "
            f"{link_resp.status_code} {link_resp.text}"
        )
    link_data = link_resp.json()

    return {
        "order_id": order_id,
        "payment_link_id": link_data["id"],
        "payment_link_url": link_data["short_url"],
        "receipt": tier["receipt"],
        "product": tier["product"],
        "amount_paisa": tier["amount_paisa"],
        "amount_inr": tier["amount_inr"],
        "customer_name": tier["customer_name"],
        "customer_email": tier["customer_email"],
        "customer_phone": tier["customer_phone"],
        "order_created_at": order_data.get("created_at"),
    }


def main():
    parser = argparse.ArgumentParser(description="Seed Razorpay Test Mode with SaaS orders.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing seed_output.json if it exists",
    )
    args = parser.parse_args()

    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        print("[ERROR] RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in backend/.env")
        sys.exit(1)

    if not RAZORPAY_KEY_ID.startswith("rzp_test_"):
        print(f"[SECURITY ALERT] Key '{RAZORPAY_KEY_ID}' is NOT a test key (must start with rzp_test_). Aborting.")
        sys.exit(1)

    if OUTPUT_FILE.exists() and not args.force:
        print(f"[INFO] Seed output already exists at {OUTPUT_FILE}.")
        print("Use --force to re-seed or inspect the existing file.")
        sys.exit(0)

    auth = (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    print("=" * 72)
    print("ReconPilot -- Live Razorpay Sandbox Seeder")
    print(f"Key ID: {RAZORPAY_KEY_ID}")
    print(f"Target Archetype: SaaS & Cloud (5 Subscription Orders)")
    print("=" * 72)

    seeded_records: List[Dict[str, Any]] = []

    with httpx.Client() as client:
        for idx, tier in enumerate(SAAS_TIERS, start=1):
            print(f"\n[{idx}/5] Creating order: {tier['product']} (Rs. {tier['amount_inr']})...")
            try:
                record = create_order_and_link(client, auth, tier)
                seeded_records.append(record)
                print(f"    [OK] Order ID:        {record['order_id']}")
                print(f"    [OK] Payment Link ID: {record['payment_link_id']}")
                print(f"    [OK] Checkout URL:    {record['payment_link_url']}")
            except Exception as exc:
                print(f"    [FAIL] Failed: {exc}")
                sys.exit(1)

    manifest = {
        "seeded_at": datetime.now(timezone.utc).isoformat(),
        "key_id": RAZORPAY_KEY_ID,
        "archetype": "saas_and_cloud",
        "orders_count": len(seeded_records),
        "orders": seeded_records,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 72)
    print("SEEDING COMPLETE -- Output written to backend/scripts/seed_output.json")
    print("=" * 72)
    print("\nNext Steps (Manual Payment Completion):")
    print("Open each checkout URL in your browser and pay with Razorpay's test card:")
    print("  Card Number: 4111 1111 1111 1111")
    print("  Expiry:      12/28 (any future date)")
    print("  CVV:         123 (any 3 digits)")
    print("  OTP:         Any 4-6 digit number (e.g. 1234)\n")
    for r in seeded_records:
        print(f"  * Rs. {r['amount_inr']:>9} ({r['product']}): {r['payment_link_url']}")
    print("\nAfter completing payments, run:")
    print("  python backend/scripts/pull_live_demo.py")
    print("=" * 72)


if __name__ == "__main__":
    main()
