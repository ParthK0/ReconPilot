# Settlement Aggregation (N:1 Matching) — Feature Specification

> **Status:** Draft — awaiting stakeholder review before Stage 2 (Architecture)  
> **Author:** ReconPilot Architecture  
> **Created:** 2026-08-30  
> **References:** [`01-PRD.md`](file:///E:/Razorpay/docs/01-PRD.md), [`04-Database-Design.md`](file:///E:/Razorpay/docs/04-Database-Design.md), [`rule_engine.py`](file:///E:/Razorpay/backend/rules/rule_engine.py), [`pipeline.py`](file:///E:/Razorpay/backend/services/pipeline.py)

---

## 1. Problem Statement

### 1.1 The N:1 Relationship

Razorpay (and every production payment gateway — Stripe, PayU, Cashfree, etc.) does
**not** remit funds order-by-order. It **batches** hundreds or thousands of individual
order-level settlements into a single net lump-sum bank credit per payout cycle. That
single bank credit carries one UTR (Unique Transaction Reference) and one
`payout_id`/settlement batch reference from the gateway.

Concretely:

```
┌────────────────────────────────────────┐      ┌─────────────────────────────┐
│ Razorpay Settlement Report             │      │ Bank Statement              │
│ ─────────────────────────              │      │ ──────────────              │
│ ORD-001  ₹ 4,500.00  SET-001  PAY-77  │      │                             │
│ ORD-002  ₹ 2,200.00  SET-002  PAY-77  │      │ UTR-99887766   ₹1,17,450.00 │
│ ORD-003  ₹15,750.00  SET-003  PAY-77  │  ──▶ │ "ACH CR RAZORPAY"           │
│ ...      ...         ...      PAY-77  │      │ Status: Credited            │
│ ORD-500  ₹   950.00  SET-500  PAY-77  │      │                             │
│                                        │      │                             │
│ Gross: ₹1,20,000.00                   │      │                             │
│ MDR:   −₹2,400.00   GST: −₹432.00     │      │                             │
│ TDS:   −₹1,200.00   Holdback: −₹518   │      │                             │
│ ────────────────                       │      │                             │
│ Net Payout: ₹1,17,450.00   UTR-998877 │      │                             │
└────────────────────────────────────────┘      └─────────────────────────────┘
```

The **relationship is N settlement rows : 1 bank credit row**, linked by a shared
`payout_id` (or shared UTR when payout_id is absent in the source data).

### 1.2 Why the Current 1:1 Assumption Breaks

The current pipeline ([`pipeline.py`](file:///E:/Razorpay/backend/services/pipeline.py)
L128–L167) iterates settlement records one at a time and looks up a bank row by
`settlement.reference_number == bank.reference_number`. This works when each settlement
row has a **unique UTR that corresponds 1:1 to a bank credit**. In the real N:1 case:

| Scenario | What happens today | Correct behavior |
|---|---|---|
| 500 settlements share UTR `UTR-99887766` | The `bank_by_utr` dict maps that UTR to a single bank row. The **first** settlement to match "wins" the bank row. All subsequent settlements either (a) silently match against a bank row already consumed by another match, or (b) fail to match and become false exceptions. | All 500 settlements should be grouped, their net sum computed, and the group matched against the single bank credit. |
| 500 settlements share `payout_id` PAY-77, but each has a **different** per-order UTR (or no UTR at all) | No bank match found for any individual settlement UTR, since the bank only has the payout-level UTR. 100% exception rate. | Group by `payout_id`, sum, match against bank credit by payout-level UTR. |
| No explicit `payout_id` in settlement CSV (some gateway exports omit it) | No grouping signal at all. Every settlement is tried individually. | Heuristic grouping by date + running-sum matching against unmatched bank credits (with human confirmation). |

This is the **single highest-severity correctness gap** in the project: the "3-way
reconciliation" claim is invalid for any merchant doing meaningful Razorpay volume,
because 100% of their bank credits will be aggregated payouts that the current engine
cannot match.

### 1.3 Invoice Leg

The invoice leg is **not** affected by aggregation. ERP invoices are always per-order
(ORD-001 → INV-001). The existing 1:1 invoice↔settlement matching (Rules 1–7) remains
valid for the invoice↔settlement leg. Aggregation only affects the
**settlement↔bank** leg.

This is an important simplification: we do not need to aggregate invoices. We need to:
1. Match invoices to individual settlement rows (existing rules, unchanged).
2. Group matched/unmatched settlement rows into payout batches.
3. Match each payout batch's net sum against a bank credit.

---

## 2. Scope Boundaries

### 2.1 In Scope (WILL Handle)

| Edge Case | Decision | Rationale |
|---|---|---|
| **Standard N:1** — many settlements → one bank credit via shared `payout_id` or shared UTR | ✅ Primary use case. Deterministic grouping when explicit key exists. | This is the normal Razorpay flow and the core deliverable. |
| **Partial/incomplete aggregation** — some settlement rows in a batch match their invoices, others don't | ✅ The payout batch is formed regardless of whether individual settlements matched their invoices. The payout-to-bank match is independent of the invoice match status. Unmatched individual settlements within the batch are still flagged as invoice-level exceptions. | A payout batch always contains all its constituent settlements. Invoice matching is a separate concern. |
| **Aggregate delta that doesn't balance** — sum of settlement net amounts ≠ bank credit, even after summing all rows in the batch | ✅ If delta ≤ ₹2.00 (penny tolerance), auto-match with reduced confidence. If delta > ₹2.00, route as a new exception type `payout_aggregate_mismatch` for human review. Do **not** route to the AI verification engine — this is an arithmetic mismatch, not a reasoning problem. | The AI engine is designed for single-record discrepancy explanation (fee/GST/TDS reasoning). An aggregate mismatch across 500 records is not something it can usefully reason about. A human needs to inspect the batch composition. See §2.3 for rationale. |
| **Negative/net-debit payouts** — refund overhang exceeds gross sales (no bank credit, or a bank debit) | ✅ Handled as a special case. If the computed net payout is ≤ 0, generate an exception of type `net_debit_payout` with no bank match expected. If a corresponding bank debit exists, match against it. | Real merchant scenario, especially during heavy refund periods. |
| **Payout_id fallback** — settlement CSV has no explicit `payout_id` column | ✅ Fallback: group by shared UTR on settlement rows. If no shared UTR either, fall back to date-based grouping + running-sum heuristic, but **always** with `requires_human_confirmation = true`. | See §2.2 below for the risk analysis on heuristic grouping. |
| **1:1 passthrough** — datasets where each settlement has a unique UTR matching a unique bank credit | ✅ Trivially handled: each "batch" has exactly 1 settlement. Degenerates to existing behavior with zero overhead. | Backward compatibility — see §4. |

### 2.2 Risk Analysis: Heuristic Grouping Without Explicit Keys

When neither `payout_id` nor a shared UTR is available, the only fallback is to
infer groups from **date proximity** (settlements on the same date likely belong to
the same payout cycle) and **running-sum matching** (find a subset of settlements
whose net sum equals an unmatched bank credit).

**This is a subset-sum problem.** For `n` unmatched settlements and `m` unmatched bank
credits, the naive approach is O(2^n × m), which is computationally infeasible at
scale. Even with optimizations (meet-in-the-middle, dynamic programming on discretized
amounts), this is:

1. **NP-hard in the general case** — no polynomial-time guarantee.
2. **Potentially ambiguous** — multiple subsets might sum to the same bank amount.
3. **Dangerous to auto-accept** — a false grouping means misattributing money.

**Decision:** Heuristic grouping will be gated behind `requires_human_confirmation = true`.
The system will propose candidate groups, but **never auto-match** without an explicit
payout_id or shared UTR. This is a guardrail, not a limitation — silently auto-matching
an inferred group violates the project's audit principles.

The heuristic will use:
- Date windowing (same settlement date ± 1 day)
- Amount bucketing (sort candidates by plausible fee-adjusted net sums)
- Greedy single-bank-credit matching (try to match the largest unmatched bank credit first)

This will catch ~80–90% of inferrable cases in practice (most merchants settle daily with
one payout per day), but will **never claim 100% confidence** on inferred groups.

### 2.3 Out of Scope (WILL NOT Handle)

| Edge Case | Decision | Rationale |
|---|---|---|
| **Split tranches** — one payout split across 2+ bank credits (NEFT/RTGS cutoff limits) | ❌ Out of scope for MVP | This is the inverse problem (1:M on the bank side). It requires matching one payout against multiple bank credits, which is combinatorially harder and much rarer in practice. Razorpay typically uses NEFT for sub-₹10L and RTGS above, but does not split a single payout across both in the same cycle. **If this occurs in real data, it should be flagged as `unmatched_bank_credit` (existing exception) for manual resolution.** Adding this later is additive and does not conflict with the N:1 design. |
| **Cross-batch payout merging** — settlements from different upload batches belonging to the same payout | ❌ Out of scope | Each upload batch is an atomic unit in the current design. Cross-batch grouping would require a fundamentally different lifecycle model. |
| **AI-powered aggregation reasoning** — using the LLM to figure out groupings | ❌ Explicitly excluded | Per project principle: "Rules before AI." Aggregation is arithmetic and relational matching, not a reasoning problem. No LLM calls in the grouping logic. |

### 2.4 Decision on Aggregate Delta Routing

> *"Should an aggregate that doesn't balance to the paisa route to the existing AI
> verification engine, or become its own exception type?"*

**It should become its own exception type** (`payout_aggregate_mismatch`), not route to
the AI engine. Reasons:

1. **The AI validator ([`validator.py`](file:///E:/Razorpay/backend/ai/validator.py))
   is designed for single-record reasoning.** Its `FinanceVerificationResponse` schema
   has `difference_amount` and `likely_reason` fields scoped to one invoice↔settlement
   pair. It cannot meaningfully explain "the sum of 500 settlements is ₹47 less than
   the bank credit."

2. **Aggregate mismatches have different root causes** than individual discrepancies —
   typically: missing rows in the settlement export, dispute reserve holdbacks not
   itemized per-order, or inter-day settlement cutoff edge cases. These require a human
   to inspect the batch composition, not an AI to generate a plausible-sounding
   single-record explanation.

3. **The exception taxonomy already has infrastructure for this.** A new
   `payout_aggregate_mismatch` category in
   [`exception_taxonomy.py`](file:///E:/Razorpay/backend/rules/exception_taxonomy.py)
   is the correct home, with `financial_impact: "shortfall"` or `"excess"` and a
   `suggested_action` pointing at batch-level review.

---

## 3. Data Model Impact

### 3.1 New Table: `payout_batches`

A new first-class entity representing a gateway payout cycle — the grouping of N
settlement records that were remitted together as a single bank transfer.

```sql
CREATE TABLE payout_batches (
    id              VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          VARCHAR(100) NOT NULL DEFAULT 'org_default',
    batch_id        VARCHAR(36)  NOT NULL REFERENCES batches(id),
    payout_id       VARCHAR(100),
    utr             VARCHAR(100),
    payout_date     DATE,
    gross_amount    NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    total_fees      NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    total_gst       NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    total_tds       NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    net_amount      NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    settlement_count INTEGER NOT NULL DEFAULT 0,
    grouping_method VARCHAR(50) NOT NULL,  -- 'explicit_payout_id', 'shared_utr', 'date_heuristic', 'single_passthrough'
    requires_human_confirmation BOOLEAN NOT NULL DEFAULT FALSE,
    bank_record_id  VARCHAR(36) REFERENCES records(id),
    match_status    VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 'pending', 'matched', 'mismatch', 'unmatched'
    match_delta     NUMERIC(14,2),
    computation_trace JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payout_batches_batch_id ON payout_batches(batch_id);
CREATE INDEX idx_payout_batches_payout_id ON payout_batches(payout_id);
CREATE INDEX idx_payout_batches_utr ON payout_batches(utr);
CREATE INDEX idx_payout_batches_org_id ON payout_batches(org_id);
```

### 3.2 Modified Table: `records`

Add a nullable FK column to the existing `records` table linking each settlement record
to its payout batch:

```sql
ALTER TABLE records ADD COLUMN payout_batch_id VARCHAR(36) REFERENCES payout_batches(id);
CREATE INDEX idx_records_payout_batch_id ON records(payout_batch_id);
```

**Why a nullable FK on `records` rather than a join table?**

- A settlement record belongs to **at most one** payout batch (1:N, not M:N).
- A nullable FK is cheaper than a join table for reads (no extra join needed).
- Non-settlement records (invoices, bank rows) will have `payout_batch_id = NULL`.
- This is additive — existing records with `payout_batch_id = NULL` continue working.

### 3.3 Modified Model: `NormalizedRecord`

Add an optional `payout_id` field to
[`NormalizedRecord`](file:///E:/Razorpay/backend/normalizer/normalizer.py#L19-L35):

```python
class NormalizedRecord(BaseModel):
    # ... existing fields ...
    payout_id: Optional[str] = None   # NEW: gateway payout batch identifier
```

The normalizer's `normalize_settlement_row()` will extract `payout_id` from
`row.get("payout_id")` — already handled by the schema mapper's alias system
(see [`aliases.py`](file:///E:/Razorpay/backend/schema_mapper/aliases.py) L96:
`"payout_id"` is already a recognized alias for `settlement_id`).

**Important distinction:** `payout_id` is NOT the same as `settlement_id`. The
`settlement_id` is per-order (SET-001, SET-002, etc.). The `payout_id` groups multiple
settlements into one bank transfer (PAY-77). These are currently conflated in some
merchant archetypes' column mappings (e.g., `"settlement_id": "payout_id"` in
[`merchant_archetypes.py`](file:///E:/Razorpay/backend/synthetic_data/merchant_archetypes.py)
L104). The normalizer needs a new dedicated extraction path for the grouping key,
separate from `transaction_id`.

### 3.4 No Changes to `matches` Table Structure

The existing `matches` table continues to represent 1:1 record-level matches for the
**invoice↔settlement** leg. It does NOT need to be modified to support N:1.

For the **settlement↔bank** leg, the match is represented by `payout_batches.bank_record_id`
and `payout_batches.match_status`. This separation is deliberate:

- Invoice↔settlement matching is granular (per order) → `matches` table.
- Settlement↔bank matching is aggregated (per payout) → `payout_batches` table.
- Audit queries can join both to produce a complete 3-way trail.

### 3.5 SQLAlchemy Model (Python)

```python
class PayoutBatch(Base):
    __tablename__ = "payout_batches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(100), nullable=False, default="org_default", index=True)
    batch_id = Column(String(36), ForeignKey("batches.id"), nullable=False)
    payout_id = Column(String(100), nullable=True)
    utr = Column(String(100), nullable=True)
    payout_date = Column(Date, nullable=True)
    gross_amount = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    total_fees = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    total_gst = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    total_tds = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    net_amount = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    settlement_count = Column(Integer, nullable=False, default=0)
    grouping_method = Column(String(50), nullable=False)
    requires_human_confirmation = Column(Boolean, nullable=False, default=False)
    bank_record_id = Column(String(36), ForeignKey("records.id"), nullable=True)
    match_status = Column(String(50), nullable=False, default="pending")
    match_delta = Column(Numeric(14, 2), nullable=True)
    computation_trace = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    batch = relationship("Batch")
    bank_record = relationship("Record", foreign_keys=[bank_record_id])
    settlement_records = relationship("Record", backref="payout_batch",
                                       foreign_keys="Record.payout_batch_id")
```

And on `Record`:

```python
class Record(Base):
    # ... existing columns ...
    payout_batch_id = Column(String(36), ForeignKey("payout_batches.id"), nullable=True)
```

---

## 4. Backward Compatibility

### 4.1 Guarantee: Existing 1:1 Rules Are Untouched

The existing 7-rule chain in
[`rule_engine.py`](file:///E:/Razorpay/backend/rules/rule_engine.py) (L398–L405:
`RULE_FUNCTIONS` list) is **not modified, reordered, or conditionally bypassed**.

For datasets where each settlement has a unique UTR that matches a unique bank credit
(the current synthetic data), every settlement forms a "payout batch" of exactly 1 row
with `grouping_method = 'single_passthrough'`. The per-settlement rules fire exactly
as before. The only new behavior is that, after all 1:1 rules have run, unmatched
settlement↔bank pairs are grouped and retried at the batch level.

### 4.2 Regression Contract

All existing ground-truth benchmarks across all 10 merchant archetypes must pass at
**identical** precision/recall/F1 scores after this change. Any delta is a bug, not a
trade-off. The test suite will enforce this with a dedicated regression test that runs
the current synthetic datasets through the modified pipeline and asserts identical
match results.

### 4.3 Additive Rule, Not a Replacement

Settlement aggregation is a **post-processing pass** that runs after the existing
per-settlement rule chain. It does not intercept or modify the inputs to Rules 1–7.
Settlement records that already matched a bank credit 1:1 are excluded from
aggregation grouping (they are already reconciled).

---

## 5. Precision Requirements

### 5.1 Decimal-Only Arithmetic

**Every** summation, subtraction, and comparison in the aggregation path uses
`decimal.Decimal` with explicit `ROUND_HALF_UP` quantization to 2 decimal places.

**No `float` anywhere in the summation path.** This includes:
- Summing `settlement.amount` across N rows → `Decimal`
- Summing `settlement.fees`, `.gst`, `.tds` across N rows → `Decimal`
- Computing `net_amount = gross_amount - total_fees - total_gst - total_tds` → `Decimal`
- Comparing `net_amount` against `bank.amount` → `Decimal` comparison
- Computing `match_delta = net_amount - bank.amount` → `Decimal`

The `round_paisa()` function from
[`rule_engine.py`](file:///E:/Razorpay/backend/rules/rule_engine.py#L15-L17) will be
reused for all rounding.

### 5.2 Drift Testing at Scale

**The problem:** summing 5,000 `Decimal("xxx.xx")` values should produce a
mathematically exact result (Decimal addition is exact for finite precision), but
implementation bugs can introduce drift via:
- Intermediate rounding (rounding each partial sum instead of summing first, then rounding once)
- Mixed Decimal/float operations (a single `float()` cast corrupts precision)
- Incorrect Decimal context (using system default precision instead of explicit quantize)

**Test strategy:**
1. **Deterministic large-batch test:** Generate a synthetic payout batch of exactly
   5,000 settlement rows with known amounts. Compute the expected sum using Python's
   `Decimal` and compare against the aggregation function's output. Assert exact
   equality (not approximate).
2. **Adversarial penny drift test:** Generate 5,000 rows where each amount ends in
   `.01`, `.49`, `.50`, `.99` — the rounding boundary values. Verify no accumulated
   drift.
3. **Round-trip test:** Persist the payout batch to the DB (SQLite or PostgreSQL
   `NUMERIC(14,2)`), read it back, and verify the amounts are unchanged. This catches
   silent float coercion by the ORM or DB driver.

### 5.3 Tolerance Band for Aggregate Matching

The existing per-record penny tolerance is ₹2.00 (Rule 6). For aggregate matching,
the tolerance is also ₹2.00 — **not scaled by batch size**. Rationale:

- Rounding errors in Razorpay's own aggregation should not exceed ₹1.00 in practice
  (they round each order's fee, then sum, same as we do).
- A ₹2.00 tolerance on a ₹1,17,450 aggregate is 0.0017% — well within audit
  acceptability.
- Scaling tolerance linearly with batch size (e.g., ₹2.00 × N) would mask real
  errors. A ₹1,000 delta on a 500-order batch is a missing order, not a rounding error.

---

## 6. Audit Trail Requirements

### 6.1 Reconstructability Principle

Every aggregated match must be **fully reconstructable** by an external auditor who has
access to the database but **not** the ability to re-run the pipeline. This means:

1. **The `payout_batches` row** records the aggregate amounts, fee totals, grouping
   method, and match delta.
2. **The `records` rows** with `payout_batch_id = <this batch>` enumerate every
   individual settlement that was included in the aggregation.
3. **The `matches` rows** for each individual settlement record its invoice-level
   match status (matched/exception) independently of the payout-level match.
4. **The join** `payout_batches JOIN records ON records.payout_batch_id = payout_batches.id`
   produces the complete itemized breakdown.

### 6.2 Audit CSV Export Extension

The existing CSV export
([`reporter.py`](file:///E:/Razorpay/backend/reports/reporter.py)) will be extended
(not replaced) with additional columns for aggregated matches:

| New Column | Description |
|---|---|
| `payout_batch_id` | UUID of the payout batch (NULL for 1:1 matches) |
| `payout_id` | Gateway payout ID (if available) |
| `payout_utr` | Bank UTR for the aggregate payout |
| `payout_gross_amount` | Sum of constituent settlement amounts |
| `payout_net_amount` | Net payout after aggregate deductions |
| `payout_settlement_count` | Number of settlements in this payout |
| `payout_match_status` | 'matched', 'mismatch', 'unmatched' |
| `payout_match_delta` | Difference between net amount and bank credit |
| `payout_grouping_method` | How the batch was formed |

Existing columns remain unchanged. 1:1 matches will have these new columns as empty/NULL.

### 6.3 Computation Trace Format

Each `payout_batches` row stores a JSON computation trace in the `computation_trace`
column (JSONB), containing:

```json
{
  "constituent_settlement_ids": ["SET-001", "SET-002", "...", "SET-500"],
  "constituent_record_ids": ["uuid-1", "uuid-2", "...", "uuid-500"],
  "gross_amount_breakdown": {
    "sum_of_settlement_amounts": "120000.00",
    "individual_amounts": ["4500.00", "2200.00", "15750.00", "..."]
  },
  "deduction_breakdown": {
    "total_fees": "2400.00",
    "total_gst": "432.00",
    "total_tds": "1200.00",
    "total_other_deductions": "518.00"
  },
  "net_computation": "120000.00 - 2400.00 - 432.00 - 1200.00 - 518.00 = 115450.00",
  "bank_credit_amount": "115450.00",
  "match_delta": "0.00",
  "match_verdict": "exact"
}
```

> **Note:** The `individual_amounts` array inside `gross_amount_breakdown` may be
> truncated for very large batches (>1,000 rows) to avoid bloating the JSONB column.
> The full itemized breakdown is always recoverable via `records.payout_batch_id` join.
> The trace stores enough for a human to verify the arithmetic without the join.

---

## 7. Clarifying Questions

Before proceeding to Stage 2 (Architecture), I need decisions on a few genuinely
ambiguous points:

### Q1: Synthetic Data Generation for N:1

The existing synthetic data generator does **not** produce a `payout_id` column — each
settlement row has a unique `settlement_id` and unique `reference_number` (UTR). The
real Razorpay settlement report CSV typically includes a `payout_id` column that groups
rows belonging to the same payout cycle.

**Question:** Should the synthetic data generator be extended to produce N:1 datasets
(multiple settlements sharing a `payout_id` mapped to a single bank credit)? This is
required for meaningful testing. I plan to add a new synthetic scenario generation mode
alongside the existing 1:1 scenarios.

### Q2: `gross_amount` vs `net_amount` Semantics

In the Razorpay settlement report, each row's `amount` field can mean either:
- **Gross amount** (invoice amount, before fee deduction) — in which case `fees`, `gst`,
  `tds` are separate columns and net = amount - fees - gst - tds
- **Net amount** (after fee deduction) — in which case the settlement `amount` is
  already the net

The current codebase's Rule 5
([`match_fee_gst_tds_adjusted_amount`](file:///E:/Razorpay/backend/rules/rule_engine.py#L231-L313))
treats `settlement.amount` as the net (post-deduction) amount and `invoice.amount` as
the gross. **Is this interpretation correct for all merchant archetypes?** My reading of
the code says yes — the assertion is `settlement.amount == invoice.amount - fees - gst - tds`.

For aggregation, I will sum `settlement.amount` (net per-order) + sum `settlement.fees`
+ sum `settlement.gst` + sum `settlement.tds` to reconstruct the gross, and then verify
that `sum(settlement.amount)` equals the bank credit. **Does this match your
understanding of the data semantics?**

### Q3: Holdback / Dispute Reserve

The problem statement mentions "dispute-reserve holdbacks" as a deduction in the
aggregate payout. The current `NormalizedRecord` schema has `fees`, `gst`, `tds` but no
`holdback` or `dispute_reserve` field. In real Razorpay exports, this appears as an
additional deduction column.

**Question:** Should this feature spec include a `holdback` field on `NormalizedRecord`
and `records` table? Or should holdbacks be treated as an "other deduction" that
contributes to the aggregate mismatch delta and gets flagged for human review? I lean
toward the latter for MVP scope — adding a new deduction field is a data model change
that ripples through the normalizer, parser, and every rule.

---

## 8. Summary of Deliverables

If approved, this spec produces:

| Deliverable | Type |
|---|---|
| `payout_batches` table + SQLAlchemy model | New DB entity |
| `payout_batch_id` FK on `records` | Schema migration |
| `payout_id` field on `NormalizedRecord` | Normalizer extension |
| Settlement aggregation grouping logic | New module (`backend/rules/aggregation.py`) |
| Aggregate↔bank matching logic | Post-processing pass in pipeline |
| `payout_aggregate_mismatch` + `net_debit_payout` exception types | Exception taxonomy additions |
| Audit CSV export extensions | Reporter changes |
| Computation trace (JSONB) | Audit trail |
| Synthetic N:1 dataset generation | Test data |
| Unit + integration + regression tests | Test suite |
