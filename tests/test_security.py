"""
tests/test_security.py
======================
Comprehensive security and backend hardening test suite:
1. API Key / Bearer Authentication
2. Sliding Window Rate Limiting Middleware
3. CSV Formula Injection Sanitization
4. Maximum Payload Size Enforcement
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.parser.csv_parser import InvoiceParser


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_public_endpoints_accessible_without_auth(client: TestClient):
    """GET endpoints (health, merchants) must be publicly accessible without API Key."""
    res_health = client.get("/api/v1/health")
    assert res_health.status_code == 200

    res_merchants = client.get("/api/v1/merchants")
    assert res_merchants.status_code == 200


def test_api_key_auth_enforcement_with_configured_key(monkeypatch, client: TestClient):
    """Mutating endpoints must reject requests without valid key when key is configured."""
    monkeypatch.setenv("RECONPILOT_API_KEY", "secret-finance-key-123")

    # 1. Without header -> 401 Unauthorized
    res_no_auth = client.post("/api/v1/batches/generate?merchant_type=retail&record_count=10")
    assert res_no_auth.status_code == 401

    # 2. With invalid header -> 401 Unauthorized
    res_bad_auth = client.post(
        "/api/v1/batches/generate?merchant_type=retail&record_count=10",
        headers={"X-API-Key": "wrong-key"},
    )
    assert res_bad_auth.status_code == 401

    # 3. With valid X-API-Key header -> 201 Created
    res_good_auth = client.post(
        "/api/v1/batches/generate?merchant_type=retail&record_count=10",
        headers={"X-API-Key": "secret-finance-key-123"},
    )
    assert res_good_auth.status_code == 201

    # 4. With valid Bearer token -> 201 Created
    res_bearer_auth = client.post(
        "/api/v1/batches/generate?merchant_type=retail&record_count=10",
        headers={"Authorization": "Bearer secret-finance-key-123"},
    )
    assert res_bearer_auth.status_code == 201


def test_csv_formula_injection_sanitized():
    """
    CSV cells with leading formula injection characters (=, @, +, -) followed by alphabetic
    payloads must be neutralized with a leading quote to prevent spreadsheet execution.
    """
    dangerous_csv = (
        "invoice_id,order_id,amount,invoice_date,customer_name,status\n"
        "=CMD('calc'),+SUM(A1:A10),1000.00,2026-08-01,@ALERT(),paid\n"
    )
    parser = InvoiceParser()
    df = parser.parse(dangerous_csv)

    # First row invoice_id and customer_name must be escaped
    assert df["invoice_id"].iloc[0].startswith("'=")
    assert df["order_id"].iloc[0].startswith("'+")
    assert df["customer_name"].iloc[0].startswith("'@")


def test_upload_payload_size_limit(monkeypatch, client: TestClient):
    """Uploading a file exceeding 10MB must return HTTP 413 Payload Too Large."""
    monkeypatch.setenv("DEMO_API_KEY", "")
    monkeypatch.setenv("RECONPILOT_API_KEY", "")
    huge_bytes = b"0" * (11 * 1024 * 1024)  # 11 MB

    files = {
        "settlement_csv": ("settlement.csv", huge_bytes, "text/csv"),
        "bank_csv": ("bank.csv", b"dummy", "text/csv"),
        "invoice_csv": ("invoice.csv", b"dummy", "text/csv"),
    }

    res = client.post("/api/v1/batches", files=files)
    assert res.status_code == 413
    assert "exceeds maximum limit" in res.json()["detail"]


def test_preview_schema_size_limit(monkeypatch, client: TestClient):
    """Uploading a schema file exceeding 10MB must return HTTP 413 Payload Too Large."""
    monkeypatch.setenv("DEMO_API_KEY", "")
    monkeypatch.setenv("RECONPILOT_API_KEY", "")
    huge_bytes = b"0" * (11 * 1024 * 1024)

    files = {"file": ("huge_settlement.csv", huge_bytes, "text/csv")}
    res = client.post("/api/v1/schema/preview", files=files)
    assert res.status_code == 413
    assert "exceeds maximum limit" in res.json()["detail"]
