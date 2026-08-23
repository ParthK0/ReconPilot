import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

from backend.db.models import Base

load_dotenv()


def get_database_url() -> str:
    """
    Builds the database URL from environment variables.
    Supports DATABASE_URL or discrete POSTGRES_* environment variables.
    Falls back to a local SQLite database for development/testing if no Postgres config is found.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Standardize postgres:// to postgresql:// for SQLAlchemy
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url

    pg_user = os.getenv("POSTGRES_USER")
    pg_password = os.getenv("POSTGRES_PASSWORD")
    pg_host = os.getenv("POSTGRES_HOST")
    pg_port = os.getenv("POSTGRES_PORT", "5432")
    pg_db = os.getenv("POSTGRES_DB")

    if pg_user and pg_host and pg_db:
        auth = f"{pg_user}:{pg_password}@" if pg_password else f"{pg_user}@"
        return f"postgresql://{auth}{pg_host}:{pg_port}/{pg_db}"

    # Fallback to local SQLite database if Postgres is not configured
    return os.getenv("SQLITE_FALLBACK_URL", "sqlite:///./reconpilot.db")


DATABASE_URL = get_database_url()

# Configure engine with appropriate connect args
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initializes the database schema."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
