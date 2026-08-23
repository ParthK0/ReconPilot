import os
import uuid
from decimal import Decimal
from datetime import date
import pandas as pd
import pytest
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal, init_db, engine
from backend.db.models import Base, Batch, Record
from backend.parser import (
    InvoiceParser,
    SettlementParser,
    BankStatementParser,
    get_parser,
    parse_csv_content,
    SchemaValidationError,
    InvalidCSVFormatError,
    EmptyFileError,
    EXPECTED_COLUMNS,
)
from backend.normalizer import (
    NormalizedRecord,
    normalize_record,
    normalize_dataframe,
    persist_normalized_records,
    normalize_and_persist,
)

SYNTHETIC_DATA_DIR = "backend/synthetic-data"


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure database tables exist for test run."""
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db_session():
    """Provides a transactional database session for tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ---------------------------------------------------------------------------
# 1. Tests for Well-Formed Files Parsing Correctly (FR-1)
# ---------------------------------------------------------------------------

def test_invoice_parser_well_formed_fixture():
    """Tests that the synthetic invoices.csv fixture parses into 100 validated rows."""
    fixture_path = os.path.join(SYNTHETIC_DATA_DIR, "invoices.csv")
    assert os.path.exists(fixture_path), f"Fixture missing: {fixture_path}"

    parser = InvoiceParser()
    df = parser.parse(fixture_path)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 100
    for col in EXPECTED_COLUMNS["invoice"]:
        assert col in df.columns


def test_settlement_parser_well_formed_fixture():
    """Tests that the synthetic settlements.csv fixture parses into 100 validated rows."""
    fixture_path = os.path.join(SYNTHETIC_DATA_DIR, "settlements.csv")
    assert os.path.exists(fixture_path), f"Fixture missing: {fixture_path}"

    parser = SettlementParser()
    df = parser.parse(fixture_path)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 100
    for col in EXPECTED_COLUMNS["settlement"]:
        assert col in df.columns


def test_bank_parser_well_formed_fixture():
    """Tests that the synthetic bank_statements.csv fixture parses into 100 validated rows."""
    fixture_path = os.path.join(SYNTHETIC_DATA_DIR, "bank_statements.csv")
    assert os.path.exists(fixture_path), f"Fixture missing: {fixture_path}"

    parser = BankStatementParser()
    df = parser.parse(fixture_path)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 100
    for col in EXPECTED_COLUMNS["bank"]:
        assert col in df.columns


# ---------------------------------------------------------------------------
# 2. Tests for Missing Required Column Rejection (FR-2)
# ---------------------------------------------------------------------------

def test_invoice_parser_rejects_missing_column():
    """Asserts that InvoiceParser rejects CSV with missing required column (e.g. invoice_date)."""
    malformed_csv = "invoice_id,order_id,amount,customer_name,status\nINV-001,ORD-001,500.00,Alice,paid\n"
    parser = InvoiceParser()

    with pytest.raises(SchemaValidationError) as exc_info:
        parser.parse(malformed_csv)

    err = exc_info.value
    assert "invoice_date" in err.missing_columns
    assert err.source_type == "invoice"
    assert "Schema validation failed for 'invoice' CSV" in str(err)


def test_settlement_parser_rejects_missing_column():
    """Asserts that SettlementParser rejects CSV with missing required columns (e.g. reference_number, tds)."""
    malformed_csv = "settlement_id,order_id,amount,settlement_date,status,fees,gst\nSET-001,ORD-001,480.00,2026-08-02,settled,20.00,0.00\n"
    parser = SettlementParser()

    with pytest.raises(SchemaValidationError) as exc_info:
        parser.parse(malformed_csv)

    err = exc_info.value
    assert "reference_number" in err.missing_columns
    assert "tds" in err.missing_columns
    assert err.source_type == "settlement"


def test_bank_parser_rejects_missing_column():
    """Asserts that BankStatementParser rejects CSV missing required columns (e.g. balance)."""
    malformed_csv = "bank_txn_id,txn_date,description,reference_number,amount,status\nBNK-001,2026-08-02,ACH CR,UTR001,480.00,credited\n"
    parser = BankStatementParser()

    with pytest.raises(SchemaValidationError) as exc_info:
        parser.parse(malformed_csv)

    err = exc_info.value
    assert "balance" in err.missing_columns
    assert err.source_type == "bank"


def test_parser_rejects_empty_file():
    """Asserts that parsers reject empty files with EmptyFileError."""
    parser = InvoiceParser()
    with pytest.raises(EmptyFileError):
        parser.parse("")


# ---------------------------------------------------------------------------
# 3. Tests for Unified Schema Field Population per Source Type (FR-3)
# ---------------------------------------------------------------------------

