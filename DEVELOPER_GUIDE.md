# ReconPilot — Internal Developer Documentation
## Every Function, Every Pipeline Stage, Every Flaw, Every Data Decision

> **This document is NOT an architecture overview or setup guide.**  
> It explains **what each file does line-by-line, how data flows through every stage, how we currently check data (and what's fake), and exactly what needs to change.**

---

## Table of Contents

1. [The Data Problem We Are Solving](#1-the-data-problem-we-are-solving)
2. [What Data We Currently Use (Synthetic) and What Real Data Would Look Like](#2-what-data-we-currently-use-and-what-real-data-would-look-like)
3. [Complete Pipeline: How Data Flows Through The System](#3-complete-pipeline-step-by-step)
4. [File-by-File: What Every File Does and Why It Exists](#4-file-by-file-breakdown)
5. [How We Check / Validate Data at Every Stage](#5-how-we-check-and-validate-data)
6. [Current Flaws — What's Broken, Fake, or Missing](#6-current-flaws)
7. [What Needs To Change When We Switch to Real Data](#7-what-needs-to-change-for-real-data)
8. [Test Coverage — What's Tested, What's Not](#8-test-coverage)

---

## 1. The Data Problem We Are Solving

A merchant sells ₹10,000 worth of goods. Razorpay collects ₹10,000 from the customer. But the merchant doesn't receive ₹10,000. They receive:

```
₹10,000 (gross sale)
  - ₹200   (2% MDR fee to Razorpay)
  - ₹36    (18% GST on the ₹200 fee)
  - ₹100   (1% TDS under Section 194-O)
= ₹9,664  (net settlement to merchant's bank)
```

The merchant's ERP says they're owed ₹10,000. Their bank says they got ₹9,664. Razorpay's settlement report explains the ₹336 gap with fees/gst/tds columns. **But nobody automatically cross-checks all three.**

That's what ReconPilot does. Three CSV files in → matched, verified, exceptions out.

### The Three Files

| File | Source | Key Columns | What It Represents |
|---|---|---|---|
| **Invoice CSV** | Merchant's ERP (Tally, Zoho, custom) | `invoice_id`, `order_id`, `amount`, `invoice_date`, `status` | "What we billed the customer" |
| **Settlement CSV** | Downloaded from Razorpay Dashboard | `settlement_id`, `order_id`, `amount`, `settlement_date`, `reference_number`, `status`, `fees`, `gst`, `tds` | "What Razorpay paid us after deductions" |
| **Bank Statement CSV** | Downloaded from HDFC/ICICI/SBI net banking | `bank_txn_id`, `txn_date`, `description`, `reference_number`, `amount`, `balance`, `status` | "What actually landed in our bank account" |

### The Matching Logic

The core question for every settlement row is:

> **"Can we find the matching invoice AND bank credit, and does the math check out?"**

- **Invoice ↔ Settlement**: linked by `order_id`. Amount difference should equal `fees + gst + tds`.
- **Settlement ↔ Bank**: linked by `reference_number` (UTR). Amounts should be equal.
- **Invoice ↔ Bank**: indirect — through settlement as the bridge.

---

## 2. What Data We Currently Use and What Real Data Would Look Like

### Current State: 100% Synthetic Data

We generate ALL our test data in [`backend/synthetic_data/generator.py`](file:///e:/Razorpay/backend/synthetic_data/generator.py) (1,259 lines). This is the single biggest "honesty problem" in the project.

**What the generator creates:**
- 100 invoices, 100 settlements, 100 bank statements
- Each with a matching `order_id` across invoice ↔ settlement
- Each with a matching `reference_number` across settlement ↔ bank
- Pre-computed fee/gst/tds based on configurable rates
- 10 scenario types with known ground truth labels

**The 10 scenario types:**
```
70 × exact_match       — Invoice amount == settlement amount (no deductions)
 8 × fee_deduction     — Standard 2% MDR fee applied
 5 × gst_deduction     — 2% MDR + 18% GST on MDR
 3 × tds_deduction     — 2% MDR + 18% GST + 1% TDS
 6 × ai_custom         — Non-standard one-off fees (₹30, ₹45, etc.)
 2 × settlement_delay  — Settlement status = "pending"
 2 × partial_refund    — Invoice status = "refunded", negative bank amounts
 2 × duplicate_invoice — Same order_id on two different invoices
 1 × missing_credit    — Settlement exists, bank credit missing
 1 × unknown           — Genuinely unexplainable discrepancy
```

### Why This Is A Problem

The synthetic data is **perfectly clean**:
- Every `order_id` is a well-formed string like `"ORD_00001"`
- Every amount is a round number or exact percentage
- Every date is within the expected T+2 window
- Every UTR matches exactly between settlement and bank
- There are **no encoding issues, no Unicode, no truncated columns, no timezone mismatches**

Real Razorpay data has:
- Order IDs with prefixes, suffixes, case differences (`order_KjN23x` vs `ORDER_KJN23X`)
- Amounts with paisa-level rounding differences
- Dates in 5+ different formats across the three sources
- UTR numbers with spaces, slashes, hyphens (`UTR/2026/08/12345` vs `UTR2026080012345`)
- Bank descriptions like `"RAZORPAY-UTR123456-NEFT"` that need to be parsed to extract the UTR
- Settlements spanning across midnight / weekend rollovers
- Partial settlements (one invoice settled in multiple tranches)
- Foreign currency transactions with FX conversion markup

### What Would Need To Change For Real Data

| Component | Current (Synthetic) | Real Data Requirement | Effort |
|---|---|---|---|
| **Order ID matching** | Exact string equality | Case-insensitive, strip prefixes, fuzzy match | Medium |
| **UTR extraction from bank** | Direct `reference_number` column | Regex extraction from `description` field | Medium |
| **Date parsing** | Generator outputs ISO dates | Already handles 20+ formats via `clean_date()` — mostly ready | Low |
| **Amount rounding** | Exact amounts from generator | Already handles ₹2.00 tolerance via Rule 6 — mostly ready | Low |
| **Encoding** | UTF-8 only | Need `chardet` detection for Latin-1/Windows-1252 | Low |
| **Partial settlements** | Not modeled | Need split-match tracking with remaining balance | High |
| **Weekend rollovers** | Not modeled | Need business-day calendar integration | Medium |
| **Multi-currency** | FX archetype exists but synthetic | Need live FX rate lookup or tolerance band | Medium |
| **CSV column names** | Use exact expected headers | Schema mapper with 178 aliases already handles most variants | Low |

---

## 3. Complete Pipeline: Step by Step

Here's exactly what happens when a user clicks "Generate & Reconcile Demo Batch" or uploads 3 CSVs:

### Stage 1: Ingestion (Entry Point)

**Entry:** [`backend/api/routes.py`](file:///e:/Razorpay/backend/api/routes.py) → `POST /api/v1/batches/demo` or `POST /api/v1/batches`

**What happens:**
1. For demo: calls [`generate_merchant_dataset()`](file:///e:/Razorpay/backend/synthetic_data/generator.py) to create 3 CSV strings + ground truth JSON
2. For upload: reads 3 `UploadFile` objects from the request

**Flaw:** `MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024` is declared at line 67 but **never checked** against actual file size. A 2GB CSV would be read into memory.

### Stage 2: Parsing

**File:** [`backend/parser/csv_parser.py`](file:///e:/Razorpay/backend/parser/csv_parser.py) (317 lines)

**What happens:**
1. `SmartCSVParser.parse()` is called for each of the 3 files
2. `_read_to_dataframe()` converts the input (path/string/bytes/stream) into a pandas DataFrame
3. `validate_schema()` checks that all required columns exist (e.g., invoice needs `invoice_id, order_id, amount, invoice_date, customer_name, status`)
4. If columns are missing, tries schema mapper (178 aliases + AI fallback)
5. `_sanitize_formulas()` strips CSV formula injection prefixes (`=`, `@`, `+`, `-` followed by letters)

**Data check:**
- If required columns are missing AND schema mapper can't resolve them → `SchemaValidationError`
- If CSV is empty → `EmptyFileError`
- If CSV is unparseable → `InvalidCSVFormatError`

**Flaw:** No encoding detection. `pd.read_csv()` defaults to UTF-8. A Latin-1 encoded file silently corrupts non-ASCII characters.

### Stage 3: Schema Mapping (if needed)

**File:** [`backend/schema_mapper/mapper.py`](file:///e:/Razorpay/backend/schema_mapper/mapper.py) (306 lines)

**What happens (only if strict schema fails):**
1. **Phase 1 — Exact match:** Lowercase column names and check against expected schema
2. **Phase 2 — Alias dictionary:** 178 known column name variants (e.g., `"txn_amount"` → `"amount"`, `"pmt_date"` → `"settlement_date"`) defined in [`aliases.py`](file:///e:/Razorpay/backend/schema_mapper/aliases.py) (240 lines)
3. **Phase 3 — AI inference:** If aliases fail, sends column names to LLM (Gemini/OpenAI) and asks "which target column does this map to?" Only accepts mappings with ≥0.95 confidence

**Data check:** Mappings below 0.95 confidence are flagged as `"suggested_mappings"` requiring user confirmation. The system does NOT auto-apply low-confidence mappings.

**Flaw:** No headerless CSV support. If the CSV has no header row, everything fails.

### Stage 4: Normalization & Cleaning

**Files:**
- [`backend/normalizer/normalizer.py`](file:///e:/Razorpay/backend/normalizer/normalizer.py) (168 lines)
- [`backend/normalizer/data_cleaners.py`](file:///e:/Razorpay/backend/normalizer/data_cleaners.py) (189 lines)

**What happens per row:**
1. `normalize_invoice_row()` / `normalize_settlement_row()` / `normalize_bank_row()` converts each CSV row into a `NormalizedRecord` Pydantic model
2. **Amount cleaning** via `clean_currency()`:
   - Strips `₹`, `$`, `€`, `£`, `INR`, `USD`, `EUR`, `GBP`, `Rs.`
   - Removes commas: `"12,000.00"` → `12000.00`
   - Handles accounting negatives: `"(50.00)"` or `"50.00-"` → `-50.00`
   - Returns `Decimal` (never `float`)
3. **Date cleaning** via `clean_date()`:
   - Tries 20+ format patterns (ISO, DD/MM/YYYY, DD-Mon-YYYY, MM/DD/YY, etc.)
   - Handles ISO datetime with `T`: `"2026-08-21T14:30:00"` → `2026-08-21`
   - Handles partial dates: `"21 Aug"` → `2026-08-21` (assumes current year)
4. **UTR/Reference cleaning** via `clean_reference()`:
   - Strips spaces, hyphens, slashes, dots
   - Uppercases: `"UTR/2026/08/12345"` → `"UTR20260812345"`
5. **Order ID cleaning** via `clean_order_id()`:
   - Trims whitespace, uppercases
6. **Status normalization** via `clean_status()`:
   - Maps `"success"/"captured"/"completed"` → `"paid"`
   - Maps `"reversed"` → `"refund_processed"`

**Data check:** If any amount can't be parsed → defaults to `Decimal("0.00")`. If any date can't be parsed → raises `ValueError`.

### Stage 5: Database Ingestion

**File:** [`backend/normalizer/normalizer.py`](file:///e:/Razorpay/backend/normalizer/normalizer.py) → `persist_normalized_records()`

**What happens:**
1. Creates a `Batch` row with status `"uploaded"`
2. Creates `Record` rows for each normalized record
3. Each record gets a UUID primary key, `org_id`, `batch_id`, and all normalized fields

**Flaw:** No unique constraint on `(batch_id, order_id, source_type)`. If you upload the same file twice in the same batch, you get duplicate records.

### Stage 6: Reconciliation Pipeline

**File:** [`backend/services/pipeline.py`](file:///e:/Razorpay/backend/services/pipeline.py) (343 lines) → `process_reconciliation_batch()`

**This is the heart of the system.** Here's what it does:

#### Step 6.1: Load Records
```python
records = db.query(Record).filter(Record.batch_id == batch_id).all()
invoices = [r for r in records if r.source_type == "invoice"]
settlements = [r for r in records if r.source_type == "settlement"]
banks = [r for r in records if r.source_type == "bank"]
```
Builds lookup dictionaries:
- `inv_by_order`: invoice keyed by `order_id`
- `bank_by_utr`: bank record keyed by `reference_number`

#### Step 6.2: Duplicate Detection
```python
duplicates = find_duplicate_order_ids(norm_invoices)
```
Scans all invoices. If two invoices share the same `order_id`, both are blocked from auto-matching and routed to exceptions.

#### Step 6.3: Settlement-Centric Matching Loop
The pipeline iterates **over settlements** (not invoices). For each settlement:

1. **Find candidate invoice:** `inv = inv_by_order.get(settle.order_id)`
2. **Find candidate bank credit:** `bank = bank_by_utr.get(settle.reference_number)`
3. **Run deterministic rules** via `apply_rules_in_order()`
4. If rules match → create `Match` row with `match_method="rule"`, `confidence=100%`
5. If rules miss → send to AI engine

#### Step 6.4: AI Verification (Only for Rule Misses)
```python
ai_res = verify_discrepancy(invoice=inv, settlement=settle, bank=bank, db=db, match_id=match_id)
```
- If AI validates (confidence ≥ 80%) → create `Match` with `match_method="ai"`
- If AI fails → create `Match` with `status="exception"`

#### Step 6.5: Exception Classification
For every exception, the pipeline assigns one of 10+ categories based on:
- `settlement_delay` — if status is "pending"
- `refund_pending` — if invoice is refunded or bank amount is negative
- `duplicate_invoice` — if order_id is in duplicates set
- `missing_credit` — if bank credit doesn't exist
- `chargeback` / `escrow_hold` / `fraud_hold` / `tds_revision` / `settlement_holiday` — from AI reason
- `cost_ceiling_exceeded` — if AI budget was exceeded
- `unknown_discrepancy` — catch-all

#### Step 6.6: 3-Way Gap Detection
After the main loop, scans for:
1. **Uncollected invoices:** Paid invoices with no corresponding settlement
2. **Unmatched bank credits:** Bank credits with no corresponding settlement

These create additional exception records.

#### Step 6.7: Metrics Snapshot
Computes and persists: `records_processed`, `rule_matches`, `ai_verified`, `needs_review`, `match_rate`, `precision`, `recall`, `true_positives`, `false_positives`, `false_negatives`, `ai_accuracy`, `processing_time_seconds`, `manual_hours_saved`.

### Stage 7: Frontend Display

**File:** [`frontend/app/page.tsx`](file:///e:/Razorpay/frontend/app/page.tsx) (366 lines)

After batch processing, the frontend calls 4 parallel API requests:
1. `GET /api/v1/batches/{id}` → metrics data
2. `GET /api/v1/batches/{id}/matches?limit=100` → match ledger
3. `GET /api/v1/batches/{id}/cash-position` → treasury analytics
4. `GET /api/v1/batches/{id}/exceptions` → exception report

These populate the KPI cards, match table, evidence drawers, and exception grid.

---

## 4. File-by-File Breakdown

### Backend Core (what each file actually does)

| File | Lines | What It Actually Does | Why It Exists |
|---|---|---|---|
| [`main.py`](file:///e:/Razorpay/backend/main.py) | 65 | FastAPI app, safe CORS (`http://localhost:3000`), rate limiter, structured logging, CSRF note | Entry point |
| [`logging_config.py`](file:///e:/Razorpay/backend/logging_config.py) | 35 | Centralized structured logging with uniform timestamps, levels, and module tracing | Observability |
| [`db/models.py`](file:///e:/Razorpay/backend/db/models.py) | 225 | Defines 8 ORM tables: `Batch`, `Record`, `Match`, `AIVerification`, `ExceptionRecord`, `MetricsSnapshot`, `FeedbackMemoryRecord`, `ReconciliationJob` (with `UniqueConstraint` on `Record`) | Database schema |
| [`db/session.py`](file:///e:/Razorpay/backend/db/session.py) | 51 | Creates SQLAlchemy engine (PostgreSQL or SQLite), session factory, `init_db()` | DB connection |
| [`migrations/`](file:///e:/Razorpay/backend/migrations) | — | Alembic migration framework (`alembic.ini`, `env.py`, versioned migration scripts) | Schema evolution |
| [`parser/csv_parser.py`](file:///e:/Razorpay/backend/parser/csv_parser.py) | 317 | `InvoiceParser`, `SettlementParser`, `BankStatementParser` + `SmartCSVParser` with schema mapping integration | Read & validate CSV files |
| [`normalizer/normalizer.py`](file:///e:/Razorpay/backend/normalizer/normalizer.py) | 175 | `NormalizedRecord` model + `normalize_invoice_row()`, `normalize_settlement_row()`, `normalize_bank_row()`, `normalize_dataframe()`, `persist_normalized_records()` with unique violation catches | Convert raw CSV into clean typed records |
| [`normalizer/data_cleaners.py`](file:///e:/Razorpay/backend/normalizer/data_cleaners.py) | 189 | `clean_currency()` (strips ₹, commas, handles negatives), `clean_date()` (20+ formats), `clean_reference()` (strips hyphens, uppercases), `clean_order_id()`, `clean_status()` (maps "success"→"paid") | Handle dirty real-world data formats |
| [`schema_mapper/mapper.py`](file:///e:/Razorpay/backend/schema_mapper/mapper.py) | 306 | 3-phase column mapping: exact → 178 aliases → AI with ≥0.95 gating | Handle non-standard CSV column names |
| [`schema_mapper/aliases.py`](file:///e:/Razorpay/backend/schema_mapper/aliases.py) | 240 | Dictionary of 178 known column name variants | Alias lookup |
| [`config/fee_rules.py`](file:///e:/Razorpay/backend/config/fee_rules.py) | 84 | `FeeConfig` Pydantic model (mdr, gst, tds, platform_fee, convenience_fee, settlement_delay_days) + `load_fee_config()` from JSON/dict/string/profile name | Make fee rates configurable per merchant |
| [`rules/rule_engine.py`](file:///e:/Razorpay/backend/rules/rule_engine.py) | 415 | 7 matching functions + `apply_rules_in_order()` orchestrator + `find_duplicate_order_ids()` (differentiated Rule 4 for extended T+7 window) | Deterministic matching — the core engine |
| [`rules/adjusted_amount.py`](file:///e:/Razorpay/backend/rules/adjusted_amount.py) | 100 | `validate_adjusted_amount()` — verifies that recorded fees/gst/tds match the expected rate card | Statutory compliance check |
| [`rules/exception_taxonomy.py`](file:///e:/Razorpay/backend/rules/exception_taxonomy.py) | 342 | 30+ `ExceptionDefinition` objects across 8 domains, each with category_id, description, suggested_action, financial_impact | Standardize exception types |
| [`ai/engine.py`](file:///e:/Razorpay/backend/ai/engine.py) | 627 | `FinanceVerificationOrchestrator` class: context assembly → feedback memory → LLM call → validator → audit persistence. Strict `disable_simulation_fallback` support + cluster micro-batching | AI verification for rule misses |
| [`ai/validator.py`](file:///e:/Razorpay/backend/ai/validator.py) | 100 | `validate_finance_verification()`: independently recalculates `invoice - fees - gst - tds == settlement`. Assigns confidence: 99% (exact) / 88% (rounding) / 65% (unconfirmable) / 40% (contradicted). **Never trusts model's self-reported score.** | Safety anchor — prevents AI hallucination from becoming a ledger entry |
| [`ai/llm_client.py`](file:///e:/Razorpay/backend/ai/llm_client.py) | 249 | `LLMClient`: multi-provider (Gemini + OpenAI), `temperature=0.0`, strict JSON schema, exponential backoff retry for HTTP 429, per-call cost tracking, `AI_SPEND_CEILING_USD` budget cap | LLM gateway with cost control |
| [`ai/prompts.py`](file:///e:/Razorpay/backend/ai/prompts.py) | 21 | `SYSTEM_PROMPT` + `USER_PROMPT_TEMPLATE` with closed enum of 7 `likely_reason` values | Constrain LLM output to valid JSON schema |
| [`ai/feedback_memory.py`](file:///e:/Razorpay/backend/ai/feedback_memory.py) | 146 | `FeedbackMemoryStore`: finds historical human corrections similar to current case by merchant type, amount magnitude, fee delta | Active learning from human reviews |
| [`services/pipeline.py`](file:///e:/Razorpay/backend/services/pipeline.py) | 385 | `process_reconciliation_batch()`: rule matching → AI → exceptions → gap detection → metrics, with structured logging | Pipeline coordination |
| [`services/job_queue.py`](file:///e:/Razorpay/backend/services/job_queue.py) | 185 | `JobQueueManager` with `ThreadPoolExecutor(4)` and DB persistence (`ReconciliationJob`) surviving server restarts | Handle large batches without blocking the API |
| [`services/metrics.py`](file:///e:/Razorpay/backend/services/metrics.py) | 81 | `compute_batch_metrics()`: calculates precision, recall, F1, match rate, hours saved from confusion matrix | Scoring |
| [`analytics/cash_position.py`](file:///e:/Razorpay/backend/analytics/cash_position.py) | 126 | `compute_cash_position()`: bank balance, pending settlements, refund reserves, next-day projections, liquidity health index | Treasury analytics |
| [`reports/reporter.py`](file:///e:/Razorpay/backend/reports/reporter.py) | 267 | `generate_reconciliation_csv()`, `generate_tally_xml()` (Tally Prime XML), `generate_zoho_books_csv()`, `generate_netsuite_journal_json()` | ERP journal exports |
| [`api/routes.py`](file:///e:/Razorpay/backend/api/routes.py) | 735 | 16+ REST endpoints with 10MB bounded upload streams (HTTP 413), duplicate conflict mapping (HTTP 409), and single-query batch map lookups | HTTP API layer |
| [`api/auth.py`](file:///e:/Razorpay/backend/api/auth.py) | 137 | HMAC-SHA256 JWT: `create_access_token()`, `decode_access_token()`, `verify_api_key()`, `get_current_tenant()` | Authentication & multi-tenant |
| [`api/rate_limiter.py`](file:///e:/Razorpay/backend/api/rate_limiter.py) | 39 | Sliding window rate limiter: 120 requests/minute per IP | Abuse prevention |
| [`api/schemas.py`](file:///e:/Razorpay/backend/api/schemas.py) | 84 | Pydantic request/response models for API endpoints | API contracts |
| [`synthetic_data/generator.py`](file:///e:/Razorpay/backend/synthetic_data/generator.py) | 1,259 | Generates 100-record datasets with 10 scenario types and ground truth labels | Test data |
| [`synthetic_data/merchant_archetypes.py`](file:///e:/Razorpay/backend/synthetic_data/merchant_archetypes.py) | 494 | 11 merchant profiles with industry-specific fee rates, order ID patterns, settlement windows | Multi-merchant support |
| [`evaluation/score.py`](file:///e:/Razorpay/backend/evaluation/score.py) | 483 | Automated benchmark runner: generates data → runs pipeline → computes confusion matrix | Evaluation harness |

---

## 5. How We Check and Validate Data

### Layer 1: Schema Validation (csv_parser.py)
**What:** Checks that CSV has all required columns  
**How:** String comparison of column names against `EXPECTED_COLUMNS` dict  
**When it fails:** `SchemaValidationError` with list of missing columns  

### Layer 2: Type Coercion (data_cleaners.py)
**What:** Converts raw strings to typed values  
**How:** `clean_currency()` returns `Decimal`, `clean_date()` returns `date`, etc.  
**When it fails:** Amount defaults to `0.00`, date raises `ValueError`  

### Layer 3: Duplicate Detection (rule_engine.py)
**What:** Finds order_ids appearing in multiple invoices  
**How:** `find_duplicate_order_ids()` — single pass through invoice list  
**What happens:** Duplicates are blocked from auto-matching and routed to exceptions  

### Layer 4: Deterministic Rule Matching (rule_engine.py)
**What:** 7 ordered rules that each try to match a settlement to an invoice/bank record  
**How each rule checks data:**

| Rule | What It Checks | Confidence |
|---|---|---|
| **R1: Exact Order ID** | `invoice.order_id == settlement.order_id` AND `invoice.amount == settlement.amount` AND both have correct status AND date within T+2 | 100% |
| **R2: Exact UTR** | `settlement.reference_number == bank.reference_number` AND `settlement.amount == bank.amount` AND both have correct status | 100% |
| **R3: Exact Amount** | `invoice.amount == settlement.amount` AND correct statuses AND immediate date within T+2 | 100% |
| **R4: Extended Date Window** | `invoice.amount == settlement.amount` across extended settlement corridor (T+3 to T+7 days) for delayed ACH credits | 98% |
| **R5: Fee Schedule** | Calculates `expected_fee = invoice.amount * 0.02`, `expected_gst = fee * 0.18`, `expected_tds = invoice.amount * 0.01`. Checks if settlement's recorded fees match these exact rates. Then checks `invoice.amount - fees - gst - tds == settlement.amount` | 100% |
| **R6: Tolerance** | `abs(invoice.amount - settlement.amount) ≤ ₹2.00` with matching order_ids | 95% |
| **R7: FX Spread** | `0.5% ≤ abs(delta / invoice.amount) ≤ 4.0%` with matching order_ids | 94% |

### Layer 5: AI Arithmetic Validator (validator.py)
**What:** After AI proposes a reason for the discrepancy, validator re-derives the math independently  
**How:**
```python
# For "processing_fee":
deduction = settlement.fees
independently_expected = invoice.amount - deduction
# Check: abs(independently_expected - settlement.amount) ≤ ₹0.01?
```

**Possible outcomes:**
| Outcome | Condition | Confidence | Action |
|---|---|---|---|
| `exact` | Math checks out to the paisa | 99% | Auto-match |
| `rounding` | Math within ₹2.00 | 88% | Auto-match |
| `unconfirmable` | Reason has no formula (e.g., "settlement_delay") | 65% | Human review |
| `contradicted` | Math fails | 40% | Exception |

### Layer 6: Ground Truth Comparison (pipeline.py + score.py)
**What:** If ground truth labels are provided (from synthetic generator), computes confusion matrix  
**How:** For each settlement, compares the pipeline's decision (rule/ai/exception) against `expected_resolution` label  

---

## 6. Current Flaws — Complete List

### 🔴 Critical (Must Fix)

| # | Flaw | Where | Impact | How To Fix |
|---|---|---|---|---|
| C1 | **AI benchmark live verification** | `engine.py` / `tests/test_ai_live_benchmark.py` | **RESOLVED**: Added dedicated `test_ai_live_benchmark.py` running in strict `disable_simulation_fallback=True` mode, asserting `is_simulated == False` with token/cost tracking and audit persistence to `tests/benchmark_results/live_llm_benchmark.json`. | Run `pytest tests/test_ai_live_benchmark.py -m live_llm -v -s` with valid `GEMINI_API_KEY` or `OPENAI_API_KEY` |
| C2 | **CI/CD Pipeline** | `.github/workflows/ci.yml` | **RESOLVED**: Automated GitHub Actions CI pipeline running backend tests with coverage (`pytest-cov`), Next.js frontend production build, and dual Docker container validation. | Runs automatically on push/PR to main/master |
| C3 | **No live deployment** | — | Can't show a running demo | Deploy backend to Railway/Render, frontend to Vercel |

### 🟡 High (Should Fix)

| # | Flaw | Where | Impact | How To Fix |
|---|---|---|---|---|
| H1 | **Upload size enforcement** | `routes.py` L67-90, L142, L167 | **RESOLVED**: Added `_read_validated_file()` checking `upload_file.size > MAX_FILE_SIZE_BYTES` before reading stream and using bounded chunk reads (`MAX_FILE_SIZE_BYTES + 1`) to eliminate OOM risks. | Enforces HTTP 413 on incoming streams |
| H2 | **CORS wildcard fallback** | `main.py` L37 | **RESOLVED**: Replaced wildcard `["*"]` fallback with safe default `["http://localhost:3000"]`. | Secure origin gating |
| H3 | **Unique constraint on records** | `models.py` L77, `normalizer.py` L176 | **RESOLVED**: Added `UniqueConstraint("batch_id", "transaction_id", "source_type")` and wrapped persistence to raise HTTP 409 on duplicates. | Prevents double-counting and duplicate ingestion |
| H4 | **N+1 queries in match detail** | `routes.py` L372, L416-420 | **RESOLVED**: Verified `get_batch_matches` and `get_match_detail` use single-query `in_()` lookups. | Optimal O(1) in-memory lookup |
| H5 | **Rule 3 and Rule 4 differentiation** | `rule_engine.py` L193-225, L472 | **RESOLVED**: Rule 4 now covers extended settlement window (T+3 to T+7) at calibrated 98% confidence, differentiating from Rule 3's immediate T+2 window. | Distinct matching corridor |

### 🟠 Medium (Good To Fix)

| # | Flaw | Where | Impact | How To Fix |
|---|---|---|---|---|
| M1 | **Two synthetic data folders** | `backend/synthetic_data/` | **RESOLVED**: Consolidated into `backend/synthetic_data/`, deleted legacy `backend/synthetic-data/`, and updated all code/test references. | Single canonical data source |
| M2 | **`verifier.py` is dead code** | `ai/verifier.py` | **RESOLVED**: Deleted dead file `backend/ai/verifier.py` (verified zero references). | Clean AI module surface |
| M3 | **Structured logging** | `backend/logging_config.py` | **RESOLVED**: Added centralized `logging_config.py` with standard formatting, log levels, and module tracing across core services. | Production traceability |
| M4 | **CSRF protection** | API layer / `main.py` | **RESOLVED (N/A)**: Documented architectural rationale: ReconPilot uses stateless Bearer/API-key headers; no ambient cookie state exists. | OWASP compliant |
| M5 | **Partial settlement** | Rule engine + pipeline | **DEFERRED (MVP FROZEN)**: Deferred per `01-PRD.md §6` and `AGENTS.md` non-negotiable MVP freeze. Planned for post-MVP. | Architectural roadmap |
| M6 | **Alembic migrations** | `backend/migrations/` | **RESOLVED**: Added `alembic.ini`, `backend/migrations/env.py`, template scripts, and registered `alembic>=1.13.0` in `requirements.txt`. | Schema evolution support |
| M7 | **Frontend hardcoded `localhost:8000`** | `frontend/lib/api.ts`, `page.tsx` | **RESOLVED**: Created `API_BASE_URL` resolver reading `NEXT_PUBLIC_API_URL` with `.env.local` fallback, replaced all hardcoded URLs. | Cloud/staging deployment ready |
| M8 | **In-memory job queue** | `backend/services/job_queue.py`, `models.py` | **RESOLVED**: Added `ReconciliationJob` table and added database persistence across job creation, execution, and queries. | Survives server restarts |
| M9 | **Test coverage measurement** | `pytest.ini`, `.github/workflows/ci.yml` | **RESOLVED**: Added `--cov=backend --cov-report=term-missing` to `pytest.ini` and XML artifact export in GitHub Actions CI. | Verified test coverage visibility |

### 🔵 Low (Nice To Have)

| # | Flaw | Where | Impact | How To Fix |
|---|---|---|---|---|
| L1 | No CSV encoding detection | `csv_parser.py` | Non-UTF-8 files silently corrupt | Add `chardet` |
| L2 | No headerless CSV support | `mapper.py` | Edge case | Add heuristic |
| L3 | No ambiguous multi-match scoring | `rule_engine.py` | Two invoices with same amount/date could be wrong-matched | Add candidate ranking |
| L4 | No OpenAPI/Swagger customization | `main.py` | Missing API docs polish | Add `openapi_tags` |

---

## 7. What Needs To Change For Real Data

### Problem 1: Real Razorpay CSVs have different column names

**Current expected columns:**
```python
"settlement": ["settlement_id", "order_id", "amount", "settlement_date", "reference_number", "status", "fees", "gst", "tds"]
```

**Real Razorpay settlement report columns:**
```
Payment ID, Order ID, Type, Method, Amount, Fee, Tax, Settlement Amount, Settlement Date, Settlement ID, UTR
```

**Fix:** The schema mapper with 178 aliases already handles most of these. But we need to add:
- `"Payment ID"` → `"settlement_id"` (or `"transaction_id"`)
- `"Fee"` → `"fees"`
- `"Tax"` → `"gst"`
- `"Settlement Amount"` → `"amount"` (this is the net amount)
- `"UTR"` → `"reference_number"`

**Important:** In real Razorpay data, `Amount` = gross amount and `Settlement Amount` = net amount. Our current schema treats `amount` as the net (settlement) amount. This mapping needs to be explicit.

### Problem 2: Real bank statements bury UTR in description

**Current:** Bank CSV has a clean `reference_number` column  
**Real:** Bank statement has a `description` field like:
```
"NEFT/RAZORPAY/UTR2026080012345/SETTLEMENT PAYOUT"
"RTGS-CMS-UTR2026080012345-RAZORPAY SOFTWARE"
"BY TRANSFER-INB-UTR 2026/08/0012345"
```

**Fix:** Add a regex extraction function:
```python
def extract_utr_from_description(description: str) -> Optional[str]:
    patterns = [
        r'UTR[\s/:-]?(\d{10,20})',
        r'UTR[\s/:-]?(\d{4}/\d{2}/\d+)',
        r'NEFT/[^/]+/([\w\d]+)',
    ]
    # ... try each pattern, clean_reference() the result
```

### Problem 3: Real amounts have paisa-level rounding differences

**Current:** Generator produces exact calculated amounts  
**Real:** Razorpay may round `₹200.004` to `₹200.00` while the merchant's ERP rounds to `₹200.01`

**Fix:** Rule 6 (tolerance ≤ ₹2.00) already handles this. But the tolerance should be tighter for fee reconciliation — maybe ≤ ₹0.05 for fee-level checks and ≤ ₹2.00 for gross-level checks.

### Problem 4: Settlements can span multiple days

**Current:** Generator creates settlements within T+2  
**Real:** Weekend settlements, banking holidays, NEFT cutoff times can push to T+5 or more

**Fix:**
1. Increase `max_days` in `FeeConfig.settlement_delay_days`
2. Add a business-day calendar that excludes Indian banking holidays
3. The `settlement_delay` exception category already handles this — just need better thresholds

### Problem 5: One invoice can have multiple settlements (partial payouts)

**Current:** 1:1 mapping between invoice and settlement  
**Real:** A ₹50,000 invoice might be settled in two tranches: ₹30,000 on Day 1 and ₹20,000 on Day 3

**Fix:** This requires the most significant architectural change:
1. Add a `remaining_balance` tracker per `order_id`
2. Allow multiple `Match` rows pointing to the same `invoice_record_id`
3. Only mark invoice as "fully reconciled" when remaining balance ≤ ₹0.01
4. This is a **high-effort** change

---

## 8. Test Coverage — What's Tested, What's Not

### What IS Tested (28 suites, 97 passed tests, 78% line coverage)

| Area | Test File | What It Verifies |
|---|---|---|
| Live LLM benchmark | `test_ai_live_benchmark.py` | Strict `disable_simulation_fallback=True`, token/cost accounting, real Gemini/OpenAI evaluation |
| 7-rule engine | `test_rules.py` (191 lines) | All 7 rules with positive/negative cases, Rule 4 T+7 window, duplicate detection |
| AI engine | `test_ai_engine.py` (197 lines) | Simulation output, context assembly, clustered batching |
| Arithmetic validator | `test_validator.py` (44 lines) | exact/rounding/unconfirmable/contradicted outcomes |
| CSV parsing | `test_parser_and_normalizer.py` (233 lines) | Schema validation, type coercion, error handling, unique constraints |
| Data cleaning | `test_data_cleaners.py` (58 lines) | Currency stripping, date parsing, status mapping |
| Schema mapping | `test_schema_mapper.py` (84 lines) | Alias resolution, AI fallback |
| Fee adjustment | `test_adjusted_amount.py` (52 lines) | Statutory rate card validation |
| FX matching | `test_fx_rules.py` (45 lines) | FX spread corridor |
| Tolerance | `test_tolerance_matching.py` (63 lines) | Penny rounding band |
| Gap detection | `test_gap_detection.py` (104 lines) | Uncollected invoices, unmatched bank credits |
| Feedback memory | `test_feedback_memory.py` (71 lines) | Similarity matching, precedent retrieval |
| Micro-batching | `test_micro_batching.py` (64 lines) | Cluster grouping, representative selection |
| ERP exports | `test_erp_export.py` (77 lines) | Tally XML, Zoho CSV, NetSuite JSON structure |
| Cash position | `test_cash_position.py` (78 lines) | Treasury snapshot calculations |
| Auth & tenancy | `test_auth_tenant.py` (53 lines) | JWT lifecycle, signature validation |
| Security | `test_security.py` (74 lines) | Upload size limits (HTTP 413), injection prevention |
| Scalability | `test_scalability_10k.py` (27 lines) | 10,000 record processing |
| Multi-merchant | `test_multi_merchant.py` (62 lines) | Cross-archetype evaluation across 11 profiles |
| LLM client | `test_llm_client.py` (129 lines) | Provider selection, retry, cost tracking |
| Job queue | `test_job_queue.py` (24 lines) | DB-backed async job submission and progress |
| API health & CORS | `test_api_health.py` (21 lines) | Health endpoint, safe CORS preflight |

### Remaining Testing Gaps (Future Roadmap)

| Gap | Impact | Why It Matters | Status |
|---|---|---|---|
| **No end-to-end integration test** | The full pipeline is tested unit-by-unit rather than a single 100-record API upload flow | A breaking change in any middle layer won't be caught | Open |
| **Live LLM test suite** | Live LLM benchmark exists in `test_ai_live_benchmark.py` | Validates live API accuracy against ground truth | **RESOLVED** |
| **No concurrent upload stress test** | Unknown behavior with 10 simultaneous uploads | Race conditions on batch creation possible | Open |
| **No encoding edge case tests** | Only UTF-8 tested | Latin-1/Windows-1252 files would fail silently | Open |
| **Coverage percentage measurement** | `--cov=backend` in `pytest.ini` with 78% line coverage | Measures exact % of lines tested | **RESOLVED** |

---

*This document should be updated whenever a new file is added, a flaw is fixed, or the data pipeline changes.*
