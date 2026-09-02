# ReconPilot — AI-Powered 3-Way Finance Reconciliation Engine

> **Razorpay AI Buildathon 2026 — Track 04: AI Finance Controller**  
> *"Throughput plus measured accuracy plus an honest exception list. One cherry-picked match proves nothing."*

[![Python](https://img.shields.io/badge/Python-3.11%2B%20%7C%203.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose%20Ready-2496ED?logo=docker)](docker-compose.yml)
[![Tests](https://img.shields.io/badge/Tests-26%20Suites%20%7C%2083%2B%20Cases-brightgreen?logo=pytest)](tests/)
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
| [`verifier.py`](backend/ai/verifier.py) | `verify_discrepancy_for_match()` | Legacy compatibility wrapper around `engine.py`. **Should be merged into engine.py.** | 78 |

### 4. Pipeline & Services (`backend/services/`)

| Module | Key Functions | Purpose | Lines |
|---|---|---|---|
| [`pipeline.py`](backend/services/pipeline.py) | `process_reconciliation_batch()` | End-to-end orchestrator: Rule Matching → AI Verification → Exception Classification → 3-Way Gap Detection → Metrics Snapshot. Handles ground truth comparison for evaluation. | 343 |
| [`job_queue.py`](backend/services/job_queue.py) | `job_queue.submit_job()`, `job_queue.get_job()`, `job_queue.list_jobs()` | Thread-safe async background processing via `ThreadPoolExecutor(max_workers=4)`. State machine: `queued → processing → completed/failed`. Independent DB sessions per worker. | 130 |
| [`metrics.py`](backend/services/metrics.py) | `compute_batch_metrics()` | Calculates precision, recall, match rate, F1, manual hours saved, and AI accuracy from confusion matrix components. | 81 |

### 5. API Layer (`backend/api/`)

| Module | Key Functions | Purpose | Lines |
|---|---|---|---|
| [`routes.py`](backend/api/routes.py) | 16+ REST endpoints | Full CRUD: batch upload, demo generation, match querying, exception listing, metrics retrieval, human review, CSV export, ERP journal export, async job submission, cash position | 719 |
| [`auth.py`](backend/api/auth.py) | `create_access_token()`, `decode_access_token()`, `verify_api_key()`, `get_current_tenant()` | HMAC-SHA256 JWT lifecycle. Zero external JWT library (pure stdlib). Supports Bearer token + X-Tenant-ID header + `org_default` fallback. | 137 |
| [`rate_limiter.py`](backend/api/rate_limiter.py) | `RateLimiterMiddleware` | Sliding window rate limiter: 120 requests/minute per client IP. | 39 |
| [`schemas.py`](backend/api/schemas.py) | `BatchUploadResponse`, `ReviewMatchRequest`, `PaginatedMatchesResponse`, etc. | Pydantic request/response schemas for all endpoints. | 84 |

### 6. Database (`backend/db/`)

| Module | Key Classes | Purpose | Lines |
|---|---|---|---|
| [`models.py`](backend/db/models.py) | `Batch`, `Record`, `Match`, `AIVerification`, `ExceptionRecord`, `MetricsSnapshot`, `FeedbackMemoryRecord` | 7 ORM models with UUID PKs, `org_id` tenant isolation, `currency`/`fx_rate` multi-currency, cascading relationships, 10+ indexes | 166 |
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

## 🔍 Known Flaws & Current Gaps

### Critical

| # | Flaw | Impact | Where | Suggested Fix |
|---|---|---|---|---|
| 1 | **AI benchmark uses simulation fallback** | The `100% AI accuracy` in benchmarks comes from `_simulate_llm_reasoning()` — a hardcoded deterministic function — not live LLM calls. Cannot verify live accuracy from the repo. | [`engine.py`](backend/ai/engine.py) L150-245 | Record ≥1 live LLM API call with the validator chain end-to-end |
| 2 | **No CI/CD pipeline** | No automated test execution on push/PR. No deployment automation. | Repo root | Add `.github/workflows/ci.yml` with pytest + coverage |
| 3 | **No live deployed URL** | Judges cannot interact with a running instance. Docker support exists but no public deployment. | — | Deploy to Railway/Render + Vercel |

### High

| # | Flaw | Impact | Where | Suggested Fix |
|---|---|---|---|---|
| 4 | **No CSV upload size limit enforcement** | `MAX_FILE_SIZE_BYTES` constant (10MB) is declared in [`routes.py`](backend/api/routes.py) L67 but never enforced on incoming file streams. A 2GB file could OOM the server. | `routes.py` | Add `if file.size > MAX_FILE_SIZE_BYTES: raise HTTPException(413)` |
| 5 | **CORS wildcard fallback** | `allow_origins=["*"]` when env var is empty. Allows any origin to call the API. | [`main.py`](backend/main.py) L37 | Default to `["http://localhost:3000"]` instead of `["*"]` |
| 6 | **No unique constraint on `(batch_id, order_id, source_type)`** | Could allow duplicate record ingestion within same batch. | [`models.py`](backend/db/models.py) | Add `UniqueConstraint("batch_id", "order_id", "source_type")` |
| 7 | **N+1 query in match detail retrieval** | Individual `db.query(Record).filter(Record.id == ...)` calls for each linked record in the detail endpoint. | `routes.py` | Use `joinedload()` or batch query |
| 8 | **No test coverage measurement** | No `--cov` flag in any config. Cannot verify actual line coverage. | `pytest.ini` | Add `--cov=backend --cov-report=html` |

### Medium

| # | Flaw | Impact | Where | Suggested Fix |
|---|---|---|---|---|
| 9 | **Dual synthetic data folders** | `backend/synthetic_data/` (underscore) and `backend/synthetic-data/` (hyphen) both exist with overlapping CSV files. | Backend root | Consolidate into `synthetic_data/` |
| 10 | **`verifier.py` is a redundant wrapper** | Duplicates `engine.py` functionality. Dead code smell. | [`verifier.py`](backend/ai/verifier.py) | Merge into `engine.py` and delete |
| 11 | **No structured logging** | Only `print()` output. No log levels, no request tracing, no correlation IDs. | All backend modules | Add `structlog` or `logging` with JSON formatting |
| 12 | **No CSRF protection** | Frontend makes plain fetch requests without CSRF tokens. | API layer | Add CSRF middleware or use SameSite cookies |
| 13 | **No partial settlement support** | True partial settlements (one invoice settled in multiple tranches with different amounts) are not explicitly modeled. | Rule engine | Add split-match tracking with remaining balance per `order_id` |
| 14 | **No Alembic migrations** | Schema is created via `Base.metadata.create_all()`. No migration history for schema evolution. | `session.py` | Add Alembic with auto-generate |
| 15 | **Frontend hardcodes `localhost:8000`** | API URL is hardcoded in [`page.tsx`](frontend/app/page.tsx). Breaks in any non-local deployment. | Frontend | Use `NEXT_PUBLIC_API_URL` env var |
| 16 | **No Swagger/ReDoc customization** | Despite FastAPI's built-in docs, no custom OpenAPI schema metadata is configured. | `main.py` | Add `openapi_tags` and response examples |

### Low

| # | Flaw | Impact | Where | Suggested Fix |
|---|---|---|---|---|
| 17 | **No encoding detection on CSV** | `pd.read_csv()` defaults to UTF-8. No fallback for Latin-1 or Windows-1252 encoded files. | `csv_parser.py` | Add `chardet` detection |
| 18 | **No headerless CSV support** | Schema mapper requires CSV headers. | `mapper.py` | Add `header=None` heuristic |
| 19 | **Ambiguous multi-match not scored** | Two invoices with same amount/date but different order IDs could be ambiguously matched. No candidate scoring. | `rule_engine.py` | Add weighted candidate ranking |
| 20 | **Job queue is in-memory only** | `JobQueueManager` stores jobs in a Python dict. Server restart loses all job state. | `job_queue.py` | Add Redis or DB persistence |

---

## 📁 Repository Structure

```
ReconPilot/
├── backend/                          # Python 3.11+ FastAPI Backend (7,993 lines)
│   ├── ai/                           # Finance Verification Engine & Validator (1,121 lines)
│   │   ├── engine.py                 # AI Orchestrator + Cluster Micro-Batching (627 lines)
│   │   ├── llm_client.py             # Multi-provider LLM Gateway (249 lines)
│   │   ├── feedback_memory.py        # Historical Precedent Store (146 lines)
│   │   ├── validator.py              # Deterministic Arithmetic Validator (100 lines)
│   │   ├── verifier.py               # Legacy wrapper [TO BE MERGED] (78 lines)
│   │   └── prompts.py                # Strict Prompt Templates (21 lines)
│   ├── api/                          # FastAPI REST Layer (979 lines)
│   │   ├── routes.py                 # 16+ Endpoints (719 lines)
│   │   ├── auth.py                   # JWT Auth & Tenant Scoping (137 lines)
│   │   ├── schemas.py                # Pydantic Schemas (84 lines)
│   │   └── rate_limiter.py           # Sliding Window Limiter (39 lines)
│   ├── rules/                        # Deterministic Rule Engine (857 lines)
│   │   ├── rule_engine.py            # 7-Rule Priority Pipeline (415 lines)
│   │   ├── exception_taxonomy.py     # 30+ Exception Categories (342 lines)
│   │   └── adjusted_amount.py        # Statutory Fee Validator (100 lines)
│   ├── services/                     # Pipeline & Job Queue (554 lines)
│   │   ├── pipeline.py               # Reconciliation Orchestrator (343 lines)
│   │   ├── job_queue.py              # Async Background Workers (130 lines)
│   │   └── metrics.py                # Metrics Computation (81 lines)
│   ├── db/                           # Database Layer (217 lines)
│   │   ├── models.py                 # 7 ORM Models (166 lines)
│   │   └── session.py                # Engine & Sessions (51 lines)
│   ├── parser/                       # CSV Parsing (272 lines)
│   ├── normalizer/                   # Data Cleaning & Normalization (335 lines)
│   ├── schema_mapper/                # AI-Assisted Column Mapping (546 lines)
│   ├── config/                       # Fee Rules & Merchant Profiles (84 lines)
│   ├── analytics/                    # Cash Position Engine (126 lines)
│   ├── reports/                      # ERP Export Generator (267 lines)
│   ├── evaluation/                   # Benchmark Suite (1,008 lines)
│   └── synthetic_data/               # Data Generator & Archetypes (1,971 lines)
├── frontend/                         # Next.js 14 + Tailwind CSS + shadcn/ui
│   ├── app/                          # App Router (page.tsx, layout.tsx, globals.css)
│   └── components/                   # 8 React Components
├── tests/                            # 26 Test Suites (2,110 lines)
├── docs/                             # 7 Specification Documents
├── Dockerfile                        # Production Container Image
├── docker-compose.yml                # Full-Stack Orchestration
├── requirements.txt                  # Python Dependencies (14 packages)
└── README.md                         # This File
```

**Total Backend Python**: ~7,993 lines across 45 files  
**Total Test Code**: ~2,110 lines across 26 test suites  
**Total Frontend**: ~366 lines (page.tsx) + 8 component files  

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
# Run the 26-suite test battery (83+ test cases)
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