def test_unified_schema_field_population_invoice():
    """
    Asserts every field in the unified schema is correctly populated for an invoice row.
    """
    parser = InvoiceParser()
    df = parser.parse(os.path.join(SYNTHETIC_DATA_DIR, "invoices.csv"))
    records = normalize_dataframe(df, "invoice", batch_id="test-batch-inv")

    assert len(records) == 100
    rec = records[0]

    assert rec.batch_id == "test-batch-inv"
    assert rec.source_type == "invoice"
    assert rec.transaction_id == "INV-0001"
    assert rec.order_id == "ORD-2026-EX-0001"
    assert isinstance(rec.amount, Decimal)
    assert rec.amount == Decimal("1000.00")
    assert isinstance(rec.txn_date, date)
    assert rec.txn_date == date(2026, 8, 1)
    assert rec.reference_number is None  # invoices do not have UTR
    assert rec.status == "paid"
    assert rec.fees == Decimal("0.00")
    assert rec.gst == Decimal("0.00")
    assert rec.tds == Decimal("0.00")
    assert isinstance(rec.raw_payload, dict)
    assert rec.raw_payload["customer_name"] == "Customer_1"


def test_unified_schema_field_population_settlement():
    """
    Asserts every field in the unified schema is correctly populated for a settlement row.
    """
    parser = SettlementParser()
    df = parser.parse(os.path.join(SYNTHETIC_DATA_DIR, "settlements.csv"))
    records = normalize_dataframe(df, "settlement", batch_id="test-batch-set")

    assert len(records) == 100
    rec = records[0]

    assert rec.batch_id == "test-batch-set"
    assert rec.source_type == "settlement"
    assert rec.transaction_id == "SET-0001"
    assert rec.order_id == "ORD-2026-EX-0001"
    assert isinstance(rec.amount, Decimal)
    assert rec.amount == Decimal("1000.00")
    assert isinstance(rec.txn_date, date)
    assert rec.txn_date == date(2026, 8, 2)
    assert rec.reference_number == "UTR202608000001"
    assert rec.status == "settled"
    assert isinstance(rec.fees, Decimal)
    assert isinstance(rec.gst, Decimal)
    assert isinstance(rec.tds, Decimal)
    assert isinstance(rec.raw_payload, dict)


def test_unified_schema_field_population_bank():
    """
    Asserts every field in the unified schema is correctly populated for a bank row.
    """
    parser = BankStatementParser()
    df = parser.parse(os.path.join(SYNTHETIC_DATA_DIR, "bank_statements.csv"))
    records = normalize_dataframe(df, "bank", batch_id="test-batch-bnk")

    assert len(records) == 100
    rec = records[0]

    assert rec.batch_id == "test-batch-bnk"
    assert rec.source_type == "bank"
    assert rec.transaction_id == "BNK-0001"
    assert rec.order_id is None  # bank rows don't have order_id
    assert isinstance(rec.amount, Decimal)
    assert rec.amount == Decimal("1000.00")
    assert isinstance(rec.txn_date, date)
    assert rec.txn_date == date(2026, 8, 2)
    assert rec.reference_number == "UTR202608000001"
    assert rec.status == "credited"
    assert rec.fees == Decimal("0.00")
    assert rec.gst == Decimal("0.00")
    assert rec.tds == Decimal("0.00")
    assert isinstance(rec.raw_payload, dict)
    assert "balance" in rec.raw_payload


# ---------------------------------------------------------------------------
# 4. Tests for Database Persistence (Writing records into PostgreSQL)
# ---------------------------------------------------------------------------

def test_database_persistence_all_three_sources(db_session: Session):
    """
    Tests creating a Batch and persisting normalized records from all three CSV sources
    into the database `records` table, verifying all columns round-trip correctly.
    """
    # Create batch
    batch = Batch(
        id=str(uuid.uuid4()),
        settlement_filename="settlements.csv",
        bank_filename="bank_statements.csv",
        invoice_filename="invoices.csv",
        status="uploaded",
    )
    db_session.add(batch)
    db_session.commit()

    # Parse and normalize all three sources
    inv_df = InvoiceParser().parse(os.path.join(SYNTHETIC_DATA_DIR, "invoices.csv"))
    set_df = SettlementParser().parse(os.path.join(SYNTHETIC_DATA_DIR, "settlements.csv"))
    bnk_df = BankStatementParser().parse(os.path.join(SYNTHETIC_DATA_DIR, "bank_statements.csv"))

    inv_records = normalize_and_persist(db_session, inv_df, "invoice", batch.id)
    set_records = normalize_and_persist(db_session, set_df, "settlement", batch.id)
    bnk_records = normalize_and_persist(db_session, bnk_df, "bank", batch.id)

    assert len(inv_records) == 100
    assert len(set_records) == 100
    assert len(bnk_records) == 100

    # Query back from DB
    db_rows = db_session.query(Record).filter(Record.batch_id == batch.id).all()
    assert len(db_rows) == 300

    # Verify breakdown by source_type
    counts_by_source = {}
    for r in db_rows:
        counts_by_source[r.source_type] = counts_by_source.get(r.source_type, 0) + 1

    assert counts_by_source["invoice"] == 100
    assert counts_by_source["settlement"] == 100
    assert counts_by_source["bank"] == 100

    # Check a settlement record with non-zero fees/taxes
    set_with_fee = db_session.query(Record).filter(
        Record.batch_id == batch.id,
        Record.source_type == "settlement",
        Record.fees > Decimal("0.00")
    ).first()
    assert set_with_fee is not None
    assert set_with_fee.fees > Decimal("0.00")
    assert set_with_fee.raw_payload is not None
