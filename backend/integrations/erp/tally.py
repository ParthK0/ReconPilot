"""
backend/integrations/erp/tally.py
=================================
Tally Prime & ERP 9 Invoice Adapter for ReconPilot.
Parses Tally sales register exports into canonical invoice records.
"""

from typing import Any, Dict, List
import pandas as pd
from backend.integrations.base import BaseERPAdapter
from backend.normalizer.data_cleaners import clean_currency, clean_date, clean_order_id


class TallyERPAdapter(BaseERPAdapter):
    """Parses Tally ERP sales voucher registers."""

    @property
    def erp_name(self) -> str:
        return "tally"

    def import_invoices(self, raw_content: Any) -> List[Dict[str, Any]]:
        if isinstance(raw_content, pd.DataFrame):
            df = raw_content
        else:
            df = pd.read_csv(raw_content)

        records = []
        for _, row in df.iterrows():
            amt = clean_currency(row.get("amount") or row.get("billed_amount") or row.get("Gross Total"))
            records.append({
                "invoice_id": str(row.get("invoice_id") or row.get("bill_no") or row.get("Vch No.")),
                "order_id": clean_order_id(row.get("order_id") or row.get("order_number") or row.get("Buyer Ref")),
                "amount": f"{amt:.2f}",
                "invoice_date": clean_date(row.get("invoice_date") or row.get("bill_date") or row.get("Date")).isoformat(),
                "customer_name": str(row.get("customer_name") or row.get("Party's Name") or "Customer"),
                "status": "paid",
            })
        return records
