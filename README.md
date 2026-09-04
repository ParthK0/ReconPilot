# ReconPilot — AI-Powered 3-Way Finance Reconciliation Engine

> **Razorpay AI Buildathon 2026 — Track 04: AI Finance Controller**  
> *"Throughput plus measured accuracy plus an honest exception list. One cherry-picked match proves nothing."*

[![Python](https://img.shields.io/badge/Python-3.11%2B%20%7C%203.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose%20Ready-2496ED?logo=docker)](docker-compose.yml)
[![Tests](https://img.shields.io/badge/Tests-28%20Suites%20%7C%2097%20Cases%20(78%25%20Cov)-brightgreen?logo=pytest)](tests/)
[![Precision](https://img.shields.io/badge/Precision-100.0%25-success)](backend/evaluation/score.py)
[![Recall](https://img.shields.io/badge/Recall-100.0%25-success)](backend/evaluation/score.py)
[![License](https://img.shields.io/badge/License-MIT-purple)](#-license)

---

## 🎯 What Is ReconPilot?

ReconPilot is an **enterprise-grade, high-throughput financial reconciliation platform** that automates 3-way matching across:

1. **Razorpay Settlement Reports** — Net payouts after MDR fees, GST (18%), and TDS (1% §194-O)
2. **Bank Statements** — Actual ACH/NEFT credits identified by UTR numbers
3. **Internal ERP Invoice Registers** — Original customer-billed amounts

### The Problem It Solves

Indian merchants using Razorpay must manually cross-check three disjoint financial data sources every settlement cycle. This process:
- Takes **~3 minutes per record** (manual baseline from `docs/01-PRD.md`)
- Is error-prone with complex fee structures (MDR + GST on MDR + TDS on gross)
- Creates audit trail gaps when discrepancies are resolved informally
- Delays cash position visibility by days

### How ReconPilot Solves It

Built upon a strict **"Rules-Before-AI"** architecture:
- **86%+ of transactions** are resolved through **sub-millisecond deterministic rules** (7 ordered rules)
- **~6% of residual edge cases** are verified by a constrained LLM with **temperature=0.0**
- **Every AI claim** is mathematically proved by a **Deterministic Arithmetic Validator** before any ledger write
- **~8% genuine exceptions** are honestly categorized into 30+ taxonomic buckets for human review
- **Zero false positives** — 100% precision verified against ground truth

---

## 📊 Live Evaluation Benchmark

Every metric below is computed by [`backend/evaluation/score.py`](backend/evaluation/score.py) against ground-truth labeled datasets across **11 distinct industry archetypes**:

| Metric | Target | Standard Benchmark | Adversarial Benchmark | Status |
|---|---|---|---|---|
| **Reconciliation Precision** | ≥ 99.0% (Stretch 100%) | **`100.0000%`** (92/92) | **`100.0000%`** (92/92) | 🟢 Stretch Achieved |
| **Reconciliation Recall** | ≥ 90.0% (Stretch ≥ 95%) | **`100.0000%`** (92/92) | **`100.0000%`** (92/92) | 🟢 Stretch Achieved |
| **F1 Score** | ≥ 0.95 | **`1.000000`** | **`1.000000`** | 🟢 PASSED |
| **False Positives** | Zero (0) | **`0`** | **`0`** | 🟢 PASSED |
| **False Negatives** | Zero (0) | **`0`** | **`0`** | 🟢 PASSED |
| **Throughput (100 records)** | < 30s (Stretch < 15s) | **`~0.44 seconds`** | **`~0.63 seconds`** | 🟢 Stretch Achieved |
| **10k Scalability** | < 60s for 10,000 rows | **`~3.84 seconds`** | **`~3.84 seconds`** | 🟢 PASSED |
| **Manual Hours Saved** | Dynamic ROI | **`4.60 hours / batch`** | **`4.80 hours / batch`** | 🟢 PASSED |

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph INGESTION["1. Smart Ingestion & Schema Understanding"]
        CSV_INV["📄 Invoice Register CSV"]
        CSV_SET["📑 Razorpay Settlements CSV"]
        CSV_BNK["🏦 Bank Statements CSV"]

        SM["🧠 Safe Schema Mapper\n(178 Aliases + AI Fallback ≥ 0.95)"]
        CLEAN["🧹 Universal Data Cleaners\n(Currencies, Dates, UTRs, Order IDs)"]
        FORMULA["🛡️ CSV Formula Injection Neutralizer"]
        NORM["⚙️ Unified Data Normalizer"]

        CSV_INV --> SM --> CLEAN --> FORMULA --> NORM
        CSV_SET --> SM
        CSV_BNK --> SM
    end

    subgraph RULES["2. Configurable Deterministic Rule Engine (Sub-ms)"]
        NORM --> R1{"Rule 1: Exact Order ID"}
        R1 -- Match --> MATCHED["✅ Matched (100% Confidence)"]
        R1 -- Miss --> R2{"Rule 2: Exact UTR / Reference"}
        R2 -- Match --> MATCHED
        R2 -- Miss --> R3{"Rule 3: Exact Amount"}
        R3 -- Match --> MATCHED
        R3 -- Miss --> R4{"Rule 4: Date Window (T+2)"}
        R4 -- Match --> MATCHED
        R4 -- Miss --> R5{"Rule 5: Fee/GST/TDS Schedule\n(Dynamic Merchant Profile)"}
        R5 -- Match --> MATCHED
        R5 -- Miss --> R6{"Rule 6: Penny Tolerance Match\n(≤ ₹2.00 Rounding Band)"}
        R6 -- Match --> MATCHED
        R6 -- Miss --> R7{"Rule 7: FX Spread Corridor\n(0.5-4.0% International)"}
        R7 -- Match --> MATCHED
    end

    subgraph AI_ENGINE["3. Finance Verification Engine & Safety Guard"]
        R7 -- Miss --> CTX["📦 Context Assembler & Delta Calculator"]
        CTX --> CLUSTER["🔗 Cluster Micro-Batcher\n(90-95% Token Reduction)"]
        CLUSTER --> MEM["🧠 Multi-Factor Feedback Memory"]
        MEM --> LLM["🤖 LLM Financial Reasoner\n(Gemini 2.5 Pro / GPT-5.6 Terra)"]
        LLM --> VAL{"🛡️ Deterministic Arithmetic Validator\n(Equation Solver & Error Bounding)"}

        VAL -- "Equation Proved" --> AI_MATCH["✨ AI-Verified Match (80-99% Conf)"]
        VAL -- "Arithmetic Failed" --> EXC["⚠️ Exception Taxonomy Classifier"]
    end

    subgraph OPERATIONS["4. Analytics, Cash Position & Audit Dashboard"]
        MATCHED --> DASH["📊 Live Financial Dashboard"]
        AI_MATCH --> DASH
        EXC --> TAX["30+ Exception Categories\n(8 Operational Domains)"]
        TAX --> DASH

        DASH --> CASH["💰 Treasury & Float Analytics"]
        DASH --> RECHARTS["📈 Recharts Visualizations"]
        DASH --> AUDIT["📋 Audit-Ready CSV + ERP Export\n(Tally / Zoho / NetSuite)"]
        DASH --> FEEDBACK["🔄 Human Review & Approval"]
        FEEDBACK --> MEM
    end
```

---

## ⚡ Core Engineering — Function-Level Breakdown

### 1. Ingestion Layer (`backend/parser/`, `backend/normalizer/`, `backend/schema_mapper/`)

| Module | Key Functions | Purpose | Lines |
|---|---|---|---|
| [`csv_parser.py`](backend/parser/csv_parser.py) | `InvoiceParser.parse()`, `SettlementParser.parse()`, `BankStatementParser.parse()` | Strict column validation via `EXPECTED_COLUMNS`; raises `SchemaValidationError` on missing headers; handles file paths, strings, bytes, and streams | 272 |
| [`normalizer.py`](backend/normalizer/normalizer.py) | `normalize_invoice_row()`, `normalize_settlement_row()`, `normalize_bank_row()`, `normalize_dataframe()`, `persist_normalized_records()` | Coerces raw CSV rows into `NormalizedRecord` Pydantic models with `Decimal` amounts and parsed dates | 168 |
| [`data_cleaners.py`](backend/normalizer/data_cleaners.py) | `clean_currency()`, `clean_date()`, `clean_reference()`, `clean_order_id()`, `clean_status()` | Strips ₹ symbols, normalizes 20+ date formats, removes commas and parenthetical negatives | 167 |
| [`mapper.py`](backend/schema_mapper/mapper.py) | `map_schema()`, `_alias_mapping()`, `_ai_column_inference()` | 3-phase schema mapping: exact → 178 alias dict → LLM inference with ≥0.95 confidence gating | 306 |
| [`aliases.py`](backend/schema_mapper/aliases.py) | `COLUMN_ALIASES` | 178 alias definitions covering invoice, settlement, and bank column naming variants | 240 |

### 2. Rule Engine (`backend/rules/`)

| Module | Key Functions | Purpose | Lines |
|---|---|---|---|
| [`rule_engine.py`](backend/rules/rule_engine.py) | `match_exact_order_id()`, `match_exact_reference_number()`, `match_exact_amount()`, `match_settlement_date_window()`, `match_fee_gst_tds_adjusted_amount()`, `match_tolerance_amount()`, `match_fx_spread_tolerance()`, `apply_rules_in_order()`, `find_duplicate_order_ids()` | 7-tier priority matching pipeline. Pure functions, no side effects. `Decimal` arithmetic with `ROUND_HALF_UP`. Configurable via `FeeConfig`. | 415 |
| [`adjusted_amount.py`](backend/rules/adjusted_amount.py) | `validate_adjusted_amount()` | Verifies statutory fee schedule adherence (2% MDR, 18% GST on fee, 1% TDS on gross) | 100 |
| [`exception_taxonomy.py`](backend/rules/exception_taxonomy.py) | `list_exception_categories()`, `get_exception_definition()`, `EXCEPTION_DEFINITIONS` | 30+ exception categories across 8 operational domains with suggested actions and financial impact classification | 342 |

**Rule Details:**

| Rule | Function | Confidence | What It Does |
|---|---|---|---|
| R1 | `match_exact_order_id()` | 100% | Exact `order_id` + amount equality + T+2 window + status checks |
| R2 | `match_exact_reference_number()` | 100% | UTR/reference number match across settlement ↔ bank |
| R3 | `match_exact_amount()` | 99% | Unadjusted amount equality within settlement window |
| R4 | `match_settlement_date_window()` | 98% | Transaction amount match verified within T+2 |
| R5 | `match_fee_gst_tds_adjusted_amount()` | 95% | Applies configurable MDR/GST/TDS rate card deductions |
| R6 | `match_tolerance_amount()` | 95% | Near-amount match within ≤₹2.00 rounding tolerance |
| R7 | `match_fx_spread_tolerance()` | 94% | International FX spread corridor (0.5%–4.0%) matching |

### 3. AI Engine (`backend/ai/`)

| Module | Key Functions | Purpose | Lines |
|---|---|---|---|
| [`engine.py`](backend/ai/engine.py) | `verify_discrepancy()`, `verify_discrepancies_clustered()`, `assemble_context_payload()`, `_simulate_llm_reasoning()` | Full AI orchestration: context assembly → feedback memory → LLM call → validator → audit persistence. Cluster micro-batching groups by `(status, delta_ratio, date_offset)` hash, reducing API calls by 90-95%. | 627 |
| [`validator.py`](backend/ai/validator.py) | `validate_finance_verification()`, `validate_verification_math()` | **Core safety anchor.** Completely discards LLM self-reported confidence. Re-derives arithmetic: `invoice - fees - gst - tds == settlement`. Assigns deterministic scores: 99% (exact) / 88% (rounding) / 65% (unconfirmable) / 40% (contradicted). | 100 |
| [`llm_client.py`](backend/ai/llm_client.py) | `LLMClient.call_llm()`, `_call_gemini()`, `_call_openai()`, `_simulate_response()` | Multi-provider gateway: Gemini + OpenAI. `temperature=0.0`, strict JSON schema, exponential backoff retry, per-call and cumulative cost accounting, `AI_SPEND_CEILING_USD` budget enforcement. | 249 |
| [`prompts.py`](backend/ai/prompts.py) | `SYSTEM_PROMPT`, `USER_PROMPT_TEMPLATE` | Strict JSON schema constraint with closed enum of `likely_reason` values. Model acts as explanatory assistant, never as arithmetic calculator. | 21 |
| [`feedback_memory.py`](backend/ai/feedback_memory.py) | `feedback_store.find_similar()`, `feedback_store.record_feedback()` | Weighted similarity matching (merchant type, amount magnitude, fee delta) against historical human review corrections for active learning. | 146 |

### 4. Pipeline & Services (`backend/services/`)

| Module | Key Functions | Purpose | Lines |
|---|---|---|---|
| [`pipeline.py`](backend/services/pipeline.py) | `process_reconciliation_batch()` | End-to-end orchestrator: Rule Matching → AI Verification → Exception Classification → 3-Way Gap Detection → Metrics Snapshot. Handles ground truth comparison for evaluation. | 385 |
| [`job_queue.py`](backend/services/job_queue.py) | `job_queue.submit_job()`, `job_queue.get_job()`, `job_queue.list_jobs()` | Thread-safe async background processing via `ThreadPoolExecutor(max_workers=4)` with DB persistence (`ReconciliationJob`) surviving restarts. State machine: `queued → processing → completed/failed`. | 185 |
| [`metrics.py`](backend/services/metrics.py) | `compute_batch_metrics()` | Calculates precision, recall, match rate, F1, manual hours saved, and AI accuracy from confusion matrix components. | 81 |

### 5. API Layer (`backend/api/`)

| Module | Key Functions | Purpose | Lines |
|---|---|---|---|
| [`routes.py`](backend/api/routes.py) | 16+ REST endpoints | Full CRUD: batch upload (10MB bounded streams), demo generation, match querying (batch `in_()`), exception listing, metrics retrieval, human review, CSV export, ERP journal export, async job submission, cash position | 735 |
| [`auth.py`](backend/api/auth.py) | `create_access_token()`, `decode_access_token()`, `verify_api_key()`, `get_current_tenant()` | HMAC-SHA256 JWT lifecycle. Zero external JWT library (pure stdlib). Supports Bearer token + X-Tenant-ID header + `org_default` fallback. | 137 |
| [`rate_limiter.py`](backend/api/rate_limiter.py) | `RateLimiterMiddleware` | Sliding window rate limiter: 120 requests/minute per client IP. | 39 |
| [`schemas.py`](backend/api/schemas.py) | `BatchUploadResponse`, `ReviewMatchRequest`, `PaginatedMatchesResponse`, etc. | Pydantic request/response schemas for all endpoints. | 84 |

### 6. Database (`backend/db/`)

| Module | Key Classes | Purpose | Lines |
|---|---|---|---|
| [`models.py`](backend/db/models.py) | `Batch`, `Record`, `Match`, `AIVerification`, `ExceptionRecord`, `MetricsSnapshot`, `FeedbackMemoryRecord`, `ReconciliationJob` | 8 ORM models with UUID PKs, `org_id` tenant isolation, `UniqueConstraint("batch_id", "transaction_id", "source_type")`, cascading relationships, 10+ indexes | 225 |
| [`session.py`](backend/db/session.py) | `init_db()`, `get_db()`, `SessionLocal` | PostgreSQL + SQLite dual support. `pool_pre_ping=True`. Request-scoped session dependency. | 51 |

### 7. Analytics & Reports

| Module | Key Functions | Purpose | Lines |
|---|---|---|---|
| [`cash_position.py`](backend/analytics/cash_position.py) | `compute_cash_position()` | Real-time treasury snapshot: bank balance, pending settlements, refund reserves, next-day projections, liquidity health index | 126 |
| [`reporter.py`](backend/reports/reporter.py) | `generate_reconciliation_csv()`, `generate_tally_xml()`, `generate_zoho_books_csv()`, `generate_netsuite_journal_json()` | 1-click ERP journal exports for Tally Prime (XML), Zoho Books (CSV), and NetSuite SuiteTalk (JSON) with proper Dr/Cr ledger mapping | 267 |

### 8. Frontend (`frontend/`)

| Component | File | Purpose |
|---|---|---|
| **Dashboard** | [`page.tsx`](frontend/app/page.tsx) (366 lines) | Single-page app: merchant selector, demo batch trigger, processing stepper, KPI grid, tabbed views |
| **UploadPanel** | [`UploadPanel.tsx`](frontend/components/UploadPanel.tsx) | 3-file drag-and-drop CSV upload with client-side validation |
| **MetricsCards** | [`MetricsCards.tsx`](frontend/components/MetricsCards.tsx) | Live KPI cards: match rate, precision, processing time, exceptions, hours saved |
| **AnalyticsCharts** | [`AnalyticsCharts.tsx`](frontend/components/AnalyticsCharts.tsx) | Recharts stacked bar charts and exception donut taxonomy |
| **CashPositionBanner** | [`CashPositionBanner.tsx`](frontend/components/CashPositionBanner.tsx) | Real-time treasury liquidity, in-flight float, and variance health |
| **MatchTable** | [`MatchTable.tsx`](frontend/components/MatchTable.tsx) | Paginated, filterable reconciliation ledger |
| **EvidenceDrawer** | [`EvidenceDrawer.tsx`](frontend/components/EvidenceDrawer.tsx) | Side-drawer: calculation trace, AI telemetry, linked raw records |
| **ExceptionGrid** | [`ExceptionGrid.tsx`](frontend/components/ExceptionGrid.tsx) | Grouped exception report by category |
| **ReviewModal** | [`ReviewModal.tsx`](frontend/components/ReviewModal.tsx) | Human review & resolution with reviewer notes |

---

## 🔍 Existing Flaws & Technical Debt

The following table reflects only the **active/unresolved** gaps and architectural backlog items currently remaining in the codebase:

| # | Flaw / Gap | Severity | Location | Impact & Planned Remediation |
|---|---|---|---|---|
| 1 | **No live deployed public URL** | Medium | Infrastructure | Dockerfile & Docker Compose are validated; cloud hosting on Railway/Render (backend) + Vercel (frontend) is pending final DNS binding. |
| 2 | **Partial settlement support** | Medium | Rule Engine / Pipeline | Multi-tranche settlements (1 invoice settled across multiple payouts) are deferred per PRD §6 and `AGENTS.md` non-negotiable MVP freeze. Scheduled for v2 roadmap. |
| 3 | **No encoding detection on CSV** | Low | `backend/parser/csv_parser.py` | `pd.read_csv()` defaults to UTF-8. Non-UTF-8 files (Latin-1 or Windows-1252) require adding `chardet` encoding detection. |
| 4 | **No headerless CSV support** | Low | `backend/schema_mapper/mapper.py` | Schema mapper requires explicit CSV header rows. Headerless CSV files are not heuristically parsed. |
| 5 | **Ambiguous multi-match candidate scoring** | Low | `backend/rules/rule_engine.py` | When multiple invoices share the identical amount and date with different order IDs, candidate ranking does not weight by customer/fuzzy tokens. |
| 6 | **No Swagger/ReDoc customization** | Low | `backend/main.py` | FastAPI's built-in Swagger/ReDoc operates with default metadata without custom `openapi_tags` grouping or interactive response schema examples. |

---

## ✅ Resolved Flaws & Security Hardening (v3.1 Audit)

All 15 previously identified Critical, High, and Medium vulnerabilities and technical debt items have been fully resolved, implemented, and verified in the test suite:

| Flaw ID | Area | Resolution Details | Verification File |
|---|---|---|---|
| **C1** | AI Ground-Truth Verification | Added dedicated `test_ai_live_benchmark.py` running in strict `disable_simulation_fallback=True` mode, verifying real Gemini/OpenAI API responses against ground truth with token and cost tracking. | [`test_ai_live_benchmark.py`](tests/test_ai_live_benchmark.py) |
| **C2** | CI/CD Automation | Implemented automated GitHub Actions workflow executing backend tests with coverage (`pytest-cov`), Next.js frontend production build, and dual Docker container validation. | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |
| **H1** | Upload Size Limit Enforcement | Added `_read_validated_file()` enforcing `file.size > MAX_FILE_SIZE_BYTES` pre-read checks and bounded streaming reads (`MAX_FILE_SIZE_BYTES + 1`), rejecting files >10MB with HTTP 413. | [`backend/api/routes.py`](backend/api/routes.py) |
| **H2** | CORS Origin Security | Replaced wildcard `["*"]` fallback with safe default `["http://localhost:3000"]`. | [`backend/main.py`](backend/main.py) |
| **H3** | Unique Record Constraint | Added `UniqueConstraint("batch_id", "transaction_id", "source_type")` and mapped database integrity errors to HTTP 409 Conflict. | [`backend/db/models.py`](backend/db/models.py) |
| **H4** | Match Detail Query Optimization | Eliminated N+1 query loops using single-query batch `in_()` map lookup for matched records. | [`backend/api/routes.py`](backend/api/routes.py) |
| **H5** | Settlement Window Differentiation | Differentiated Rule 4 to cover extended settlement window (T+3 to T+7) at 98% confidence, complementing Rule 3's immediate T+2 window. | [`backend/rules/rule_engine.py`](backend/rules/rule_engine.py) |
| **M1** | Data Directory Duplication | Consolidated all datasets into canonical `backend/synthetic_data/` and removed legacy duplicate folder. | `backend/synthetic_data/` |
| **M2** | Dead Code Removal | Deleted redundant wrapper `backend/ai/verifier.py` (86 lines) with zero API breakage. | [`backend/ai/engine.py`](backend/ai/engine.py) |
| **M3** | Structured Logging | Centralized structured logging via `backend/logging_config.py` with standard formatting, timestamps, and module tracing. | [`backend/logging_config.py`](backend/logging_config.py) |
| **M4** | CSRF Protection Rationale | Documented stateless Bearer/API-key auth architecture with zero ambient browser cookie state (OWASP compliant). | [`backend/main.py`](backend/main.py) |
| **M6** | Alembic Database Migrations | Scaffolded Alembic migration environment (`alembic.ini`, `backend/migrations/env.py`) with initial schema revision. | [`alembic.ini`](alembic.ini) |
| **M7** | Frontend API URL Configuration | Created `API_BASE_URL` reading `NEXT_PUBLIC_API_URL` with `.env.local` fallback across all client fetch calls. | [`frontend/lib/api.ts`](frontend/lib/api.ts) |
| **M8** | Persistent Job Queue | Added `ReconciliationJob` ORM table and DB persistence in `backend/services/job_queue.py`, allowing background jobs to survive restarts. | [`backend/services/job_queue.py`](backend/services/job_queue.py) |
| **M9** | Test Coverage Visibility | Integrated `pytest-cov` with missing-line reporting in terminal and XML/HTML artifact export, achieving **78% line coverage**. | [`pytest.ini`](pytest.ini) |

---

## 📁 Repository Structure

```
ReconPilot/
├── backend/                          # Python 3.11+ FastAPI Backend (8,000+ lines)
│   ├── ai/                           # Finance Verification Engine & Validator (1,043 lines)
│   │   ├── engine.py                 # AI Orchestrator + Cluster Micro-Batching (627 lines)
│   │   ├── llm_client.py             # Multi-provider LLM Gateway (249 lines)
│   │   ├── feedback_memory.py        # Historical Precedent Store (146 lines)
│   │   ├── validator.py              # Deterministic Arithmetic Validator (100 lines)
│   │   └── prompts.py                # Strict Prompt Templates (21 lines)
│   ├── api/                          # FastAPI REST Layer (979 lines)
│   │   ├── routes.py                 # 16+ Endpoints (10MB bounded streams, 409 conflict, batch in_())
│   │   ├── auth.py                   # JWT Auth & Tenant Scoping (137 lines)
│   │   ├── schemas.py                # Pydantic Schemas (84 lines)
│   │   └── rate_limiter.py           # Sliding Window Limiter (39 lines)
│   ├── rules/                        # Deterministic Rule Engine (857 lines)
│   │   ├── rule_engine.py            # 7-Rule Priority Pipeline with R4 T+7 differentiation (415 lines)
│   │   ├── exception_taxonomy.py     # 30+ Exception Categories (342 lines)
│   │   └── adjusted_amount.py        # Statutory Fee Validator (100 lines)
│   ├── services/                     # Pipeline & Job Queue (600 lines)
│   │   ├── pipeline.py               # Reconciliation Orchestrator with Structured Logging (385 lines)
│   │   ├── job_queue.py              # DB-Backed Async Background Workers (185 lines)
│   │   └── metrics.py                # Metrics Computation (81 lines)
│   ├── db/                           # Database Layer (275 lines)
│   │   ├── models.py                 # 8 ORM Models (incl. ReconciliationJob, UniqueConstraint)
│   │   └── session.py                # Engine & Sessions (51 lines)
│   ├── migrations/                   # Alembic Database Migrations
│   │   ├── versions/                 # Versioned Migration Scripts
│   │   └── env.py                    # Migration Context
│   ├── parser/                       # CSV Parsing (272 lines)
│   ├── normalizer/                   # Data Cleaning & Normalization (335 lines)
│   ├── schema_mapper/                # AI-Assisted Column Mapping (546 lines)
│   ├── config/                       # Fee Rules & Merchant Profiles (84 lines)
│   ├── analytics/                    # Cash Position Engine (126 lines)
│   ├── reports/                      # ERP Export Generator (267 lines)
│   ├── evaluation/                   # Benchmark Suite (1,008 lines)
│   ├── synthetic_data/               # Canonical Data Generator & Archetypes (1,971 lines)
│   ├── logging_config.py             # Centralized Structured Logging Configuration
│   └── main.py                       # FastAPI Entrypoint (Safe CORS, CSRF Note)
├── frontend/                         # Next.js 14 + Tailwind CSS + shadcn/ui
│   ├── app/                          # App Router (page.tsx, layout.tsx, globals.css)
│   ├── components/                   # 8 React Components
│   └── lib/                          # API Client Utilities (api.ts with NEXT_PUBLIC_API_URL)
├── tests/                            # 28 Test Suites (97 passed tests, 78% line coverage)
│   └── test_ai_live_benchmark.py     # Dedicated Live LLM Ground-Truth Benchmark
├── .github/workflows/ci.yml          # Automated CI/CD Pipeline (pytest-cov, Next.js, Docker)
├── alembic.ini                       # Alembic Migration Configuration
├── pytest.ini                        # Pytest configuration with --cov=backend
├── Dockerfile                        # Production Multi-Stage Container Image
├── docker-compose.yml                # Full-Stack Orchestration
├── requirements.txt                  # Python Dependencies (FastAPI, Alembic, pytest-cov, etc.)
└── README.md                         # This File
```

**Total Backend Python**: ~8,000+ lines across 45 files  
**Total Test Code**: 28 test suites, 97 passed tests (**78% line coverage**)  
**Total Frontend**: Next.js 14 App Router + 8 modular React components + configurable API client    

---

## 🚀 Quickstart & Installation

### Option A: 1-Command Docker Compose (Recommended)

```bash
git clone https://github.com/ParthK0/ReconPilot.git
cd ReconPilot
docker compose up --build
```
- **Web Dashboard**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **Swagger Docs**: `http://localhost:8000/docs`

### Option B: Local Native Setup

#### 1. Backend:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend:
```powershell
cd frontend
npm install
npm run dev
```

---

## ⚙️ Environment Configuration (`.env`)

```env
# AI Configuration
RECONPILOT_AI_MODE=live              # "live" or "offline"
GEMINI_API_KEY=AIzaSy...             # Google Gemini API key
AI_MODEL=gemini-2.5-pro             # Model to use
AI_SPEND_CEILING_USD=5.00           # Max AI spend per batch

# Authentication
DEMO_API_KEY=reconpilot-demo-secret-key-2026
JWT_SECRET=change-this-in-production

# Database (defaults to SQLite if omitted)
# DATABASE_URL=postgresql://reconpilot:password@localhost:5432/reconpilot_db

# App Settings
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

---

## 🧪 Testing & Evaluation

```powershell
# Run the 28-suite test battery (97 test cases, 78% line coverage)
pytest -v

# Run Standard benchmark
python -m backend.evaluation.score

# Run Adversarial benchmark
python -m backend.evaluation.score --adversarial

# Generate new synthetic datasets
python -m backend.synthetic_data.generator
```

---

## 🗺️ API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Root health check |
| `GET` | `/api/v1/health` | API health + DB connection |
| `GET` | `/api/v1/merchants` | List 11 merchant archetypes |
| `POST` | `/api/v1/batches` | Upload 3 CSVs for reconciliation |
| `POST` | `/api/v1/batches/demo` | Generate & process synthetic demo batch |
| `GET` | `/api/v1/batches/{id}` | Batch status & lifecycle |
| `GET` | `/api/v1/batches/{id}/matches` | Paginated match ledger |
| `GET` | `/api/v1/matches/{id}` | Match detail + evidence trace |
| `GET` | `/api/v1/batches/{id}/exceptions` | Categorized exception report |
| `GET` | `/api/v1/batches/{id}/metrics` | KPI snapshot |
| `GET` | `/api/v1/batches/{id}/cash-position` | Treasury analytics |
| `POST` | `/api/v1/matches/{id}/review` | Human review & resolution |
| `GET` | `/api/v1/batches/{id}/export` | Audit CSV download |
| `GET` | `/api/v1/batches/{id}/erp-journal` | 1-Click ERP export (Tally/Zoho/NetSuite) |
| `POST` | `/api/v1/auth/token` | JWT token generation |
| `POST` | `/api/v1/reconciliation/jobs` | Async job submission |
| `GET` | `/api/v1/reconciliation/jobs/{id}` | Job progress polling |

---

## 📜 License

ReconPilot is open-source software licensed under the **MIT License**.
