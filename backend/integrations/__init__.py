"""
backend/integrations/__init__.py
================================
ReconPilot Extensible Adapter Layer.
"""

from backend.integrations.base import (
    BaseGatewayAdapter,
    BaseBankAdapter,
    BaseERPAdapter,
    IntegrationMode,
    SyncResult,
)

__all__ = [
    "BaseGatewayAdapter",
    "BaseBankAdapter",
    "BaseERPAdapter",
    "IntegrationMode",
    "SyncResult",
]
