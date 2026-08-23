# 02 — Software Requirements Specification
## ReconPilot

## 1. Functional Requirements

### Ingestion & Normalization
- **FR-1:** System accepts three CSV uploads per batch: settlement, bank statement, invoice.
- **FR-2:** System validates each CSV against an expected column schema before processing; malformed files are rejected with a specific error, not a silent partial parse.
- **FR-3:** System normalizes all three sources into one common record schema (transaction ID, order ID, amount, date, reference number, status, fees, GST, TDS, source_type).

### Rule Engine
- **FR-4:** System attempts to match records using, in order: exact Order ID, exact UTR/reference number, exact amount, settlement-date window, then fee/GST/TDS-adjusted amount.
- **FR-5:** Every rule match records *which* rule fired, at 100% confidence, with zero AI involvement.
- **FR-6:** Records the rule engine cannot resolve are passed to the Finance Verification Engine as candidate *pairs* (or a lone record with no candidate), never dropped.

### Finance Verification Engine (AI)
- **FR-7:** The Finance Verification Engine is invoked only on rule-engine misses — never on already-matched records. It handles only the ambiguous remainder; by design this is ~5–10% of a typical batch (see 01-PRD.md §4).
- **FR-8:** Every call returns a structured result: difference amount, likely reason, expected value under that reason, a confidence score, and a named evidence field.
- **FR-9:** The Engine's claimed numeric explanation is independently re-checked by a deterministic function before being accepted (see 06-AI-Design.md) — its self-reported confidence is never trusted blindly.
- **FR-10:** If the Engine is unavailable, times out, or returns an unparseable response, the record is routed to "needs review" — the batch must still complete.

### Exception Classification
- **FR-11:** Every unresolved record is classified into exactly one of: Settlement Delay, Missing Credit, Duplicate Invoice, Refund Pending, Unknown.
- **FR-12:** "Unknown" is a valid, expected output — the system must never force-fit a record into a category it doesn't support.

### Reporting
- **FR-13:** System produces a final reconciliation report: per-record status, confidence, evidence, and a reviewer action.
- **FR-14:** System computes and displays: records processed, rule matches, AI-verified matches, needs-review count, overall match rate, precision, processing time, estimated manual hours saved.
- **FR-15:** The report is exportable (CSV at minimum).
- **FR-16:** Match rate, precision, processing time, manual-review count, and manual hours saved are **visibly displayed on the dashboard UI**, not only computable via the API or logged internally — evaluation is a product surface, not documentation (see 01-PRD.md §8).

## 2. Non-Functional Requirements

| # | Requirement |
|---|---|
| NFR-1 | **Performance** — a 100-record batch completes in well under a minute; target ~15–30s. |
| NFR-2 | **Explainability** — no AI-touched record reaches "matched" without a visible evidence field and confidence score. |
| NFR-3 | **Auditability** — every AI call (prompt, response, latency, cost) is logged for later inspection. |
| NFR-4 | **Determinism** — the rule engine is idempotent: same input batch, same output, every run. |
| NFR-5 | **Graceful degradation** — an LLM outage degrades affected matches to "needs review," never a failed batch. |
| NFR-6 | **Cost safety** — a per-batch AI-spend ceiling exists; the system stops calling the LLM and flags the remainder as "needs review" rather than run away on cost. |
| NFR-7 | **Data safety** — only synthetic data is used; no real Razorpay/bank credentials or production PII touch the system. |
| NFR-8 | **Usability** — the dashboard's headline numbers are readable in under 5 seconds by someone who has never seen the tool before (a real constraint, since a panel will be skimming). |

## 3. Constraints

- Runway is short — the Buildathon's reported close is around September 5, 2026, roughly two weeks from project start (confirm exact date). Scope discipline (PRD §5) is a hard constraint, not a nice-to-have.
- Reliant on a third-party LLM API for the Finance Verification Engine — subject to that provider's rate limits, latency, and cost.
- Synthetic data only; no production reconciliation data is available or should be sought.
- Single or very small team, most implementation delegated to AI coding agents (Antigravity, Codex) with human review — see 08-Roadmap.md for the workflow this implies.

## 4. Assumptions

- UTR (bank reference number) and Order ID are reliable join keys when present in the data.
- Settlement delay has a bounded expected window (assume T+2 days unless the generated data says otherwise).
- Fees, GST, and TDS follow deterministic formulas that can be hand-coded into the rule engine rather than inferred.
- The synthetic dataset generator can produce labeled ground truth (which records *should* match, and under which exception category), which the evaluation plan depends on.
- A single LLM provider is enough for the Buildathon build; provider failover is a documented future step, not a requirement now.

## 5. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Next.js + Tailwind CSS + shadcn/ui | matches source brief |
| Backend | FastAPI | matches source brief |
| Database | PostgreSQL | matches source brief |
| Batch processing | Pandas | matches source brief |
| AI (Finance Verification Engine) | GPT-5.6 (Terra, with Sol as an escalation option) or Gemini 3.1 Pro / 2.5 Pro | see 06-AI-Design.md for the reasoning — the source brief named GPT-5 / Gemini 2.5 Pro, both now a generation behind |
| Deployment | Vercel (frontend), Railway or Render (backend) | matches source brief |

## 6. Acceptance Criteria

- **Given** a synthetic batch of 100 records with known ground truth, **when** the pipeline runs end-to-end, **then** overall match rate is ≥ 95%, precision on auto-matched records is ≥ 99%, and processing completes in under 30 seconds.
- **Given** an AI-verified match, **when** a reviewer opens it, **then** they see the exact rule/AI decision, the evidence field, the confidence score, and (for AI matches) the calculation trace.
- **Given** the LLM API is unreachable, **when** the batch runs, **then** it still completes, with affected records marked "needs review" rather than the batch failing.
- **Given** the exception report, **when** viewed, **then** every unresolved record has exactly one category and no record is silently dropped.
