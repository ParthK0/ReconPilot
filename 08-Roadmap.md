# 08 — Roadmap
## ReconPilot

## 0. Timeline Reality Check

Reported application close for the Buildathon is around **September 5, 2026** (~2 weeks out from today) — confirm the exact date on the [official form](https://razorpay.com/buildathon/), since it wasn't printed on the page itself when this was checked, only in a secondhand repost. That runway is the reason this roadmap is 7 tight phases, not 7 loose ones: there's no slack for the "will not build" list in 01-PRD.md to sneak back in.

Phases are written as relative day-ranges assuming a ~10–12 day active build window, evenings/weekends realistic for a student schedule — compress or stretch to your actual calendar, but keep the *order* and the *checkpoints*, since each phase's checkpoint is what makes "vibecoding with proper checking" actually mean something instead of just a phrase.

## 1. Phases

### Phase 1 — Project Setup (Day 1)
- Repo scaffold: `frontend/`, `backend/` (`api/`, `parser/`, `normalizer/`, `rules/`, `ai/`, `evaluation/`, `reports/`), `synthetic-data/`, `docs/` (these 8 files live here).
- Provision Postgres, wire up FastAPI + Next.js skeletons that can talk to each other.
- **Write the synthetic data generator first**, before any pipeline code — everything downstream (rules, AI, evaluation) needs labeled test data to be checkable at all. A convincing dataset needs every one of these represented, not just the easy exact matches:
  - Exact matches (order ID + UTR + amount all agree)
  - Fee deductions
  - GST deductions
  - TDS deductions
  - Delayed settlements
  - Refunds
  - Duplicate invoices
  - Missing bank credits
  - Unknown / genuinely-doesn't-fit-any-category exceptions
- **Checkpoint:** `docs/` committed, empty frontend hits a "hello" backend route, generator produces 100+100+100 rows with a ground-truth label file covering every category above.

### Phase 2 — CSV Parsing & Normalization (Day 2–3)
- Implement the 3 parsers + the unified schema (04-Database-Design.md).
- **Checkpoint:** every generated row round-trips into `records` with no silently-dropped fields — spot-check 10 rows by hand against the source CSV.

### Phase 3 — Rule Engine (Day 4–6)
- Implement each rule (order ID, UTR, exact amount, date window, fee/GST/TDS-adjusted amount) as its own small, independently testable function.
- **Checkpoint:** unit tests pass for every rule *and* you manually verify 10 rule-matched records against the source CSVs by hand. This is the phase where reading every line matters most — the rule engine is the 90% everything else's trust depends on.

### Phase 4 — Finance Verification Engine (Day 7–8)
- Implement the orchestrator, the prompt (06-AI-Design.md §4), and — before anything else — **the Deterministic Validator**. Build the validator first, even against fake model output, so it exists before you trust a single real response.
- **Checkpoint:** run against every injected edge case in the synthetic set; check the Engine's stated reason against the ground-truth label for each one; confirm the validator actually catches at least one deliberately-wrong test case you feed it on purpose.

### Phase 5 — Dashboard (Day 9)
- Reconciliation table, exception report, metrics dashboard — match rate, precision, processing time, manual reviews, hours saved, all visible in the UI itself (01-PRD.md §8 numbers), not just in a report doc.
- **Checkpoint:** every number on the dashboard traces to a query against `metrics_snapshots` — no hardcoded demo numbers anywhere in the frontend.

### Phase 6 — Evaluation (Day 10)
- Run 07-Evaluation-Plan.md's methodology for real; compute precision/recall/false-positive-rate against ground truth.
- **Checkpoint:** if precision is below target, that's a rules/prompt bug to fix now, not a number to soften in the video later.

### Phase 7 — Demo Polishing (Day 11–12)
- Rehearse the exact 5-minute structure from 01-PRD.md §9.
- Seed one clean "hero" edge case (the ₹30 fee example) so the AI-verification moment is guaranteed to render well on camera — staging a real case for visibility, not fabricating a result.
- Error-proof the recording: run the batch once right before recording, don't reuse a screenshot from a different run.
- Write the README/architecture writeup a reviewer will actually read.

## 2. Tooling Workflow — Antigravity + Codex (Go), with real checking

You already build with a "vibe coding with understanding" approach — reading every line rather than trusting output blind. The workflow below is that same instinct, applied across two agents with genuinely different quota shapes, not a replacement for it.

### Division of labor

| Tool | What it's for here | Why |
|---|---|---|
| **Antigravity** (IDE, or the standalone Agent Manager) | The daily driver for most of Phases 1–5 — scaffolding, the normalizer, the dashboard, wiring the API | Free in public preview with generous Gemini 3 Pro rate limits; its Agent Manager produces **artifacts** (task lists, screenshots, verification runs) by design, which is exactly the checkable trail this project needs, and it can drive a browser to actually click through your own dashboard as a test, not just write code that claims to work |
| **Codex (ChatGPT Go)** | A small number of high-value, tightly-scoped tasks — the rule engine's trickiest fee/GST/TDS math, the prompt + validator pair in Phase 4, or a second, independent read of a module Antigravity already wrote | Go's Codex access is real but explicitly positioned for lightweight tasks, on a shared, non-purchasable quota — it's not the tool to point at a whole phase and walk away from |

### The actual loop, per phase

1. **Spec first, every time.** Before opening either tool for a phase, point it at the matching doc from this set (e.g., Phase 4 → `06-AI-Design.md`) rather than describing the task from memory in a prompt. Keep a short `AGENTS.md` at the repo root with the constraints that apply everywhere (tech stack, "rules before AI," "never trust AI confidence without the validator," synthetic-data-only) — Codex CLI reads this convention automatically, and pointing Antigravity at the same file keeps both agents working off one source of truth instead of drifting apart.
2. **Let the agent run, then read the diff — all of it, not the summary.** This is where your existing philosophy does the actual work; the tools just need you to make time for it. Antigravity's artifacts (task list + verification results) are a starting point for review, not a substitute for opening the changed files.
3. **Check against the phase's checkpoint** (Section 1) before moving on — not "does it look right," but the specific, stated check (unit tests pass *and* 10 hand-verified records; the validator catches a deliberately-wrong test case; every dashboard number traces to a real query).
4. **Commit at every verified checkpoint**, not at the end of a phase. A checkpoint you can `git revert` to is what makes it safe to let an agent run further than you'd otherwise trust — if Phase 4 goes sideways, you lose an afternoon, not the whole rule engine underneath it.
5. **Spend Codex-Go quota deliberately.** Check `/status` (CLI) or the usage dashboard before starting anything you'd call "a real session" rather than a quick fix — Free/Go can't buy top-up credits mid-task the way Plus/Pro can, so a burned quota mid-Phase-4 is a multi-hour wait, not a $5 top-up. Reserve it for the tasks in the table above; do routine scaffolding and UI work in Antigravity instead.
6. **Use one agent to check the other, on the parts that matter most.** The Deterministic Validator (06-AI-Design.md §3–5) is the single highest-value thing to get right in this whole project — it's worth having Codex and Antigravity each take an independent pass at it (or one write it and the other review it) rather than accepting the first version either produces.

### A note on verifying, not just building

Track 04's own rationale is that what's scarce in 2026 is the capacity to check what a model produces, not the capacity to produce it in the first place. That's not a constraint fighting against vibecoding — it's the exact skill the checkpoints above are built to demonstrate.
