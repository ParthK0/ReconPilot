"""
tests/test_auth_tenant.py
=========================
Tests for JWT Token Authentication and Multi-Tenant Scoping:
- HMAC-SHA256 Token Generation & Decoding
- Tampered token rejection
- Expired token handling
- Tenant resolution via header and Bearer token
"""

import pytest
from datetime import timedelta
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from backend.api.auth import (
    create_access_token,
    decode_access_token,
    get_current_tenant,
)


def test_jwt_token_lifecycle():
    payload = {"org_id": "tenant_saas_01", "sub": "admin_user", "role": "finance_lead"}
    token = create_access_token(payload=payload)
    assert token is not None
    assert token.count(".") == 2

    decoded = decode_access_token(token)
    assert decoded["org_id"] == "tenant_saas_01"
    assert decoded["sub"] == "admin_user"
    assert "exp" in decoded


def test_jwt_tampered_token():
    payload = {"org_id": "tenant_saas_01"}
    token = create_access_token(payload=payload)
    tampered = token[:-4] + "xxxx"
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(tampered)
    assert exc_info.value.status_code == 401


def test_jwt_expired_token():
    payload = {"org_id": "tenant_saas_01"}
    token = create_access_token(payload=payload, expires_delta=timedelta(seconds=-10))
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401
    assert "expired" in str(exc_info.value.detail).lower()


def test_tenant_scoping_resolution():
    # 1. Header Resolution
    tenant_hdr = get_current_tenant(header_tenant="org_enterprise_99", bearer_creds=None)
    assert tenant_hdr == "org_enterprise_99"

    # 2. Bearer Token Resolution
    token = create_access_token({"org_id": "org_jwt_bearer_42"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    tenant_bearer = get_current_tenant(header_tenant=None, bearer_creds=creds)
    assert tenant_bearer == "org_jwt_bearer_42"

    # 3. Default Fallback
    tenant_default = get_current_tenant(header_tenant=None, bearer_creds=None)
    assert tenant_default == "org_default"
