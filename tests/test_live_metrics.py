import io
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.db.session import init_db


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_live_metrics_endpoint_without_ground_truth_returns_null_precision(client):
    """
    Verifies that when an arbitrary batch is uploaded without ground truth,
    the live GET /batches/{batch_id}/metrics endpoint returns null/None for
    precision, recall, false_positives, false_negatives, rather than hardcoded 0.
    """
    inv_csv = "invoice_id,order_id,amount,invoice_date,customer_name,status\nINV-01,ORD-LIVE-01,1000.00,2026-08-01,Alice,paid\n"
    set_csv = "settlement_id,order_id,amount,settlement_date,reference_number,status,fees,gst,tds\nSET-01,ORD-LIVE-01,1000.00,2026-08-02,UTR-LIVE-01,settled,0.00,0.00,0.00\n"
    bnk_csv = "bank_txn_id,txn_date,description,reference_number,amount,balance,status\nBNK-01,2026-08-02,ACH CR RAZORPAY UTR-LIVE-01,UTR-LIVE-01,1000.00,500000.00,credited\n"

    files = {
        "settlement_csv": ("settlements.csv", io.BytesIO(set_csv.encode("utf-8")), "text/csv"),
        "bank_csv": ("bank_statements.csv", io.BytesIO(bnk_csv.encode("utf-8")), "text/csv"),
        "invoice_csv": ("invoices.csv", io.BytesIO(inv_csv.encode("utf-8")), "text/csv"),
    }

    res = client.post("/api/v1/batches", files=files)
    assert res.status_code == 201
    batch_id = res.json()["batch_id"]

    metrics_res = client.get(f"/api/v1/batches/{batch_id}/metrics")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()

    assert metrics["records_processed"] == 1
    assert metrics["rule_matches"] == 1
    assert metrics["match_rate"] == 100.0
    # Ground truth was not provided -> these MUST be null/None, never hardcoded 0
    assert metrics["precision"] is None
    assert metrics["recall"] is None
    assert metrics["false_positives"] is None
    assert metrics["false_negatives"] is None
    assert metrics["true_positives"] is None


def test_live_metrics_endpoint_with_known_false_positive_reflects_in_api(client):
    """
    Feeds a batch with 2 records where:
    - Record 1: Exact match, GT expected_resolution = 'rule' (True Positive)
    - Record 2: Exact match in rule engine, BUT GT expected_resolution = 'exception' (Known False Positive)
    Asserts that the LIVE GET /batches/{batch_id}/metrics endpoint correctly reflects
    false_positives=1, true_positives=1, precision=50.0% from real ground-truth comparison.
    """
    inv_csv = (
        "invoice_id,order_id,amount,invoice_date,customer_name,status\n"
        "INV-01,ORD-TP-01,1000.00,2026-08-01,Alice,paid\n"
        "INV-02,ORD-FP-02,2000.00,2026-08-01,Bob,paid\n"
    )
    set_csv = (
        "settlement_id,order_id,amount,settlement_date,reference_number,status,fees,gst,tds\n"
        "SET-01,ORD-TP-01,1000.00,2026-08-02,UTR-TP-01,settled,0.00,0.00,0.00\n"
        "SET-02,ORD-FP-02,2000.00,2026-08-02,UTR-FP-02,settled,0.00,0.00,0.00\n"
    )
    bnk_csv = (
        "bank_txn_id,txn_date,description,reference_number,amount,balance,status\n"
        "BNK-01,2026-08-02,ACH CR RAZORPAY UTR-TP-01,UTR-TP-01,1000.00,500000.00,credited\n"
        "BNK-02,2026-08-02,ACH CR RAZORPAY UTR-FP-02,UTR-FP-02,2000.00,502000.00,credited\n"
    )
    gt_data = [
        {"order_id": "ORD-TP-01", "expected_resolution": "rule"},
        {"order_id": "ORD-FP-02", "expected_resolution": "exception"},  # Known False Positive
    ]

    files = {
        "settlement_csv": ("settlements.csv", io.BytesIO(set_csv.encode("utf-8")), "text/csv"),
        "bank_csv": ("bank_statements.csv", io.BytesIO(bnk_csv.encode("utf-8")), "text/csv"),
        "invoice_csv": ("invoices.csv", io.BytesIO(inv_csv.encode("utf-8")), "text/csv"),
        "ground_truth_json": ("ground_truth.json", io.BytesIO(json.dumps(gt_data).encode("utf-8")), "application/json"),
    }

    res = client.post("/api/v1/batches", files=files)
    assert res.status_code == 201
    batch_id = res.json()["batch_id"]

    metrics_res = client.get(f"/api/v1/batches/{batch_id}/metrics")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()

    assert metrics["records_processed"] == 2
    assert metrics["rule_matches"] == 2
    assert metrics["true_positives"] == 1
    assert metrics["false_positives"] == 1
    assert metrics["precision"] == 50.0  # (1 TP / 2 Matched) * 100
    assert metrics["recall"] == 100.0
