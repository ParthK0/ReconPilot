"""
backend/api/auth.py
===================
API Key, JWT Authentication, and Tenant Scoping dependencies.
Supports HMAC-SHA256 signed JWT tokens, X-Tenant-ID headers, and scoped tenant isolation.
"""

import os
import hmac
import hashlib
import base64
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

API_KEY_NAME = "X-API-Key"
TENANT_HEADER_NAME = "X-Tenant-ID"
JWT_SECRET = os.getenv("JWT_SECRET", "reconpilot-secret-token-key-change-in-production")
JWT_ALGORITHM = "HS256"
DEFAULT_EXPIRY_MINUTES = 60 * 24  # 24 hours

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
tenant_header = APIKeyHeader(name=TENANT_HEADER_NAME, auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ""
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def create_access_token(
    payload: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    secret_key: str = JWT_SECRET,
) -> str:
    """
    Creates a cryptographically signed HMAC-SHA256 JWT access token.
    Payload typically contains {"org_id": "...", "sub": "...", "role": "..."}.
    """
    to_encode = payload.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=DEFAULT_EXPIRY_MINUTES))
    to_encode.update({"exp": int(expire.timestamp()), "iat": int(datetime.now(timezone.utc).timestamp())})

    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(to_encode, separators=(",", ":")).encode("utf-8")

    encoded_header = _b64_encode(header_bytes)
    encoded_payload = _b64_encode(payload_bytes)

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_sig = _b64_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_sig}"


def decode_access_token(token: str, secret_key: str = JWT_SECRET) -> Dict[str, Any]:
    """
    Validates and decodes a signed HMAC-SHA256 JWT access token.
    Raises HTTPException(401) on expired or tampered tokens.
    """
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid JWT token format.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    encoded_header, encoded_payload, encoded_sig = parts
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    expected_sig = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()

    try:
        actual_sig = _b64_decode(encoded_sig)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload_data = json.loads(_b64_decode(encoded_payload).decode("utf-8"))
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Malformed token payload: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check expiration
    if "exp" in payload_data and int(payload_data["exp"]) < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload_data


def get_configured_api_key() -> Optional[str]:
    """Retrieves the expected API key from environment."""
    return os.getenv("RECONPILOT_API_KEY") or os.getenv("DEMO_API_KEY")


def verify_api_key(
    header_key: Optional[str] = Security(api_key_header),
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
) -> bool:
    """
    Validates API key from either 'X-API-Key' header or 'Authorization: Bearer <key>'.
    If RECONPILOT_API_KEY / DEMO_API_KEY is not configured or set to 'dev-mode', allows access.
    """
    expected_key = get_configured_api_key()

    if not expected_key or expected_key in ("dev-mode", "test-mode", ""):
        return True

    provided_key = header_key or (bearer_creds.credentials if bearer_creds else None)

    if not provided_key or provided_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key. Provide 'X-API-Key' header or 'Authorization: Bearer <key>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


def get_current_tenant(
    header_tenant: Optional[str] = Security(tenant_header),
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
) -> str:
    """
    Resolves the tenant/organization identifier from JWT Bearer token or 'X-Tenant-ID' header.
    Defaults to 'org_default' for backwards compatibility and local testing.
    """
    # 1. Check Bearer Token
    if bearer_creds and bearer_creds.credentials:
        raw_token = bearer_creds.credentials
        # If token starts with standard JWT 3-part layout
        if raw_token.count(".") == 2:
            try:
                payload = decode_access_token(raw_token)
                tenant_id = payload.get("org_id") or payload.get("tenant_id") or payload.get("sub")
                if tenant_id:
                    return str(tenant_id)
            except HTTPException:
                pass  # Fallback to header or default if configured

    # 2. Check X-Tenant-ID header
    if header_tenant and header_tenant.strip():
        return header_tenant.strip()

    # 3. Default fallback
    return "org_default"

