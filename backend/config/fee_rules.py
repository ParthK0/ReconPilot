import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class FeeConfig(BaseModel):
    """
    Configurable fee, tax, and settlement schedule for a specific merchant profile.
    Allows business logic without code changes.
    """
    merchant_type: str = "retail"
    mdr: Decimal = Field(default=Decimal("2.0"), description="MDR fee percentage, e.g. 2.0 for 2%")
    gst: Decimal = Field(default=Decimal("18.0"), description="GST percentage on MDR fees, e.g. 18.0 for 18%")
    tds: Decimal = Field(default=Decimal("1.0"), description="TDS percentage on invoice amount, e.g. 1.0 for 1%")
    platform_fee: Decimal = Field(default=Decimal("0.0"), description="Platform fee percentage on invoice, e.g. 0.5")
    convenience_fee: Decimal = Field(default=Decimal("0.0"), description="Convenience fee percentage on invoice, e.g. 0.3")
    settlement_delay_days: int = Field(default=2, description="Expected settlement window in days")

    @property
    def mdr_rate(self) -> Decimal:
        """Returns MDR as a multiplier (e.g. 0.02 for 2%)."""
        return self.mdr / Decimal("100")

    @property
    def gst_rate(self) -> Decimal:
        """Returns GST as a multiplier on MDR fee (e.g. 0.18 for 18%)."""
        return self.gst / Decimal("100")

    @property
    def tds_rate(self) -> Decimal:
        """Returns TDS as a multiplier on invoice (e.g. 0.01 for 1%)."""
        return self.tds / Decimal("100")

    @property
    def platform_fee_rate(self) -> Decimal:
        """Returns platform fee as a multiplier on invoice."""
        return self.platform_fee / Decimal("100")

    @property
    def convenience_fee_rate(self) -> Decimal:
        """Returns convenience fee as a multiplier on invoice."""
        return self.convenience_fee / Decimal("100")


DEFAULT_FEE_CONFIG = FeeConfig(
    merchant_type="retail",
    mdr=Decimal("2.0"),
    gst=Decimal("18.0"),
    tds=Decimal("1.0"),
    platform_fee=Decimal("0.0"),
    convenience_fee=Decimal("0.0"),
    settlement_delay_days=2,
)

STANDARD_FEE_RATE: Decimal = DEFAULT_FEE_CONFIG.mdr_rate  # 2.0% standard Razorpay MDR
STANDARD_GST_RATE: Decimal = DEFAULT_FEE_CONFIG.gst_rate  # 18.0% GST on MDR fees
STANDARD_TDS_RATE: Decimal = DEFAULT_FEE_CONFIG.tds_rate  # 1.0% TDS under Section 194O


def load_fee_config(config_source: Union[str, Path, Dict[str, Any], FeeConfig, None] = None) -> FeeConfig:
    """
    Loads FeeConfig from:
      1. FeeConfig instance (passed through)
      2. Dictionary
      3. JSON file path
      4. Merchant profile name (e.g. 'retail', 'marketplace', 'subscription', 'restaurant', 'enterprise')
      5. Defaults to DEFAULT_FEE_CONFIG
    """
    if config_source is None:
        return DEFAULT_FEE_CONFIG

    if isinstance(config_source, FeeConfig):
        return config_source

    if isinstance(config_source, dict):
        return FeeConfig.model_validate(config_source)

    if isinstance(config_source, (str, Path)):
        source_str = str(config_source).strip()
        # Check if it is a path to an existing JSON file
        if os.path.isfile(source_str):
            with open(source_str, "r", encoding="utf-8") as f:
                data = json.load(f)
            return FeeConfig.model_validate(data)

        # Check if it matches a profile name in merchant_profiles directory
        base_dir = Path(__file__).parent / "merchant_profiles"
        named_profile_path = base_dir / f"{source_str.lower()}.json"
        if named_profile_path.is_file():
            with open(named_profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return FeeConfig.model_validate(data)

        # Check if raw JSON string
        if source_str.startswith("{"):
            try:
                data = json.loads(source_str)
                return FeeConfig.model_validate(data)
            except Exception:
                pass

    return DEFAULT_FEE_CONFIG
