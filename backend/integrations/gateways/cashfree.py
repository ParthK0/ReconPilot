"""
backend/integrations/gateways/cashfree.py
=========================================
Cashfree Gateway Adapter for ReconPilot.
Extensibility for Indian high-volume UPI and AutoCollect nodal settlements.
"""

from typing import Any, Dict, List, Optional
from backend.integrations.base import BaseGatewayAdapter, IntegrationMode


class CashfreeAdapter(BaseGatewayAdapter):
    """Adapter for syncing Cashfree AutoCollect Settlements."""

    def __init__(self, app_id: Optional[str] = None, secret_key: Optional[str] = None, mode: IntegrationMode = IntegrationMode.PRODUCTION):
        self.app_id = app_id or ""
        self.secret_key = secret_key or ""
        self.mode = mode

    @property
    def provider_name(self) -> str:
        return "cashfree"

    def health_check(self) -> bool:
        return bool(self.app_id and self.secret_key)

    def sync_settlements(self, limit: int = 100) -> List[Dict[str, Any]]:
        return []

    def sync_payments(self, limit: int = 100) -> List[Dict[str, Any]]:
        return []
