# RAZORPAY BUILDATHON 2026: FINAL EVALUATION COMMITTEE REPORT
**Track 04 — AI Finance Controller: "Run the books and the cash position"**  
**Submission:** ReconPilot  
**Evaluation Date:** August 26, 2026  
**Classification:** INTERNAL — FINAL PANEL DELIBERATION  
**Committee Composition:** CTO · Head of Engineering · Staff Engineer (Payments) · Principal AI/ML Engineer · Finance Ops Lead · Product Director · Engineering Manager · Senior Buildathon Judge

---

> **Committee Protocol:** Every claim in this document is supported by a specific file, line number, test result, or the explicit statement "Cannot verify from repository." Scores are calibrated against the realistic distribution of 300+ submissions, not against perfection.

---

## PART 1: PRODUCT RECONSTRUCTION

Before scoring anything, we reconstructed the product from source.

### What problem is being solved?
Indian merchants using Razorpay must reconcile three disjoint financial data sources every settlement cycle:
1. **Razorpay settlement reports** — net payouts after MDR fees, GST (18% on fees), and TDS (1% Section 194-O)
2. **Corporate bank statements** — actual ACH credits identified by UTR numbers
3. **Internal ERP invoice registers** — original amounts billed to customers

This 3-way cross-check is overwhelmingly manual, error-prone, and time-consuming. The claimed baseline is 3.0 minutes per record. Evidence: [`docs/01-PRD.md`](file:///e:/Razorpay/docs/01-PRD.md), [`backend/evaluation/score.py`](file:///e:/Razorpay/backend/evaluation/score.py) line 337.

### Who is the customer?
Finance controllers, operations analysts, CFOs at mid-market to enterprise merchants. Evidence: [`docs/01-PRD.md`](file:///e:/Razorpay/docs/01-PRD.md).

### What is the workflow?
```
Upload 3 CSVs (or trigger demo batch)
  → Schema validation (strict or AI-assisted column mapping)
  → Normalization (dates, currencies, references cleaned)
  → 5 ordered deterministic rules (86% of volume resolved at 100% confidence)
  → AI verification engine on residual misses (6% verified)
  → Deterministic arithmetic validator intercepts AI output
  → Exception classification into 5 buckets (8% routed to human review)
  → Dashboard with KPI metrics, evidence drawers, and CSV export
```
Evidence: [`backend/api/routes.py`](file:///e:/Razorpay/backend/api/routes.py) lines 79-342, [`backend/rules/rule_engine.py`](file:///e:/Razorpay/backend/rules/rule_engine.py), [`backend/ai/engine.py`](file:///e:/Razorpay/backend/ai/engine.py).

### Why is AI required?
Standard deterministic rules cover known statutory rate schedules (2% MDR, 18% GST, 1% TDS). AI is needed for **non-standard one-off adjustments** — e.g., a ₹30 flat fee override on a ₹12,000 invoice that doesn't match any rate formula. The AI hypothesizes which field explains the discrepancy; a Python validator independently verifies the arithmetic. Evidence: [`backend/ai/engine.py`](file:///e:/Razorpay/backend/ai/engine.py) lines 150-246 (simulation), [`backend/ai/validator.py`](file:///e:/Razorpay/backend/ai/validator.py) lines 41-93.

### What finance loop is closed?
Ingestion → Matching → Verification → Exception Classification → Human Resolution → Audit Export. The loop is fully closed end-to-end. Evidence: The `POST /api/v1/batches` endpoint accepts files, runs the pipeline, and the `GET /api/v1/batches/{id}/export` endpoint streams an audit CSV. The `POST /api/v1/matches/{id}/review` endpoint allows human resolution. Evidence: [`backend/api/routes.py`](file:///e:/Razorpay/backend/api/routes.py).

### How is this different from existing finance software?
Most reconciliation tools are either purely rule-based (failing on edge cases) or purely AI-based (hallucinating numbers). ReconPilot is a **hybrid**: deterministic rules handle the bulk, AI proposes hypotheses for residuals, and a deterministic validator rejects any AI claim that fails arithmetic verification to the paisa.

### What business value is created?
Saves ~4.6 manual hours per 100 records. Zero false positives. Sub-second processing. Auditor-ready calculation traces. Evidence: Evaluation output shows `Manual Hours Saved: 4.5999`, `Precision: 100.0000%`, `Processing Time: 0.3189 seconds`.

---

## PART 2: TRACK ALIGNMENT

We evaluated every clause of the Track 04 challenge against the codebase.

| Track 04 Requirement | Verdict | Evidence |
|---|---|---|
| "Throughput plus measured accuracy" | ✅ Fully satisfies | 100 records processed in 0.32s. Precision=100%, Recall=100%. Confusion matrix computed by [`backend/evaluation/score.py`](file:///e:/Razorpay/backend/evaluation/score.py). |
| "An honest exception list" | ✅ Fully satisfies | 8 genuine exceptions categorized into 5 distinct buckets (`settlement_delay`, `missing_credit`, `duplicate_invoice`, `refund_pending`, `unknown`). Not swept under the rug. Evidence: [`backend/api/routes.py`](file:///e:/Razorpay/backend/api/routes.py) lines 277-301. |
| "One cherry-picked match proves nothing" | ✅ Fully satisfies | Evaluation runs against the complete 100-record labeled dataset with ground truth comparison for every single record. Evidence: [`backend/evaluation/score.py`](file:///e:/Razorpay/backend/evaluation/score.py) lines 216-318. |
| "Rules before AI" | ✅ Fully satisfies | Rule engine resolves 86/100 records. AI only sees the 14 that rules couldn't handle. This is architecturally enforced, not advisory. Evidence: [`backend/api/routes.py`](file:///e:/Razorpay/backend/api/routes.py) lines 184-196, [`backend/rules/rule_engine.py`](file:///e:/Razorpay/backend/rules/rule_engine.py) lines 320-393. |
| "Never trust AI confidence directly" | ✅ Fully satisfies | [`backend/ai/validator.py`](file:///e:/Razorpay/backend/ai/validator.py) replaces model confidence with independently derived scores (99/88/65/40) based on arithmetic re-derivation. Line 31: `"A deterministic verdict; confidence never uses the model's score."` |
| "Evaluation is a product surface" | ✅ Fully satisfies | Dashboard renders live KPI cards. Evidence: [`frontend/app/page.tsx`](file:///e:/Razorpay/frontend/app/page.tsx). |
| "MVP is frozen — no chatbot, RAG, voice, multi-agent" | ✅ Fully satisfies | Zero LangChain, LlamaIndex, or vector DB dependencies. No conversational interface. Evidence: [`backend/requirements.txt`](file:///e:/Razorpay/backend/requirements.txt) contains only `fastapi`, `sqlalchemy`, `pandas`, `pydantic`, `httpx`, `python-dotenv`, `uvicorn`, `python-multipart`, `psycopg2-binary`. |
| "Every feature that touches money needs a test" | ✅ Fully satisfies | 57 automated tests covering rules, AI engine, validator, parsers, schema mapper, data cleaners, evaluation, live metrics, and multi-merchant profiles. All passing. Evidence: test suite output. |

---

## PART 3: PRODUCT EVALUATION

### Problem Selection: Strong
Reconciliation is a genuine, high-pain operational problem. Not a contrived hackathon toy. Finance teams at Razorpay merchants spend real hours on this every day.

### Market Need: Strong
Every Razorpay merchant doing >500 transactions/month faces this. The addressable market is large and the pain is immediate.

### Business Value: Strong
4.6 hours saved per 100 records. Zero false positives. This directly reduces opex for finance teams.

### Innovation: Strong
The "rules before AI" + "deterministic arithmetic validator" architecture is genuinely novel for a hackathon submission. Most teams would either build a pure rule engine or throw everything at an LLM.

### Differentiation: Strong
The three-tier architecture (deterministic rules → AI hypothesis → arithmetic validator) is a significant differentiator. The multi-merchant profile system with schema-agnostic ingestion adds another layer.

### Enterprise Readiness: Moderate
- ✅ PostgreSQL support with SQLite fallback
- ✅ CORS middleware with configurable origins
- ✅ Structured error handling with proper HTTP status codes
- 🟡 Authentication is absent — no OAuth2, no RBAC, no tenant isolation
- 🟡 No CI/CD pipeline in the repository
- 🟡 No Dockerfile or deployment configuration
- ❌ No rate limiting on API endpoints
- ❌ No request logging or observability (no structured logging, no tracing)

### Product Thinking: Strong
The team made deliberate scope decisions: explicitly freezing chatbots, RAG, voice interfaces. They built the core reconciliation loop to completion rather than spreading thin.

### User Experience: Strong
Dark-mode financial terminal aesthetic. Evidence drawer with calculation traces. Exception review modal with reviewer notes. KPI cards immediately visible.

### Would finance teams actually use this?
**Yes**, with caveats. The core matching engine is trustworthy. However, the lack of webhook-based ingestion (requiring manual CSV uploads) limits real-world adoption. Finance teams want automated, scheduled reconciliation — not file uploads.

### Would Razorpay internally benefit?
**Yes.** The rule engine logic and validator pattern could be adapted for internal settlement reconciliation.

### Would merchants pay for this?
**Maybe.** The CSV upload flow is a barrier. If it had automated Razorpay API/webhook ingestion, the answer would be a clear yes.

---

## PART 4: AI EVALUATION

### Could this be built using only rules?
**No — not entirely.** Rules handle the 86% of standard, predictable statutory deductions. But the 6 "hero cases" — non-standard one-off manual fee overrides — cannot be deterministically resolved without either (a) a human reviewing each one, or (b) an AI proposing which field explains the delta. Evidence: [`backend/synthetic_data/generator.py`](file:///e:/Razorpay/backend/synthetic_data/generator.py) generates 6 non-standard fee adjustment records that deliberately fail Rule 5.

### Does AI actually improve accuracy?
**Yes.** Without AI, 6 records would be false negatives (dropped as exceptions despite being reconcilable). With AI + validator, all 6 are correctly verified. Evidence: Evaluation output shows `AI Engine Matches: 6`, `Engine Decision Acc: 100.0000%`.

### Is AI used intelligently?
**Yes.** This is one of the most disciplined AI integrations we've reviewed:
1. The numeric delta is **pre-computed in Python** ([`backend/ai/engine.py`](file:///e:/Razorpay/backend/ai/engine.py) line 67) — the LLM is never asked to do arithmetic
2. Temperature is **0.0** ([`backend/ai/engine.py`](file:///e:/Razorpay/backend/ai/engine.py) line 111, 137)
3. Output is constrained to **strict JSON schema** with a **closed enum** of reasons ([`backend/ai/prompts.py`](file:///e:/Razorpay/backend/ai/prompts.py) line 13)
4. The model's self-reported confidence is **completely discarded** and replaced by the validator's independent score ([`backend/ai/validator.py`](file:///e:/Razorpay/backend/ai/validator.py))

### Is hallucination prevented?
**Yes, structurally.** Even if the LLM hallucinates a fee amount, the deterministic validator independently recalculates `invoice.amount - claimed_deduction == settlement.amount`. If the equation fails by more than ₹0.01, the match is rejected and routed to exceptions. Evidence: [`backend/ai/validator.py`](file:///e:/Razorpay/backend/ai/validator.py) lines 64-93.

### Are confidence scores trustworthy?
**Yes.** They are deterministically derived, not model-reported:
- **99%**: Exact paisa reconciliation after independent arithmetic check
- **88%**: Within ₹2.00 rounding tolerance
- **65%**: Non-equation qualitative claim (e.g., "settlement_delay") — forced to human review
- **40%**: Arithmetic contradiction — forced to exception

Evidence: [`backend/ai/validator.py`](file:///e:/Razorpay/backend/ai/validator.py) lines 77-93.

### Critical AI Weakness — the "simulation" escape hatch
**Important finding:** When no API key is configured, the AI engine falls back to `_simulate_llm_reasoning()` ([`backend/ai/engine.py`](file:///e:/Razorpay/backend/ai/engine.py) lines 150-245), which is a **hardcoded deterministic function** that pattern-matches settlement fields to produce the "correct" JSON output. This means:

1. The 100% AI accuracy in the benchmark is achieved **without actually calling any LLM**.
2. The simulation function essentially encodes the ground truth logic, making the evaluation somewhat circular for the AI-touched subset.
3. We **cannot verify** from the repository that a live LLM call would achieve the same 100% accuracy.

**This is the single most important caveat in the entire evaluation.** The simulation is well-designed for offline testing, but the team has not demonstrated that their system works with a live LLM endpoint.

---

## PART 5: RECONCILIATION QUALITY

| Capability | Supported? | Evidence |
|---|---|---|
| Match transactions by Order ID | ✅ Yes | Rule 1: [`rule_engine.py`](file:///e:/Razorpay/backend/rules/rule_engine.py) lines 61-109 |
| Match transactions by UTR/Reference | ✅ Yes | Rule 2: [`rule_engine.py`](file:///e:/Razorpay/backend/rules/rule_engine.py) lines 116-149 |
| Handle standard MDR fees | ✅ Yes | Rule 5: 2.0% MDR via configurable `FeeConfig` |
| Handle GST on fees | ✅ Yes | Rule 5: 18.0% GST on MDR fees |
| Handle TDS (Section 194-O) | ✅ Yes | Rule 5: 1.0% TDS on invoice amount |
| Handle non-standard fee overrides | ✅ Yes | AI engine + validator for custom amounts |
| Handle delayed settlements | ✅ Yes | `settlement_delay` exception category |
| Handle refunds | ✅ Yes | `refund_pending` exception category; detects negative bank amounts |
| Handle duplicates | ✅ Yes | `find_duplicate_order_ids()` blocks auto-matching |
| Handle missing bank credits | ✅ Yes | `missing_credit` exception category |
| Handle ambiguous/unresolvable records | ✅ Yes | `unknown` exception category |
| Handle partial settlements | 🟡 Partial | Refunds are detected, but true partial settlements (where only part of an invoice is settled) are not explicitly modeled |
| Multi-merchant fee schedules | ✅ Yes | 5 configurable profiles: retail, marketplace, subscription, restaurant, enterprise |
| Schema-agnostic column mapping | ✅ Yes | [`backend/schema_mapper/mapper.py`](file:///e:/Razorpay/backend/schema_mapper/mapper.py) with 178 column aliases |
| Dirty data cleaning (₹ symbols, date formats) | ✅ Yes | [`backend/normalizer/data_cleaners.py`](file:///e:/Razorpay/backend/normalizer/data_cleaners.py) handles ₹, INR, commas, parenthetical negatives, 20+ date formats |
| Produce evidence for every decision | ✅ Yes | Calculation trace attached to every AI verification |

---

## PART 6: DATASET REVIEW

### Structure
- **100 invoices, 100 settlements, 100 bank statements** with full ground truth (JSON + CSV)
- **10 distinct scenario categories**: 70 exact, 8 fee, 5 GST, 3 TDS, 6 AI custom, 2 delayed, 2 refund, 2 duplicate, 1 missing credit, 1 unknown
- Evidence: [`backend/synthetic_data/generator.py`](file:///e:/Razorpay/backend/synthetic_data/generator.py)

### Multi-Merchant Extension
- **5 merchant profiles × 100 records each = 500 total records** across retail, marketplace, subscription, restaurant, enterprise
- Each profile has different MDR rates, column names, date formats, and currency formatting
- Evidence: [`backend/synthetic-data/merchants/`](file:///e:/Razorpay/backend/synthetic-data/merchants) with 5 subdirectories, each containing full CSV datasets and ground truth

### Realism Assessment
**Moderate.** The data uses realistic-looking order IDs (ORD-2026-EX-0001), UTR formats, Indian-style bank descriptions ("ACH CR RAZORPAY"), and correct statutory rate calculations. However:
- All amounts are round numbers or simple percentages — no truly messy real-world data
- The "non-standard" AI cases are still deterministic (the fee field exactly explains the delta)
- No edge cases with timezone issues, encoding problems, or truncated records
- 100 records is a small dataset; a Razorpay engineer would want to see 10,000+

### Would larger datasets break the system?
**At 100-1,000 records:** No. Synchronous pipeline handles this easily.
**At 10,000-100,000 records:** **Yes**, the current architecture would break. The rule engine loads all records into memory, iterates settlements sequentially, and makes individual DB queries per match. No pagination, no batching, no async workers. Evidence: [`backend/api/routes.py`](file:///e:/Razorpay/backend/api/routes.py) lines 124-303 — entire pipeline is synchronous within a single HTTP request.

---

## PART 7: ENGINEERING REVIEW

### Architecture: 9/10
Clean separation of concerns across `parser/`, `normalizer/`, `rules/`, `ai/`, `evaluation/`, `api/`, `db/`, `config/`, `schema_mapper/`, `reports/`. The tiered "rules → AI → validator → exception" pipeline is well-architected. The new `config/fee_rules.py` + `merchant_profiles/` system enables configurable matching without code changes.

### Code Quality: 9/10
- Consistent use of Pydantic models for all data structures
- Type hints throughout
- `Decimal` for all monetary calculations (avoids floating-point errors)
- `round_paisa()` with `ROUND_HALF_UP` for statutory compliance
- Clean ABC pattern for parsers
- One smell: `verifier.py` is a redundant wrapper that duplicates `engine.py`'s functionality

### Database Design: 8.5/10
- Normalized schema with proper foreign keys and cascade deletes
- Indexes on hot-path columns (`order_id`, `reference_number`, `batch_id+source_type`, `batch_id+status`)
- `raw_payload` JSON column preserves original input for forensics
- **Weakness:** No unique constraint on `(batch_id, order_id, source_type)` — could theoretically allow duplicate record ingestion within the same batch

### API Design: 9/10
- RESTful `/api/v1` prefix
- Proper HTTP status codes (201 for creation, 404 for not found, 422 for validation errors)
- Server-side pagination with `page` and `page_size` query params
- CSV export with `Content-Disposition` header
- **Weakness:** No authentication on any endpoint. No rate limiting.

### Testing: 9.5/10
- **57 automated tests, all passing** in 7.68 seconds
- Coverage across: adjusted amounts (6), AI engine (7), API health (2), data cleaners (5), evaluation scoring (1), live metrics (2), multi-merchant (3), parser/normalizer (11), rules (7), schema mapper (4), synthetic data (5), validator (4)
- **Strength:** Tests verify actual negative cases (false positive rejection, non-standard fee fallthrough, malformed JSON fallback, provider timeout handling)
- **Strength:** The `test_live_metrics.py` tests are particularly good — they verify that the API correctly returns `null` for precision/recall when no ground truth is provided, and correctly reflects false positives when ground truth is provided
- **Weakness:** No integration test that calls the full `/api/v1/batches` upload endpoint with the 100-record synthetic dataset and verifies the metrics endpoint output
- **Weakness:** No test coverage measurement (no `--cov` in any CI config)

### Performance: 7.5/10
- 0.32 seconds for 100 records is excellent
- However, the pipeline is fully synchronous within a single HTTP request — at scale this would block the web server
- No connection pooling beyond SQLAlchemy's default
- N+1 query pattern in match detail retrieval (individual `db.query(Record).filter(Record.id == ...)` calls for each linked record)

### Security: 5/10
- ✅ SQL injection protected (all queries via SQLAlchemy ORM)
- ✅ AI hallucination structurally prevented by arithmetic validator
- ✅ Synthetic data only — no real PII in repo
- ❌ **No authentication whatsoever** — any HTTP client can read/write all data
- ❌ No CSRF protection
- ❌ No rate limiting
- ❌ No input size limits on CSV uploads (could OOM with a 2GB file)
- ❌ CORS allows wildcard origins as fallback ([`backend/main.py`](file:///e:/Razorpay/backend/main.py) line 33)

### Deployment: 3/10
- ❌ No Dockerfile
- ❌ No docker-compose.yml
- ❌ No CI/CD configuration (no GitHub Actions, no Vercel config)
- ❌ No Procfile or Railway/Render deployment config
- 🟡 `.env.example` exists but is minimal
- The SRS specifies "Vercel + Railway/Render" but **cannot verify any deployment artifacts from repository**

### Documentation: 9/10
- 8 detailed specification documents (`01-PRD.md` through `08-Roadmap.md`)
- Well-structured README with live benchmark output
- Inline docstrings on all major functions
- **Gap:** No API documentation auto-generation (no Swagger/ReDoc configuration despite FastAPI's built-in support)

### Scalability: 5/10
- The synchronous in-process pipeline works for demo scale (100-1,000 records)
- **No async worker queue** — entire reconciliation runs inside a single HTTP request handler
- **No horizontal scaling** — single-process, single-database
- At 100,000 records, the system would either timeout the HTTP request or exhaust memory

---

## PART 8: DEMO REVIEW

### Imagined 5-Minute Demo Flow
```
[0:00-0:30]  Problem statement: "Finance teams waste 4.6 hours per 100 records."
[0:30-1:00]  1-click demo batch: Hit POST /batches/demo, show processing stepper
[1:00-2:00]  Dashboard reveal: 92% match rate, 100% precision, 0.3s processing time
[2:00-3:00]  Hero case walkthrough: Click ORD-2026-AI-0087, show evidence drawer
             "₹12,000.00 − ₹30.00 (processing fee) = ₹11,970.00 = settlement amount ✓"
[3:00-4:00]  Exception report: 8 records honestly categorized, review & resolve modal
[4:00-5:00]  Multi-merchant: Show schema-agnostic mapping across 5 merchant profiles
```

### Would it be memorable?
**Yes.** The hero case evidence drawer with the paisa-level calculation trace is visually distinctive and technically impressive. Most teams won't have anything comparable.

### Would judges understand value in under 2 minutes?
**Yes.** The KPI cards are immediately legible. The pipeline stepper animation communicates the workflow clearly.

### Wow factor?
- **High:** The deterministic arithmetic validator concept — "AI proposes, Python disposes"
- **High:** The multi-merchant schema-agnostic mapping (178 column aliases + AI fallback)
- **Medium:** The 100% precision metric with confusion matrix
- **Low:** CSV upload UX is boring — no live API integration

### What parts are boring?
- The file upload interface is standard
- No live data flow visualization
- No real-time webhook or streaming reconciliation

### What parts are impressive?
- Evidence drawer with calculation trace
- Honest exception categorization
- Zero false positives verified against ground truth
- Multi-merchant profile system with configurable fee schedules

---

## PART 9: COMPETITIVE ANALYSIS

### What the strongest teams are likely building

| Competitor Archetype | Strengths Over ReconPilot | Weaknesses vs ReconPilot |
|---|---|---|
| **Live Razorpay API Integration** | Real-time webhook ingestion, live data | Likely no deterministic verification, hallucination risk |
| **Full-Stack RAG/Agent Platform** | More sophisticated AI, multi-turn reasoning | Overkill for reconciliation, unreliable arithmetic |
| **Banking API Integration** | Real bank statement pulling, Account Aggregator | More integration work, less reconciliation depth |
| **Beautiful Dashboard + Weak Backend** | Better visual demo, more polished UX | Likely no working reconciliation engine underneath |
| **Production SaaS with Auth + Deploy** | Better enterprise readiness, CI/CD | Likely less depth on matching accuracy |

### Head-to-Head Assessment

**Would a team beat ReconPilot with live Razorpay API integration?**
Only if their reconciliation logic is comparably rigorous. In our experience, teams that spend time on API integration typically build weaker matching engines. Advantage: ReconPilot.

**Would a team beat ReconPilot with better AI?**
Unlikely. Most "better AI" submissions use LLMs for open-ended reconciliation and suffer from hallucination, non-determinism, and inability to prove correctness. ReconPilot's constrained AI + validator is more trustworthy. Advantage: ReconPilot.

**Would a team beat ReconPilot with better deployment?**
This is ReconPilot's weakness. A team with Docker, CI/CD, and live deployment would score higher on production readiness. But deployment alone doesn't win — the core product must work.

**Would a team beat ReconPilot with better UX?**
Possible. If a team builds a polished, animated, real-time dashboard with drag-and-drop file upload and live progress streaming, they'd have a stronger visual impression. But without the underlying accuracy, it's style over substance.

---

## PART 10: SELECTION COMMITTEE DISCUSSION

### CTO
> "The architectural discipline here is impressive. The 'rules before AI' pattern with the deterministic validator is how we'd actually build this internally. My concern is the lack of deployment artifacts — no Dockerfile, no CI/CD. If I can't deploy it in 5 minutes, it's hard to call it production-ready. But for a hackathon, the engineering depth is exceptional. I'd advance this."

### Head of Engineering
> "57 passing tests in a hackathon submission. That alone puts this in the top 5%. The multi-merchant profile system with configurable fee schedules shows they're thinking beyond the demo. My concern is the synchronous pipeline — it won't scale beyond a few thousand records. But the architecture is clean enough that adding a task queue would be straightforward. Advance."

### Staff Engineer (Payments)
> "The rule engine is solid. `Decimal` arithmetic with `ROUND_HALF_UP` throughout — they understand paisa-level precision matters. The duplicate order ID detection is a nice touch. My concern is Rule 3 and Rule 4 are redundant — they both check `invoice.amount == settlement.amount` within the same date window. Rule 4 adds nothing that Rule 3 doesn't already cover. Minor issue, but it shows the rules weren't stress-tested against adversarial inputs. Still, advance."

### Principal AI Engineer
> "This is one of the most disciplined AI integrations I've reviewed in any hackathon. Pre-computed deltas, temperature=0.0, closed enum constraints, and complete discard of model confidence in favor of independent arithmetic validation. However, I need to flag the simulation fallback. The 100% AI accuracy in the benchmark is achieved by `_simulate_llm_reasoning()`, which is essentially a hardcoded oracle. We cannot verify that a live GPT-5.6 or Gemini call would achieve the same accuracy. If I were judging strictly, I'd want to see at least one recorded live API call. That said, the architecture is sound — if the LLM returns the right JSON shape, the validator will catch any arithmetic errors. Advance with reservation."

### Finance Operations Lead
> "The exception categories map directly to how my team actually works. Settlement delays, missing bank credits, duplicate invoices, refunds, and genuinely unknown discrepancies — that's the real world. The honest 92% match rate (not inflated to 100%) builds trust. The calculation trace in the evidence drawer is exactly what auditors ask for during quarterly reviews. My only concern: no support for partial settlements (e.g., a ₹10,000 invoice settled as two ₹5,000 payouts). That's a common real-world scenario. Advance."

### Product Director
> "The scope discipline is notable. They explicitly froze out chatbots, RAG, voice interfaces, and cash forecasting. That's product maturity — knowing what not to build. The KPI dashboard communicates value in seconds. The multi-merchant support with schema mapping shows they're thinking about onboarding friction. Missing: no user onboarding flow, no merchant settings page, no historical batch comparison. Advance."

### Engineering Manager
> "Clean repository structure. Good separation of concerns. Tests cover both positive and negative cases. The test_live_metrics.py tests are particularly good — they verify API behavior with and without ground truth, including a deliberately injected false positive scenario. Missing: no CI/CD, no deployment config, no coverage reporting. For a hackathon, acceptable. Advance."

---

## PART 11: 30 HARDEST JUDGE QUESTIONS

1. **"Your AI accuracy is 100%. How is that possible?"**
   *Honest answer:* The benchmark runs with the simulation fallback, which is a hardcoded deterministic function. We cannot verify 100% accuracy with a live LLM from the repository.

2. **"Why not just add the 6 AI cases as Rule 6?"**
   *Answer:* Because the fee amounts are non-standard — ₹30, ₹45, ₹50, etc. There's no formula. In production, new custom overrides would appear that no rule can predict.

3. **"Can this handle 100,000 transactions?"**
   *Honest answer:* Not in the current architecture. The synchronous pipeline would need an async task queue (Celery/Redis) and bulk DB operations.

4. **"Where is your Dockerfile?"**
   *Honest answer:* Not in the repository. Cannot verify deployment readiness.

5. **"Where is authentication?"**
   *Honest answer:* Not implemented. No OAuth2, no API keys, no RBAC.

6. **"What if someone uploads a 2GB CSV?"**
   *Honest answer:* No input size validation. The server would likely OOM.

7. **"Why is your match rate 92% and not 95%+ like the target?"**
   *Answer:* Because the dataset contains 8 genuine exceptions that should NOT be matched. 92/100 is the correct answer. Matching those 8 would be false positives.

8. **"How do you handle multi-currency?"**
   *Honest answer:* Not implemented. Only INR is supported.

9. **"How do you handle partial settlements?"**
   *Honest answer:* Not explicitly modeled. Each settlement maps to one invoice.

10. **"What is the latency of a live LLM call?"**
    *Answer:* `httpx.Client(timeout=15.0)` with one retry. Expected ~1-3 seconds per call. At 14 AI calls, ~15-45 seconds total.

11. **"How do you prevent prompt injection?"**
    *Answer:* The validator independently verifies all arithmetic claims. A prompt injection in a customer name field cannot bypass the Python `==` check.

12. **"Why do you have two synthetic data folders?"**
    *Answer:* Legacy artifact. `synthetic-data/` (hyphen) and `synthetic_data/` (underscore) both exist. Should be consolidated.

13. **"How are the 5 exception categories determined?"**
    *Answer:* Deterministic logic in [`routes.py`](file:///e:/Razorpay/backend/api/routes.py) lines 277-291 checks settlement status, invoice status, bank amount sign, and duplicate flags.

14. **"What happens when the AI engine returns invalid JSON?"**
    *Answer:* One automatic retry with an appended instruction. If retry also fails, the record is routed to `needs_review`. Evidence: [`engine.py`](file:///e:/Razorpay/backend/ai/engine.py) lines 285-296.

15. **"How is `verifier.py` different from `engine.py`?"**
    *Answer:* `verifier.py` is a legacy wrapper that duplicates functionality. It should be removed.

16. **"How does schema mapping work for unknown column names?"**
    *Answer:* Three-phase: exact match → 178 alias dictionary → LLM-based inference. Evidence: [`schema_mapper/mapper.py`](file:///e:/Razorpay/backend/schema_mapper/mapper.py) lines 122-240.

17. **"How many date formats does the system handle?"**
    *Answer:* 20+ formats including ISO, DD/MM/YYYY, DD-Mon-YYYY, MM/DD/YY, ISO datetime, and partial dates. Evidence: [`data_cleaners.py`](file:///e:/Razorpay/backend/normalizer/data_cleaners.py) lines 81-117.

18. **"What is the cost per 100 transactions?"**
    *Answer:* ~$0.015-$0.045 for 14 LLM calls at ~550 input / ~120 output tokens each. Rules are $0.

19. **"How do you handle idempotency if a batch is re-processed?"**
    *Answer:* `db.query(Match).filter(Match.batch_id == batch_id).delete()` at the start of processing. Evidence: [`routes.py`](file:///e:/Razorpay/backend/api/routes.py) lines 169-170.

20. **"Where is your logging?"**
    *Answer:* No structured logging framework. Only `print()` output from the evaluation script. This is a gap.

21. **"Where is your monitoring/alerting?"**
    *Answer:* Not implemented. No Prometheus metrics, no health check alerts.

22. **"Can the schema mapper handle CSV files with no headers?"**
    *Answer:* No. Headers are required. `pd.read_csv()` is called without `header=None`.

23. **"What if two different invoices have the same amount and date?"**
    *Answer:* Without matching order IDs or reference numbers, they could be ambiguously matched. The system doesn't implement candidate scoring for ambiguous multi-match scenarios.

24. **"Why did you choose SQLAlchemy ORM over raw SQL or Alembic?"**
    *Answer:* SQLAlchemy provides both the ORM and schema creation. Alembic migrations are not used — `init_db()` calls `Base.metadata.create_all()` directly.

25. **"What is your test coverage percentage?"**
    *Answer:* Cannot verify from repository. No `--cov` configuration.

26. **"How does the configurable fee system work?"**
    *Answer:* `FeeConfig` Pydantic model loaded from JSON files, dictionaries, or named profiles. Rule 5 uses `FeeConfig` rates instead of hardcoded constants. Evidence: [`config/fee_rules.py`](file:///e:/Razorpay/backend/config/fee_rules.py).

27. **"What is the cross-merchant evaluation result?"**
    *Answer:* 5 merchants × 100 records = 500 records. 100% precision, 100% recall across all profiles. Evidence: `test_multi_merchant.py::test_generate_and_evaluate_cross_merchant` passes.

28. **"How does the system handle Unicode in CSV files?"**
    *Answer:* `pd.read_csv()` defaults to UTF-8. No explicit encoding detection or fallback.

29. **"Is there any dead code?"**
    *Answer:* `backend/ai/verifier.py` is a redundant wrapper. The duplicate `synthetic-data` folder. The `adjusted_amount.py` module is imported but the `validate_adjusted_amount` function is only used indirectly through Rule 5.

30. **"Why should Razorpay care about this project?"**
    *Answer:* Because reconciliation is the #1 operational bottleneck for merchants, and this is the only submission we've seen that achieves 100% precision with mathematical proof, not probability.

---

## PART 12: WINNING ANALYSIS

| Placement Bracket | Probability | Justification |
|---|---|---|
| **Top 100** (of 300+) | **99%** | Engineering quality, test coverage, and track alignment are clearly in the top third. Almost no scenario where this doesn't advance. |
| **Top 50** | **95%** | The multi-layer architecture (rules + AI + validator) with 57 passing tests puts this well above median submissions. The multi-merchant profile system is an additional differentiator. |
| **Top 20** | **82%** | Depends on whether competitors have live integrations and deployment. ReconPilot's lack of Dockerfile, CI/CD, and authentication could cost it here. |
| **Top 10** | **65%** | At this level, polish matters. The AI simulation caveat and lack of production deployment would be scrutinized. If the team can demonstrate a live LLM call during the final demo, this goes up to 80%. |
| **Winner** | **25-35%** | Strong contender but not a lock. A team with equivalent engineering depth PLUS live Razorpay integration, deployed to a public URL, with authentication, could beat this. |

**Key uncertainty:** The winning probability depends heavily on the competition. If most Track 04 teams built chatbots and RAG wrappers (which is likely), ReconPilot's disciplined engineering would stand out dramatically. If even one team built an equally rigorous system with live integration, it becomes a close race.

---

## PART 13: REJECTION ANALYSIS

If this project were rejected, the committee feedback would read:

> **Rejection Feedback:**
>
> ReconPilot demonstrates strong engineering fundamentals and a well-architected reconciliation pipeline. However, the committee had the following concerns:
>
> 1. **The AI evaluation is not credible.** The 100% AI accuracy metric was achieved using a hardcoded simulation function, not a live LLM call. The team has not demonstrated that their system works with an actual AI model. The entire "AI Finance Controller" track requires genuine AI — running a deterministic simulation and calling it AI is insufficient.
>
> 2. **No deployment evidence.** Despite the SRS specifying "Vercel + Railway/Render," there is no Dockerfile, no CI/CD pipeline, no deployment configuration, and no live URL. We cannot verify that this system runs anywhere outside a developer's laptop.
>
> 3. **No authentication or security.** Every API endpoint is publicly accessible. For a finance tool handling reconciliation data, this is a fundamental gap, not a nice-to-have.
>
> 4. **The dataset is too small and too clean.** 100 records with deterministic edge cases is a controlled laboratory experiment. We'd need to see 10,000+ records with real-world messiness (encoding issues, truncated fields, timezone conflicts, multi-currency) to be convinced of robustness.
>
> 5. **Synchronous pipeline won't scale.** The entire reconciliation runs inside a single HTTP request. This is acceptable for a demo but unacceptable for production.

---

## PART 14: HIGH-IMPACT IMPROVEMENTS

| Priority | Improvement | Impact | Effort | Reason |
|---|---|---|---|---|
| **1** | **Record a live LLM API call and include the response in the repo** | Critical | 2 hours | Eliminates the biggest credibility concern. Even one successful live call proves the architecture works end-to-end. |
| **2** | **Add Dockerfile + docker-compose.yml** | High | 3 hours | Allows judges to run the system in one command. Shows deployment readiness. |
| **3** | **Add basic API key authentication** | High | 2 hours | Even a simple bearer token middleware removes the "no auth" criticism entirely. |
| **4** | **Add a 10,000-record stress test** | High | 4 hours | Generate 10K records, run evaluation, prove the pipeline handles scale. Profile and optimize if needed. |
| **5** | **Deploy to a live URL** | High | 3 hours | A running instance that judges can access is worth more than any documentation. |
| **6** | **Add CI/CD (GitHub Actions)** | Medium | 2 hours | Shows professional software engineering practices. |
| **7** | **Remove `verifier.py` and consolidate synthetic data folders** | Low | 1 hour | Clean code hygiene. |

---

## PART 15: FINAL VERDICT

### Scores

| Dimension | Score (/10) | Notes |
|---|---|---|
| **Track Alignment** | 9.5 | Exemplary alignment. Minor gap: match rate target not met (by design, due to genuine exceptions). |
| **Innovation** | 9.0 | The "rules → AI → arithmetic validator" architecture is genuinely novel for a hackathon. |
| **Engineering Quality** | 9.0 | 57 tests, clean architecture, proper Decimal handling. Missing CI/CD and deployment. |
| **Architecture** | 9.5 | Clean separation. Configurable multi-merchant profiles. Schema-agnostic mapping. |
| **AI Quality** | 7.5 | Excellent design, but the simulation fallback means we can't verify live LLM behavior. |
| **Business Value** | 8.5 | Genuine problem, clear ROI. Limited by CSV-only ingestion. |
| **Execution** | 9.0 | Comprehensive implementation across backend, frontend, tests, evaluation, and data generation. |
| **Demo Readiness** | 8.0 | The hero case walkthrough is strong. Missing: live deployment, real-time data flow. |
| **Security & Production** | 4.5 | No auth, no deployment, no logging, no rate limiting. |
| **Winning Potential** | 7.5 | Strong contender, not a guaranteed winner. Depends on competition. |

### Overall Score: **82 / 100**

This is a high score. In our calibration, the median hackathon submission scores around 40-50/100, and the typical "impressive-looking but shallow" project scores 60-70/100. ReconPilot's score reflects genuine engineering depth with specific gaps in production readiness and AI verification credibility.

---

### THE COMMITTEE'S ANSWER

**"If this were submitted today, would you personally advance it to the next round?"**

## **YES**

**Justification:**

ReconPilot is one of the strongest Track 04 submissions we expect to see in this Buildathon. The "rules before AI" architecture with a deterministic arithmetic validator is a genuinely sophisticated financial engineering pattern — not a thin LLM wrapper. 57 automated tests passing, a labeled ground-truth evaluation harness with confusion matrix, schema-agnostic multi-merchant support, and configurable fee schedules demonstrate execution depth that most hackathon teams never reach.

The gaps are real: no live LLM verification, no deployment, no authentication, and no CI/CD. These would prevent the project from winning outright against a polished competitor with equivalent technical depth. But they are **fixable gaps** in a fundamentally sound architecture, not fundamental design flaws.

We advance this project to the finalist round with the explicit expectation that the team addresses the live LLM verification gap and provides a deployed instance before the final pitch.

---

*Signed: Razorpay Buildathon 2026 Evaluation Committee*  
*This document represents the unanimous assessment of the reviewing panel.*
