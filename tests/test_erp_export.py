"""
tests/test_erp_export.py
========================
Tests for 1-Click ERP Journal Exports:
- Tally Prime XML envelope generation
- Zoho Books Manual Journal CSV generation
- NetSuite SuiteTalk JSON schema generation
"""

import json
import xml.etree.ElementTree as ET
from decimal import Decimal
from backend.reports.reporter import (
    generate_tally_xml,
    generate_zoho_books_csv,
    generate_netsuite_journal_json,
)


def test_tally_xml_export():
    batch_id = "test-batch-uuid-12345"
    matches_data = [
        {
            "invoice_amount": 10000.00,
            "fees": 200.00,
            "gst": 36.00,
            "bank_amount": 9764.00,
            "status": "matched",
        }
    ]
    adjustments_data = [
        {
            "difference_amount": 50.00,
            "reason": "manual_fee_adjustment",
        }
    ]

    xml_str = generate_tally_xml(batch_id, matches_data, adjustments_data)
    assert "<ENVELOPE>" in xml_str
    assert "Import Data" in xml_str
    assert "HDFC Bank Account" in xml_str
    assert "Payment Gateway Charges (MDR)" in xml_str
    assert "Input CGST/SGST/IGST on Services" in xml_str
    assert "Gateway Reconciliation Suspense Account" in xml_str

    root = ET.fromstring(xml_str)
    assert root.tag == "ENVELOPE"


def test_zoho_books_csv_export():
    batch_id = "test-batch-uuid-67890"
    matches_data = [
        {
            "invoice_amount": 5000.00,
            "fees": 100.00,
            "gst": 18.00,
            "bank_amount": 4882.00,
            "status": "matched",
        }
    ]

    csv_str = generate_zoho_books_csv(batch_id, matches_data)
    assert "Journal Date,Journal Number,Reference Number,Notes,Account Name,Description,Debit,Credit" in csv_str
    assert "HDFC Bank Clearing" in csv_str
    assert "Payment Gateway Fee Expense" in csv_str
    assert "Razorpay Settlement Nodal Account" in csv_str
    assert "4882.00" in csv_str


def test_netsuite_journal_json_export():
    batch_id = "test-batch-uuid-netsuite"
    matches_data = [
        {
            "invoice_amount": 25000.00,
            "fees": 500.00,
            "gst": 90.00,
            "bank_amount": 24410.00,
            "status": "matched",
        }
    ]

    json_str = generate_netsuite_journal_json(batch_id, matches_data)
    payload = json.loads(json_str)
    assert payload["externalId"] == f"RECONPILOT-BATCH-{batch_id}"
    assert len(payload["line"]) >= 3
    assert payload["line"][0]["debit"] == 24410.00
    assert payload["line"][1]["debit"] == 500.00
    assert payload["line"][2]["debit"] == 90.00
