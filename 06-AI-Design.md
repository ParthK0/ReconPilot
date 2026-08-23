# 06 — AI Design
## ReconPilot — the document that proves this is an AI *system*, not an LLM wrapper

This is the document a reviewer will read most closely to judge whether this is a real AI system or a thin wrapper around a chat completion. Track 04's own rationale for existing is that the scarce resource in 2026 is the ability to verify what a model produces, not the ability to produce it — every design choice below is in service of that.

Throughout this document, the AI component is named the **Finance Verification Engine** — deliberately not "AI agent," because its job is narrower and more mechanical than that name implies (see Section 3).

## 1. Why AI Is Needed

The whole argument in four points — this is the "verification over generation" philosophy from 01-PRD.md §4, worked out in full:

1. **90–95% of records are handled deterministically**, by the rule engine alone (exact amounts, exact references, bounded date windows, known fee/GST/TDS formulas). No AI, no probabilistic risk, 100% confidence, for the large majority of the batch.
2. **The Finance Verification Engine is invoked only for the ambiguous remainder** — records the rule engine genuinely could not resolve (an unusual partial refund, a one-off manual fee adjustment, or simply a pair that doesn't line up numerically but might still be the same transaction). It never re-litigates a case the rules already settled.
3. **Every decision the Engine makes ships with evidence and a confidence score** — a named field, a plain-language explanation, and a confidence number. None of this is optional or after-the-fact; it's the shape of the Engine's only output (Section 4).
4. **Low-confidence cases are routed to a human, never counted as a match.** The Engine's self-reported confidence is never trusted on its own — Section 5's Deterministic Validator adjusts it, and anything that doesn't check out becomes an honest exception, not a quiet false positive.

The Engine's job is narrow by design: **reason about the residual the rule engine couldn't resolve, and explain it with evidence** — not to re-do the matching from scratch, and never to touch the 90–95% the rules already closed.

## 2. Why Rules Come First

1. **Trust** — a finance team needs to trust the 90%+ that's unambiguous. Those should never depend on a probabilistic model, full stop.
2. **Cost & latency** — LLM calls are the slow, expensive step. Rules-first means only genuinely ambiguous cases ever reach the AI (per the worked numbers in Section 9, that's roughly 5–15 records out of 100).
3. **Narrows the AI's job** — because rules absorb everything deterministic, the AI is never asked "does this match?" — only "given that rules couldn't decide, what's the most likely explanation, with evidence?" That's a much easier, much more checkable question.
4. **Auditability** — a rule match has a name (`rule_name`) anyone can look up in code. An AI match has a logged prompt, response, and independent numeric re-check. Nothing in the system is a black box.

## 3. Finance Verification Engine — Workflow

```
1. Rule engine emits a "miss" — either:
   (a) two candidate records that don't quite reconcile, or
   (b) one record with no candidate at all within the expected window
2. Orchestrator assembles a structured context payload:
   - both (or the one) records' relevant fields
   - the applicable fee/GST/TDS rules as data, not prose
   - the specific numeric delta, pre-computed (never ask the model to do arithmetic it doesn't have to)
3. LLM call, strict JSON schema output (Section 4) — this call IS the Finance Verification Engine
4. Deterministic Validator re-derives the claimed math independently:
   - if the Engine says "processing fee explains it," the validator checks:
     invoice.amount - settlement.fees == settlement.amount (within a cent tolerance)
   - this is the single most important design decision in this document:
     the Engine proposes; a plain Python function disposes.
5. If validated → matches row, method='ai', adjusted_confidence reflects the validator's own check
   (not just the model's self-reported number)
6. If not validated, or confidence < threshold → Exception Classifier
7. Every call — prompt, response, latency, token counts, cost — is logged to ai_verifications
```

## 4. Prompt Template

**System prompt:**
```
You are a financial reconciliation verification assistant.
You are given financial records that a deterministic rule engine could NOT
automatically match. Your job is NOT to decide whether they match — a
separate system will independently verify any numeric claim you make.

Your job is to propose the most likely explanation for the discrepancy,
using ONLY the fields provided. Never invent a fee, tax, or date that
isn't in the input.

Respond with ONLY valid JSON in this exact shape:
{
  "difference_amount": <number>,
  "likely_reason": "<one of: processing_fee | gst_deduction | tds_deduction |
                     settlement_delay | partial_refund | duplicate |
                     insufficient_evidence>",
  "reasoning_explanation": "<1-2 sentences, plain language>",
  "expected_value": <number>,
  "confidence_score": <0-100>,
  "evidence_field": "<the exact input field your claim rests on>"
}
```

**User prompt (templated):**
```
Invoice record: {invoice_json}
Settlement record: {settlement_json}
Bank record (if any): {bank_json}
Known fee schedule for this period: {fee_schedule_json}

The rule engine could not match these automatically. Explain the
discrepancy.
```

**Worked example** (the one from the source brief, formalized):

| Field | Value |
|---|---|
| Invoice amount | ₹12,000 |
| Settlement amount | ₹11,970 |
| Model output | `difference_amount: 30, likely_reason: "processing_fee", expected_value: 11970, confidence_score: 98, evidence_field: "settlement.fees"` |
| Validator check | `12000 - 30 (settlement.fees) == 11970` → **true** |
| Adjusted confidence shown to user | 99 (validator-confirmed exact match bumps the raw model score slightly, per the rubric in Section 5) |

## 5. Confidence Scoring

The score the UI shows is **never** the model's raw self-report alone — it's the model's score, adjusted by the deterministic validator:

| Validator outcome | Adjusted confidence |
|---|---|
| Claimed math reconciles exactly (to the paisa) | 95–100 |
| Reconciles within a small rounding tolerance (≤ ₹2) | 80–94 |
| Plausible reason, but the validator can't independently confirm the number (e.g. "likely duplicate" — a pattern match, not an equation) | 50–79, always routed to human review regardless of the model's own confidence |
| Validator actively contradicts the model's claim | force-set to < 50, routed to Exception Classifier as `unknown`, logged as a model disagreement for later prompt tuning |

This matters because ReconPilot's confidence number is **grounded in a Python `==` check**, not in an LLM's opinion of itself — that's the difference between a demo claim and a measured one.

## 6. Evidence Generation

Every AI-verified record shows, without the reviewer needing to re-derive anything:

- The natural-language explanation (1–2 sentences)
- The exact field the claim rests on (`evidence_field`)
- A **calculation trace**: `₹12,000 − ₹30 (processing fee) = ₹11,970 = settlement amount ✓`

The calculation trace is generated by the Deterministic Validator, not the LLM — it's the validator showing its own work, which is also what makes it trustworthy.

## 7. Exception Classification

| Category | Heuristic (mostly rule-based; AI adds only the write-up) |
|---|---|
| Settlement Delay | Invoice + bank record exist; settlement missing but still inside the expected delay window (default T+2 days) |
| Missing Credit | Expected settlement (per fee schedule) not found in the bank statement at all, *past* the delay window |
| Duplicate Invoice | Two invoices share order_id and amount |
| Refund Pending | A negative-amount bank entry references an already-matched settlement |
| Unknown | Doesn't fit any heuristic above — always the lowest AI-confidence bucket, always routed to a human, and reported honestly rather than hidden |

Classification staying rule-first (same philosophy as Section 2) means the AI's only job here, too, is writing the human-readable note — not deciding the bucket.

## 8. Failure Handling

| Failure | Handling |
|---|---|
| LLM timeout / error | Record → `needs_review`, reason = "AI unavailable"; batch still completes (NFR-5) |
| Malformed JSON output | One retry with a stricter reminder; second failure → `needs_review` |
| Hallucinated evidence (cites a field that doesn't actually support the claim) | Caught by the Deterministic Validator (Section 3, step 4) — this is exactly the failure mode that step exists to catch |
| Cost/rate-limit spike mid-batch | A per-batch spend ceiling (NFR-6) stops further AI calls and flags the remainder `needs_review` rather than let one bad run blow the budget — this also protects a live demo recording from an unpredictable bill |

## 9. Cost Estimates

Worked for a 100-record batch, using the source brief's own split (91 rule matches, 7 AI-verified, 2 needs-review → **~9 AI calls**):

- Each call: ~400–700 input tokens (both records + fee schedule + instructions), ~150–250 output tokens (small JSON object).
- At current (August 2026) API list pricing:

| Model | Input $/1M | Output $/1M | Cost for ~9 calls @ ~600 in / 200 out tokens |
|---|---|---|---|
| GPT-5.6 Luna | $0.20 | $1.20 | ≈ $0.003 |
| GPT-5.6 Terra | $2.00 | $12.00 | ≈ $0.032 |
| GPT-5.6 Sol | $5.00 | $30.00 | ≈ $0.081 |
| Gemini 2.5 Pro | ~$1.25 / ~$10.00 | | ≈ $0.027 |
| Gemini 3.1 Pro (≤200K ctx) | $2.00 | $12.00 | ≈ $0.032 |

**Takeaway: at this batch size, AI cost is a rounding error regardless of tier** — a few cents per 100-record run. That means the model choice below should be driven by reliability of structured output and reasoning quality on genuinely ambiguous cases, not by price. Treat this table as order-of-magnitude and check the live pricing pages before the demo — these numbers move (Terra and Luna were both cut within the last month as of this writing).

## 10. Model Choice

The source brief names "GPT-5 / Gemini 2.5 Pro" — both are now a generation behind the current lineup (GPT-5.6, Gemini 3.1). Recommendation:

- **Default: GPT-5.6 Terra, or Gemini 3.1 Pro / 2.5 Pro** — mid-tier is the sweet spot. The AI's job (Section 1) is deliberately narrow and structured, not open-ended reasoning, so flagship-tier (Sol / 3.1 Pro at long context) is very likely unnecessary overkill for this task specifically.
- **Escalation path:** if a mid-tier model's output fails the Deterministic Validator too often during testing (Section 8), that's a signal to try the flagship tier on just the disagreement cases before assuming the prompt is broken — cheap to test given Section 9's numbers.
- **Don't hand this decision to Codex/Antigravity without checking it yourself first** — this is one of the few choices in this whole project worth spending your own judgment on, precisely because it's easy for an agent to default to "just use the biggest model" when the actual constraint is reliability of a narrow JSON output, not raw intelligence.
