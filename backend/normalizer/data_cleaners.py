import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
import pandas as pd


def clean_currency(val: Any, default: Decimal = Decimal("0.00")) -> Decimal:
    """
    Cleans dirty currency inputs into a Decimal.
    Handles formats like:
      - '₹12,000'
      - '12,000.00'
      - '₹ 12,000.50'
      - '12000 INR'
      - '12000.00'
      - '-₹50.00' or '(50.00)' (negative amounts)
    """
    if val is None or pd.isna(val):
        return default
    
    if isinstance(val, (int, float)):
        return Decimal(str(val))
    if isinstance(val, Decimal):
        return val

    val_str = str(val).strip()
    if not val_str:
        return default

    # Check for accounting style negative numbers in parentheses: (100.00) -> -100.00
    is_negative = False
    if val_str.startswith("(") and val_str.endswith(")"):
        is_negative = True
        val_str = val_str[1:-1].strip()
    elif val_str.startswith("-"):
        is_negative = True
        val_str = val_str[1:].strip()

    # Remove currency symbols (₹, $, €, £), INR, commas, and extra whitespace
    cleaned = re.sub(r"[₹\$€£]|INR|Rs\.?|rs\.?", "", val_str, flags=re.IGNORECASE)
    cleaned = cleaned.replace(",", "").strip()

    try:
        dec = Decimal(cleaned)
        return -dec if is_negative else dec
    except (InvalidOperation, ValueError):
        return default


def clean_date(val: Any, default_year: int = 2026) -> date:
    """
    Robust date parser supporting varied date formats:
      - '2026-08-21' (ISO)
      - '21/08/2026', '21-08-2026' (DD/MM/YYYY)
      - '2026/08/21' (YYYY/MM/DD)
      - '08/21/2026' (MM/DD/YYYY)
      - '21/08/26', '21-08-26' (DD/MM/YY)
      - '08-21-26', '08/21/26' (MM-DD-YY)
      - '21 Aug 2026', '21-Aug-2026', '21 Aug 26', '21-Aug-26'
      - 'Aug 21, 2026', 'August 21, 2026'
      - '21 Aug' (DD Mon -> assumed default_year)
      - ISO datetime with 'T' e.g. '2026-08-21T14:30:00'
    """
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()

    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "none", "nat"):
        raise ValueError(f"Unable to parse empty date: '{val}'")

    # Handle ISO datetime with 'T' or timezone
    if "T" in val_str:
        try:
            return datetime.fromisoformat(val_str.replace("Z", "+00:00")).date()
        except ValueError:
            pass

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%m-%d-%y",
        "%m/%d/%y",
        "%d %b %Y",
        "%d-%b-%Y",
        "%d %B %Y",
        "%d-%B-%Y",
        "%d %b %y",
        "%d-%b-%y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%B %d %Y",
        "%Y%m%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue

    # Try 'DD Mon' (e.g. '21 Aug' or '21-Aug')
    for fmt in ("%d %b", "%d-%b", "%d %B", "%d-%B"):
        try:
            parsed = datetime.strptime(val_str, fmt)
            return parsed.replace(year=default_year).date()
        except ValueError:
            continue

    raise ValueError(f"Unable to parse date string: '{val_str}'")


def clean_reference(val: Any) -> Optional[str]:
    """
    Normalizes transaction references/UTRs:
    - 'ABC-123' -> 'ABC123'
    - 'abc 123' -> 'ABC123'
    - 'UTR 2026-08-0001' -> 'UTR2026080001'
    - '  ABC123  ' -> 'ABC123'
    """
    if val is None or pd.isna(val):
        return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "none", "null"):
        return None
    
    # Strip spaces and hyphens for canonical join matching, upper-cased
    cleaned = re.sub(r"[\s\-_]", "", val_str).upper()
    return cleaned if cleaned else None


def clean_order_id(val: Any) -> Optional[str]:
    """
    Normalizes order IDs:
    - Trims whitespace and standardizes casing.
    """
    if val is None or pd.isna(val):
        return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "none", "null"):
        return None
    # For order ids, preserve standard uppercase representation
    return val_str.upper()


def clean_status(val: Any, default: str = "paid") -> str:
    """
    Maps various status representations to canonical status tokens.
    """
    if val is None or pd.isna(val):
        return default
    val_str = str(val).strip().lower()
    if not val_str:
        return default

    status_mapping = {
        "success": "paid",
        "paid": "paid",
        "captured": "paid",
        "completed": "paid",
        "settled": "settled",
        "credited": "credited",
        "debited": "debited",
        "pending": "pending",
        "pending_settlement": "pending_settlement",
        "processing": "pending",
        "refunded": "refunded",
        "refund_processed": "refund_processed",
        "reversed": "refund_processed",
        "failed": "failed",
    }
    return status_mapping.get(val_str, val_str)
