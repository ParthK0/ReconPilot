# Database Migration Versions

This directory contains versioned Alembic migration scripts for ReconPilot.
To generate a new schema revision:
```bash
alembic revision --autogenerate -m "description of changes"
```
To apply migrations:
```bash
alembic upgrade head
```
