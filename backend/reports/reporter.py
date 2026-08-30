"""
backend/reports/reporter.py
===========================
Generates reconciliation exports and 1-Click ERP Journal Entries:
- Standard Reconciliation CSV (FR-13 / FR-15)
- Tally Prime Journal XML (<ENVELOPE> formatted voucher import)
- Zoho Books Manual Journal CSV
- NetSuite SuiteTalk JSON Journal Schema
"""

import io
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional
import pandas as pd


def generate_reconciliation_csv(records_data: List[Dict[str, Any]]) -> str:
    """
    FR-13 / FR-15: Generates final reconciliation export CSV.
    Fields: record_id, order_id, source_type, amount, status, match_method, confidence, evidence, reviewer_action
    """
    df = pd.DataFrame(records_data)
    if df.empty:
        df = pd.DataFrame(
            columns=[
                "record_id",
                "order_id",
                "source_type",
                "amount",
                "status",
                "match_method",
                "confidence",
                "evidence",
                "reviewer_action",
            ]
        )
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue()


def generate_tally_xml(
    batch_id: str,
    matches_data: List[Dict[str, Any]],
    adjustments_data: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Generates Tally Prime compatible XML Envelope for Journal Vouchers.
    Maps Razorpay Gross, MDR Fees, GST on Fees, TDS deductions, and Bank Payouts to Tally Ledgers.
    """
    envelope = ET.Element("ENVELOPE")
    header = ET.SubElement(envelope, "HEADER")
    tally_req = ET.SubElement(header, "TALLYREQUEST")
    tally_req.text = "Import Data"

    body = ET.SubElement(envelope, "BODY")
    import_data = ET.SubElement(body, "IMPORTDATA")
    req_data = ET.SubElement(import_data, "REQUESTDATA")

    total_gross = Decimal("0.00")
    total_fee = Decimal("0.00")
    total_gst = Decimal("0.00")
    total_bank = Decimal("0.00")
    total_suspense = Decimal("0.00")

    for item in matches_data:
        gross = Decimal(str(item.get("invoice_amount") or item.get("amount") or "0.00"))
        fee = Decimal(str(item.get("fees") or "0.00"))
        gst = Decimal(str(item.get("gst") or "0.00"))
        bank = Decimal(str(item.get("bank_amount") or (gross - fee - gst)))

        total_gross += gross
        total_fee += fee
        total_gst += gst
        total_bank += bank

    if adjustments_data:
        for adj in adjustments_data:
            total_suspense += Decimal(str(adj.get("difference_amount") or "0.00"))

    tally_msg = ET.SubElement(req_data, "TALLYMESSAGE")
    voucher = ET.SubElement(tally_msg, "VOUCHER", VCHTYPE="Journal", ACTION="Create")
    
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    ET.SubElement(voucher, "DATE").text = date_str
    ET.SubElement(voucher, "VOUCHERTYPENAME").text = "Journal"
    ET.SubElement(voucher, "VOUCHERNUMBER").text = f"RP-REC-{batch_id[:8]}"
    ET.SubElement(voucher, "NARRATION").text = (
        f"ReconPilot 1-Click Settlement Reconciled Journal for Batch {batch_id}. "
        f"Reconciled {len(matches_data)} orders."
    )

    # 1. Bank Account (Debit Payout)
    bank_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
    ET.SubElement(bank_entry, "LEDGERNAME").text = "HDFC Bank Account"
    ET.SubElement(bank_entry, "ISDEEMEDPOSITIVE").text = "Yes"
    ET.SubElement(bank_entry, "AMOUNT").text = f"-{total_bank:.2f}"

    # 2. Payment Gateway MDR Charges (Debit Expense)
    if total_fee > Decimal("0.00"):
        fee_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(fee_entry, "LEDGERNAME").text = "Payment Gateway Charges (MDR)"
        ET.SubElement(fee_entry, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(fee_entry, "AMOUNT").text = f"-{total_fee:.2f}"

    # 3. GST on Gateway Charges (Debit Input Credit)
    if total_gst > Decimal("0.00"):
        gst_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(gst_entry, "LEDGERNAME").text = "Input CGST/SGST/IGST on Services"
        ET.SubElement(gst_entry, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(gst_entry, "AMOUNT").text = f"-{total_gst:.2f}"

    # 4. Discrepancy Suspense (Debit or Credit if exists)
    if total_suspense != Decimal("0.00"):
        susp_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(susp_entry, "LEDGERNAME").text = "Gateway Reconciliation Suspense Account"
        is_positive = "Yes" if total_suspense > Decimal("0.00") else "No"
        ET.SubElement(susp_entry, "ISDEEMEDPOSITIVE").text = is_positive
        ET.SubElement(susp_entry, "AMOUNT").text = f"-{abs(total_suspense):.2f}" if total_suspense > 0 else f"{abs(total_suspense):.2f}"

    # 5. Accounts Receivable / Customer Clearing (Credit)
    rev_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
    ET.SubElement(rev_entry, "LEDGERNAME").text = "Razorpay Clearing Account"
    ET.SubElement(rev_entry, "ISDEEMEDPOSITIVE").text = "No"
    ET.SubElement(rev_entry, "AMOUNT").text = f"{total_gross:.2f}"

    return ET.tostring(envelope, encoding="utf-8", xml_declaration=True).decode("utf-8")


def generate_zoho_books_csv(
    batch_id: str,
    matches_data: List[Dict[str, Any]],
    adjustments_data: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Generates Zoho Books Manual Journal CSV Import schema.
    Columns: Journal Date, Journal Number, Reference Number, Notes, Account Name, Description, Debit, Credit
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    journal_no = f"JN-RP-{batch_id[:8]}"
    ref_no = f"BATCH-{batch_id[:8]}"
    notes = f"ReconPilot Reconciled Batch {batch_id}"

    total_gross = Decimal("0.00")
    total_fee = Decimal("0.00")
    total_gst = Decimal("0.00")
    total_bank = Decimal("0.00")
    total_suspense = Decimal("0.00")

    for item in matches_data:
        gross = Decimal(str(item.get("invoice_amount") or item.get("amount") or "0.00"))
        fee = Decimal(str(item.get("fees") or "0.00"))
        gst = Decimal(str(item.get("gst") or "0.00"))
        bank = Decimal(str(item.get("bank_amount") or (gross - fee - gst)))

        total_gross += gross
        total_fee += fee
        total_gst += gst
        total_bank += bank

    if adjustments_data:
        for adj in adjustments_data:
            total_suspense += Decimal(str(adj.get("difference_amount") or "0.00"))

    rows = [
        {
            "Journal Date": today,
            "Journal Number": journal_no,
            "Reference Number": ref_no,
            "Notes": notes,
            "Account Name": "HDFC Bank Clearing",
            "Description": "Razorpay Net Payout Received",
            "Debit": f"{total_bank:.2f}",
            "Credit": "0.00",
        },
        {
            "Journal Date": today,
            "Journal Number": journal_no,
            "Reference Number": ref_no,
            "Notes": notes,
            "Account Name": "Payment Gateway Fee Expense",
            "Description": "Razorpay MDR Commission",
            "Debit": f"{total_fee:.2f}",
            "Credit": "0.00",
        },
        {
            "Journal Date": today,
            "Journal Number": journal_no,
            "Reference Number": ref_no,
            "Notes": notes,
            "Account Name": "Input Tax Credit - GST (18%)",
            "Description": "GST on Gateway Commission",
            "Debit": f"{total_gst:.2f}",
            "Credit": "0.00",
        },
    ]

    if total_suspense > Decimal("0.00"):
        rows.append({
            "Journal Date": today,
            "Journal Number": journal_no,
            "Reference Number": ref_no,
            "Notes": notes,
            "Account Name": "Reconciliation Variance Suspense",
            "Description": "Unresolved Settlement Discrepancy",
            "Debit": f"{total_suspense:.2f}",
            "Credit": "0.00",
        })

    rows.append({
        "Journal Date": today,
        "Journal Number": journal_no,
        "Reference Number": ref_no,
        "Notes": notes,
        "Account Name": "Razorpay Settlement Nodal Account",
        "Description": f"Gross Cleared Transactions ({len(matches_data)} orders)",
        "Debit": "0.00",
        "Credit": f"{total_gross:.2f}",
    })

    df = pd.DataFrame(rows)
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue()


def generate_netsuite_journal_json(
    batch_id: str,
    matches_data: List[Dict[str, Any]],
    adjustments_data: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Generates NetSuite SuiteTalk REST API compatible JSON Journal Entry payload.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_gross = Decimal("0.00")
    total_fee = Decimal("0.00")
    total_gst = Decimal("0.00")
    total_bank = Decimal("0.00")
    total_suspense = Decimal("0.00")

    for item in matches_data:
        gross = Decimal(str(item.get("invoice_amount") or item.get("amount") or "0.00"))
        fee = Decimal(str(item.get("fees") or "0.00"))
        gst = Decimal(str(item.get("gst") or "0.00"))
        bank = Decimal(str(item.get("bank_amount") or (gross - fee - gst)))

        total_gross += gross
        total_fee += fee
        total_gst += gst
        total_bank += bank

    if adjustments_data:
        for adj in adjustments_data:
            total_suspense += Decimal(str(adj.get("difference_amount") or "0.00"))

    lines = [
        {
            "account": {"refName": "10010 HDFC Operating Account"},
            "debit": float(total_bank),
            "credit": 0.0,
            "memo": "Net Gateway Settlement Received",
        },
        {
            "account": {"refName": "60150 Payment Gateway Fees"},
            "debit": float(total_fee),
            "credit": 0.0,
            "memo": "Razorpay MDR Charges",
        },
        {
            "account": {"refName": "14050 GST Input Credit Asset"},
            "debit": float(total_gst),
            "credit": 0.0,
            "memo": "GST 18% on Processing Charges",
        },
    ]

    if total_suspense > Decimal("0.00"):
        lines.append({
            "account": {"refName": "21090 Gateway Reconciliation Suspense"},
            "debit": float(total_suspense),
            "credit": 0.0,
            "memo": "AI Detected Discrepancy Variance",
        })

    lines.append({
        "account": {"refName": "12000 Accounts Receivable / Gateway Float"},
        "debit": 0.0,
        "credit": float(total_gross),
        "memo": f"Gross Reconciliation Offsetting for {len(matches_data)} orders",
    })

    payload = {
        "tranDate": today,
        "externalId": f"RECONPILOT-BATCH-{batch_id}",
        "memo": f"Automated 1-Click ERP Journal Entry from ReconPilot Batch {batch_id}",
        "subsidiary": {"id": "1"},
        "line": lines,
    }

    return json.dumps(payload, indent=2)

