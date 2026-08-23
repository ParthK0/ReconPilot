# 01 — Product Requirements Document
## ReconPilot — AI-Powered Finance Reconciliation Agent

> **Track fit:** This project is scoped for the **Razorpay AI Buildathon**, Track 04 — *"AI Finance Controller"* ("Run the books and the cash position"). The track's stated bar: **"Throughput plus measured accuracy plus an honest exception list. One cherry-picked match proves nothing."** Every section below is written to satisfy that bar, not just the general idea of "reconciliation."
>
> The Buildathon's deliverable is **not a live pitch** — it's a public GitHub repo, a 5-minute recorded pitch video, and an architecture writeup, reviewed asynchronously by a hiring panel (shortlisted builders then go to a panel interview). Applications reportedly close around **September 5, 2026** — confirm the exact date on the [official page](https://razorpay.com/buildathon/), since that date wasn't printed on the page itself when this was checked, only in a secondhand repost.

---

## 1. Problem Statement

Finance and ops teams reconcile three data sources by hand every settlement cycle:

| Source | What it is |
|---|---|
| Razorpay Settlement Report | What Razorpay actually paid out, net of fees/GST/TDS |
| Bank Statement | What actually landed in the bank account |
| Invoice Records | What was billed to the customer |

Doing this manually is slow, error-prone, and nearly impossible to audit after the fact — nobody can reconstruct *why* a ₹30 difference was accepted as a match three weeks later. ReconPilot automates the matching and, critically, **explains every decision it couldn't make deterministically**, so a human reviewer can trust the 90%+ that's automatic and focus only on genuine exceptions.

## 2. Users

| User | What they need from ReconPilot |
|---|---|
| Finance/ops analyst (primary) | Upload three files, get a reconciled report back in seconds instead of hours |
| Finance manager / controller (secondary) | An audit trail — every AI-touched match has evidence, not just a checkbox |
| Buildathon panel (tertiary, but real) | A working repo + a 5-minute video that proves throughput, measured accuracy, and an *honest* exception list — not a cherry-picked demo |

## 3. Goals

1. **Primary:** Close one finance-ops loop end-to-end — upload → normalize → match → verify → classify → report — across a batch of 50–100+ synthetic records, and report match rate plus unresolved exceptions honestly.
2. **Secondary:** Prove a hybrid architecture: deterministic rules resolve the unambiguous majority; AI is reserved for, and explains, only the genuine edge cases, with evidence and a confidence score attached to every AI decision.
3. **Tertiary:** Make the ROI legible — hours saved, processing time, precision — so a non-technical reviewer (or a panel member skimming a repo) gets the point in the first 60 seconds.

## 4. Features (MVP)

| # | Feature | Maps to |
|---|---|---|
| 1 | CSV upload — settlement, bank, invoice | Module 1 |
| 2 | Normalize all three into one schema | Module 2 |
| 3 | Rule engine: exact amount, UTR, order ID, settlement window, fees, GST, TDS | Module 3 |
| 4 | AI verification agent — only on rule-engine misses, always with evidence + confidence | Module 4 |
| 5 | Exception classifier — 5 categories, not a flat "unmatched" pile | Module 5 |
| 6 | Metrics dashboard — match rate, precision, processing time, hours saved | Module 6 |
| 7 | *(Stretch)* 3-day cash position forecast | Only after core is demo-ready |

## 5. Scope

**In scope:** the full loop above, run against synthetic data, with an evaluation harness that scores it against known ground truth.

**Explicitly out of scope** (per the source brief — don't let vibecoding wander into these):
- Generic chatbot / RAG over CSVs / voice assistant
- Multiple autonomous agents talking to each other
- Tax-matching or cash-forecasting as MVP features (forecast is stretch-only; tax rules are inputs to the rule engine, not a separate product)
- Any finance feature not on the direct path from "3 CSVs in" to "reconciliation report out"

**Stretch (only if core is finished and polished):** cash position forecast — "given today's bank balance, pending settlements, refunds, and invoices, what will my cash position be in 3 days?"

## 6. Success Metrics

| Metric | Target | Why it matters for the track's bar |
|---|---|---|
| Overall match rate | ≥ 95% on a 100-record synthetic batch | Throughput |
| Precision (of records marked "matched") | ≥ 99% | False matches are worse than false exceptions in finance |
| AI-verification accuracy | Measured against ground truth on the AI-touched subset, not just overall | Measured accuracy, not a vibe |
| Manual-review rate | As low as honestly possible, reported as-is | Honest exception list — don't hide a bad number |
| Processing time | Under ~15–30s for 100 records | Throughput |
| Manual hours saved | Estimated vs. a stated manual-reconciliation baseline | ROI legibility |

## 7. Demo Story (5-minute video structure)

1. **Problem (30s)** — "Finance teams spend hours reconciling settlements, bank statements, and invoices by hand."
2. **Upload (30s)** — show the three CSVs going in.
3. **Live processing (60s)** — reading → matching → verifying → done, with the actual timer visible.
4. **One AI-verified record, in detail (90s)** — the "wow" moment: a real ₹30 fee discrepancy, the AI's reasoning, its evidence, its confidence score, and the deterministic check that confirmed the AI's math.
5. **Dashboard (60s)** — the numbers from Section 6, live off this run, not a screenshot from a better run.
6. **Exception report, shown honestly (30s)** — the cases it didn't resolve, grouped and labeled, closing with: *"This system doesn't just automate reconciliation — it tells you exactly what it knows, what it inferred, and what still needs a human."*
