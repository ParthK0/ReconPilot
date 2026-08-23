import io
from decimal import Decimal
from typing import List, Dict, Any
import pandas as pd


def generate_reconciliation_csv(records_data: List[Dict[str, Any]]) -> str:
    """
    FR-13 / FR-15: Generates final reconciliation export CSV.
    Fields: record_id, order_id, source_type, amount, status, match_method, confidence, evidence, reviewer_action
    """
    df = pd.DataFrame(records_data)
    if df.empty:
        df = pd.DataFrame(
            columns=[
                "record_id",
                "order_id",
                "source_type",
                "amount",
                "status",
                "match_method",
                "confidence",
                "evidence",
                "reviewer_action",
            ]
        )
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue()
