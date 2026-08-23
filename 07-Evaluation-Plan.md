# 07 — Evaluation Plan
## ReconPilot

Track 04 grades on three things: real throughput, accuracy that's actually been measured rather than asserted, and an exception list reported as-is rather than tidied up for the video. This document exists to make that literal — every metric below is computed from the same synthetic batch, on the same run, and reported without cherry-picking.

## 1. The Trick That Makes This Measurable

Because the dataset is synthetic (100 invoices, 100 settlements, 100 bank transactions, generated on purpose), **ground truth is known** — which records should match, and which are deliberately-injected edge cases. A convincing dataset needs every one of these categories represented, not just the easy exact matches:

- Exact matches (order ID + UTR + amount all agree)
- Fee deductions, GST deductions, TDS deductions
- Delayed settlements
- Refunds
- Duplicate invoices
- Missing bank credits
- Genuine unknown exceptions (deliberately don't fit any heuristic)

This turns "does it work" into an actual confusion matrix instead of a demo vibe — see 08-Roadmap.md §1 Phase 1 for where this gets built.

## 2. Metrics

| Metric | Formula | What it catches |
|---|---|---|
| Match rate | matched / total records | Overall throughput |
| Precision | TP / (TP + FP) | False matches — the worst failure mode in finance; a confident wrong match is worse than an honest "unknown" |
| Recall | TP / (TP + FN) | Real matches the system missed and dumped into exceptions unnecessarily |
| False positives | Count of "matched" results that ground truth says shouldn't have matched | Direct measure of the failure a panel is watching for |
| False negatives | Count of true matches that ended up as false exceptions | Cost of being overly conservative |
| Finance Verification Engine accuracy | Of only the Engine-touched subset, % where its stated reason matches ground truth | Distinct from overall precision — this specifically grades the AI module, not the rule engine riding along |
| Processing time | Wall-clock, upload to report, for the full batch | Throughput |
| Manual hours saved | (records × assumed manual minutes/record) − (system time + residual review time) | ROI legibility |

## 3. Target Thresholds

| Metric | Target | Stretch |
|---|---|---|
| Match rate | ≥ 95% | ≥ 98% |
| Precision | ≥ 99% | 100% |
| Recall | ≥ 90% | ≥ 95% |
| Finance Verification Engine accuracy | ≥ 90% on the Engine-touched subset | ≥ 95% |
| Processing time (100 records) | < 30s | < 15s |

## 4. Test Methodology

1. Generate the synthetic dataset with a labeling script that records, for every injected record, what it *should* resolve to (matched-by-rule / matched-by-AI-and-which-reason / a specific exception category).
2. Run the full pipeline once, unmodified, on that labeled batch.
3. Score every metric above by comparing the pipeline's output to the labels — a script, not a manual eyeball count, so it's re-runnable every time the rule engine or prompt changes.
4. Report the **actual numbers from that run** in the dashboard and the pitch video — not a best-of-N cherry-pick. If a run has 3 false positives, the exception report and the video say so.
5. Re-run after any change to rules or prompts, and keep the last few runs' numbers so a regression is visible, not just the latest green run.

## 5. What "Honest Exception List" Means in Practice

- Every record the system couldn't resolve appears in the exception report exactly once, with a category — never silently dropped, never merged away to make the match-rate number look better.
- "Unknown" is reported as unknown, not force-classified into whichever category makes the dashboard prettiest.
- The evaluation script and the dashboard read from the same `metrics_snapshots` table (04-Database-Design.md) — there's no separate "demo numbers" path that could drift from what the system actually computed.
