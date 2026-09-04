"""
backend/integrations/base.py
============================
ReconPilot Provider-Agnostic Adapter Architecture.

Defines the contract interfaces for:
1. BaseGatewayAdapter: Payment Gateways (Razorpay, Stripe, Cashfree)
2. BaseBankAdapter: Core Banking Feeds (HDFC, ICICI, Axis Bank)
3. BaseERPAdapter: Invoicing Systems (Tally, Zoho, SAP)

Every adapter converts provider-specific APIs and exports into ReconPilot's
canonical internal representation before passing to the Normalizer and Rule Engine.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class IntegrationMode(str, Enum):
    DEMO = "demo"          # Test sandbox with simulated bank ledger
    PRODUCTION = "production"  # Live API credentials with actual bank statement imports


class SyncResult(BaseModel):
    provider: str
    mode: IntegrationMode
    status: str
    invoices_synced: int = 0
    settlements_synced: int = 0
    bank_txns_synced: int = 0
    records: Dict[str, List[Dict[str, Any]]] = {}
    notes: Optional[str] = None


class BaseGatewayAdapter(ABC):
    """Abstract contract for payment gateway integrations."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of payment gateway (e.g., 'razorpay', 'stripe', 'cashfree')."""
        pass

    @abstractmethod
    def sync_settlements(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Syncs payout/settlement records from the gateway."""
        pass

    @abstractmethod
    def sync_payments(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Syncs individual captured transaction records from the gateway."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Verifies API credentials and gateway connectivity."""
        pass


class BaseBankAdapter(ABC):
    """Abstract contract for commercial bank statement ingestion."""

    @property
    @abstractmethod
    def bank_code(self) -> str:
        """IFSC / Bank identifier (e.g., 'HDFC', 'ICIC', 'UTIB')."""
        pass

    @abstractmethod
    def import_statements(self, raw_content: Any) -> List[Dict[str, Any]]:
        """Parses bank statement feed into canonical bank transaction records."""
        pass


class BaseERPAdapter(ABC):
    """Abstract contract for enterprise invoicing and accounting software."""

    @property
    @abstractmethod
    def erp_name(self) -> str:
        """ERP platform identifier (e.g., 'tally', 'zoho', 'sap')."""
        pass

    @abstractmethod
    def import_invoices(self, raw_content: Any) -> List[Dict[str, Any]]:
        """Extracts billed sales invoices into canonical invoice records."""
        pass
