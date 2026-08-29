"""
backend/api/auth.py
===================
API Key and Bearer Token authentication dependencies for protected mutations.
"""

import os
from typing import Optional
from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


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

    # If no key is set in environment or explicitly dev-mode, permit development bypass
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
