import io
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Union, BinaryIO, TextIO, Tuple
import pandas as pd


class ParserError(Exception):
    """Base exception for all CSV parser errors."""
    pass


class SchemaValidationError(ParserError):
    """
    FR-2: Specific exception raised when a CSV fails column schema validation.
    Provides detailed error information about missing and expected columns.
    """
    def __init__(
        self,
        message: str,
        missing_columns: List[str] = None,
        expected_columns: List[str] = None,
        actual_columns: List[str] = None,
        source_type: str = "",
    ):
        super().__init__(message)
        self.missing_columns = missing_columns or []
        self.expected_columns = expected_columns or []
        self.actual_columns = actual_columns or []
        self.source_type = source_type


class InvalidCSVFormatError(ParserError):
    """Raised when CSV content is unparseable or improperly formatted."""
    pass


class EmptyFileError(ParserError):
    """Raised when the uploaded file or stream contains no data."""
    pass


# Expected column schemas per source type
EXPECTED_COLUMNS: Dict[str, List[str]] = {
    "invoice": [
        "invoice_id",
        "order_id",
        "amount",
        "invoice_date",
        "customer_name",
        "status",
    ],
    "settlement": [
        "settlement_id",
        "order_id",
        "amount",
        "settlement_date",
        "reference_number",
        "status",
        "fees",
        "gst",
        "tds",
    ],
    "bank": [
        "bank_txn_id",
        "txn_date",
        "description",
        "reference_number",
        "amount",
        "balance",
        "status",
    ],
}


