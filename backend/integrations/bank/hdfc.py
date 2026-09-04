"""
backend/integrations/bank/hdfc.py
=================================
HDFC Bank Statement Adapter for ReconPilot.
Parses corporate HDFC Bank net banking CSV and ASCII statement feeds into canonical records.
"""

from typing import Any, Dict, List
import pandas as pd
from backend.integrations.base import BaseBankAdapter
from backend.normalizer.data_cleaners import clean_currency, clean_date, clean_reference


class HDFCBankAdapter(BaseBankAdapter):
    """Parses commercial HDFC Bank corporate statement feeds."""

    @property
    def bank_code(self) -> str:
        return "HDFC"

    def import_statements(self, raw_content: Any) -> List[Dict[str, Any]]:
        """Parses HDFC statement DataFrame or raw CSV lines."""
        if isinstance(raw_content, pd.DataFrame):
            df = raw_content
        else:
            df = pd.read_csv(raw_content)

        records = []
        for _, row in df.iterrows():
            amt = clean_currency(row.get("amount") or row.get("txn_amount") or row.get("Credit"))
            records.append({
                "bank_txn_id": str(row.get("bank_txn_id") or row.get("Chq./Ref.No.") or f"TXN-HDFC-{len(records)+1:06d}"),
                "txn_date": clean_date(row.get("txn_date") or row.get("Date") or row.get("Value Date")).isoformat(),
                "description": str(row.get("description") or row.get("Narration") or ""),
                "reference_number": clean_reference(row.get("reference_number") or row.get("Chq./Ref.No.")),
                "amount": f"{amt:.2f}",
                "balance": f"{clean_currency(row.get('balance') or row.get('Closing Balance', 0)):.2f}",
                "status": "credited" if amt >= 0 else "debited",
            })
        return records
