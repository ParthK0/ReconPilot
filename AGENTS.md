# AGENTS.md — ReconPilot

Read `docs/01-PRD.md` through `docs/08-Roadmap.md` if you haven't already;
`docs/09-Build-Playbook.md` has the specific prompt for whatever phase
is active.

## Non-negotiable rules
- **Rules before AI**. The rule engine (`backend/rules/`) resolves
  everything it can; the Finance Verification Engine (`backend/ai/`)
  only ever sees what the rule engine could not resolve.
- **Never trust the Finance Verification Engine's self-reported confidence_score directly** — it always passes through
  `backend/ai/validator.py` before being written anywhere.
- **Synthetic data only**. Never fetch, generate, or reference real
  Razorpay, bank, or customer data.
- **MVP is frozen (01-PRD.md §6)**: no chatbot, no RAG, no voice
  interface, no multi-agent, no tax assistant, no cash forecasting —
  even if it looks like a quick addition.
- **Every feature that touches money needs a test** using the synthetic
  dataset's ground truth, not a hand-waved assertion.
- **Always state which files you touched and why**, even for small
  changes.

## Tech stack
Next.js + Tailwind + shadcn/ui (frontend) · FastAPI (backend) ·
PostgreSQL / SQLite · Pandas · GPT-5.6 Terra or Gemini 3.1 Pro/2.5 Pro (AI) ·
Vercel + Railway/Render (deploy). Full detail: `docs/02-SRS.md`.