class BaseCSVParser(ABC):
    """
    Abstract base class for source-specific CSV parsers.
    Enforces FR-2 strict column schema validation.
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """The source type identifier (invoice, settlement, bank)."""
        pass

    @property
    def expected_columns(self) -> List[str]:
        return EXPECTED_COLUMNS[self.source_type]

    def _read_to_dataframe(self, source: Union[str, bytes, Path, TextIO, BinaryIO]) -> pd.DataFrame:
        """
        Reads diverse input types (path, string, bytes, file stream) into a DataFrame.
        """
        try:
            if isinstance(source, (str, Path)) and os.path.exists(str(source)):
                df = pd.read_csv(str(source))
            elif isinstance(source, str):
                if not source.strip():
                    raise EmptyFileError(f"Cannot parse empty string for '{self.source_type}' CSV.")
                df = pd.read_csv(io.StringIO(source))
            elif isinstance(source, bytes):
                if not source.strip():
                    raise EmptyFileError(f"Cannot parse empty byte content for '{self.source_type}' CSV.")
                df = pd.read_csv(io.BytesIO(source))
            elif hasattr(source, "read"):
                content = source.read()
                if isinstance(content, bytes):
                    if not content.strip():
                        raise EmptyFileError(f"Cannot parse empty stream for '{self.source_type}' CSV.")
                    df = pd.read_csv(io.BytesIO(content))
                else:
                    if not str(content).strip():
                        raise EmptyFileError(f"Cannot parse empty stream for '{self.source_type}' CSV.")
                    df = pd.read_csv(io.StringIO(str(content)))
            else:
                raise InvalidCSVFormatError(f"Unsupported source type for parsing: {type(source)}")
        except (EmptyFileError, SchemaValidationError):
            raise
        except Exception as e:
            raise InvalidCSVFormatError(f"Failed to parse CSV for '{self.source_type}': {str(e)}") from e

        if df.empty and len(df.columns) == 0:
            raise EmptyFileError(f"Parsed CSV is completely empty for '{self.source_type}'.")

        return df

    def validate_schema(self, df: pd.DataFrame) -> None:
        """
        FR-2: Validates that all required columns are present in the DataFrame.
        Rejects malformed files with SchemaValidationError.
        """
        actual_columns = [str(col).strip().lower() for col in df.columns]
        df.columns = actual_columns

        missing = [col for col in self.expected_columns if col not in actual_columns]
        if missing:
            raise SchemaValidationError(
                f"Schema validation failed for '{self.source_type}' CSV. "
                f"Missing required column(s): {', '.join(missing)}. "
                f"Expected: {', '.join(self.expected_columns)}. "
                f"Found: {', '.join(actual_columns)}.",
                missing_columns=missing,
                expected_columns=self.expected_columns,
                actual_columns=actual_columns,
                source_type=self.source_type,
            )

    def parse(self, source: Union[str, bytes, Path, TextIO, BinaryIO]) -> pd.DataFrame:
        """
        Parses and validates CSV source, returning a validated DataFrame.
        """
        df = self._read_to_dataframe(source)
        self.validate_schema(df)
        return df


class InvoiceParser(BaseCSVParser):
    """
    Parser for Customer Invoices CSV.
    Expected columns: invoice_id, order_id, amount, invoice_date, customer_name, status.
    """
    @property
    def source_type(self) -> str:
        return "invoice"


class SettlementParser(BaseCSVParser):
    """
    Parser for Razorpay Settlement Report CSV.
    Expected columns: settlement_id, order_id, amount, settlement_date, reference_number, status, fees, gst, tds.
    """
    @property
    def source_type(self) -> str:
        return "settlement"


class BankStatementParser(BaseCSVParser):
    """
    Parser for Bank Statement CSV.
    Expected columns: bank_txn_id, txn_date, description, reference_number, amount, balance, status.
    """
    @property
    def source_type(self) -> str:
        return "bank"


class SmartCSVParser:
    """
    Schema-Agnostic Intelligent CSV Parser.
    Automatically maps unknown, dirty, or merchant-specific column names into canonical schema.
    """

    def __init__(self, source_type: str):
        self.source_type = source_type.strip().lower()
        self.base_parser = get_parser(self.source_type)

    def parse(
        self,
        source: Union[str, bytes, Path, TextIO, BinaryIO],
        auto_map_schema: bool = True,
    ) -> Tuple[pd.DataFrame, Any]:
        """
        Parses CSV source, automatically detecting and remapping non-standard column names if necessary.
        Returns a tuple of (canonical_df, schema_mapping).
        """
        from backend.schema_mapper.mapper import default_schema_mapper, SchemaMapping

        df = self.base_parser._read_to_dataframe(source)
        # First check if schema is already perfectly matching
        try:
            self.base_parser.validate_schema(df.copy())
            mapping = default_schema_mapper.map_columns(list(df.columns), self.source_type)
            return df, mapping
        except SchemaValidationError:
            if not auto_map_schema:
                raise
            # Schema failed strict check -> run schema mapper
            remapped_df, mapping = default_schema_mapper.remap_dataframe(df, self.source_type)
            if not mapping.is_valid:
                suggested_missing = {
                    target: mapping.suggested_mappings[target]
                    for target in mapping.missing_required
                    if target in mapping.suggested_mappings
                }
                unmappable_missing = [
                    target for target in mapping.missing_required
                    if target not in mapping.suggested_mappings
                ]

                if suggested_missing:
                    details = [
                        f"'{t}' (suggested '{s['source_column']}' via {s['method']}, confidence={s['confidence']:.2f})"
                        for t, s in suggested_missing.items()
                    ]
                    if unmappable_missing:
                        details.append(f"unmappable: {', '.join(unmappable_missing)}")
                    raise SchemaValidationError(
                        f"Schema validation failed for '{self.source_type}' CSV: requires user confirmation for low-confidence mapping(s). "
                        f"Unresolved required field(s): {'; '.join(details)}. "
                        f"Expected: {', '.join(self.base_parser.expected_columns)}. "
                        f"Found (raw): {', '.join(df.columns)}.",
                        missing_columns=mapping.missing_required,
                        expected_columns=self.base_parser.expected_columns,
                        actual_columns=list(df.columns),
                        source_type=self.source_type,
                    )
                else:
                    raise SchemaValidationError(
                        f"Schema validation failed for '{self.source_type}' CSV: required column(s) could not be mapped by any method. "
                        f"Missing required column(s): {', '.join(mapping.missing_required)}. "
                        f"Expected: {', '.join(self.base_parser.expected_columns)}. "
                        f"Found (raw): {', '.join(df.columns)}.",
                        missing_columns=mapping.missing_required,
                        expected_columns=self.base_parser.expected_columns,
                        actual_columns=list(df.columns),
                        source_type=self.source_type,
                    )
            return remapped_df, mapping


def get_smart_parser(source_type: str) -> SmartCSVParser:
    """Factory helper to obtain a SmartCSVParser."""
    return SmartCSVParser(source_type)


def parse_smart_csv(
    content: Union[str, bytes, Path, TextIO, BinaryIO],
    source_type: str,
    auto_map: bool = True,
) -> Tuple[pd.DataFrame, Any]:
    """Convenience helper for parsing CSV with intelligent schema mapping."""
    parser = get_smart_parser(source_type)
    return parser.parse(content, auto_map_schema=auto_map)


def get_parser(source_type: str) -> BaseCSVParser:
    """
    Factory function to retrieve the appropriate parser for a given source type.
    """
    source_lower = source_type.strip().lower()
    if source_lower == "invoice":
        return InvoiceParser()
    elif source_lower == "settlement":
        return SettlementParser()
    elif source_lower in ("bank", "bank_statement", "bank_statements"):
        return BankStatementParser()
    else:
        raise ValueError(f"Unknown source_type '{source_type}'. Expected one of: 'invoice', 'settlement', 'bank'.")


def validate_csv_schema(df: pd.DataFrame, source_type: str) -> None:
    """Convenience helper for schema validation."""
    parser = get_parser(source_type)
    parser.validate_schema(df)


def parse_csv_content(content: Union[str, bytes, Path, TextIO, BinaryIO], source_type: str) -> pd.DataFrame:
    """Convenience helper for parsing CSV content with schema validation."""
    parser = get_parser(source_type)
    return parser.parse(content)

