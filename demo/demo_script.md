# ReconPilot — 5-Minute Pitch & Demo Video Script
> **Target Audience:** Razorpay AI Buildathon Judges & Technical Reviewers  
> **Total Time:** Exactly 5:00 Minutes  
> **Key Message:** *"Throughput plus measured accuracy plus an honest exception list. One cherry-picked match proves nothing."*

---

## 🎬 Video Overview & Timeline

| Timestamp | Section | Visual on Screen | Key Talking Points |
|---|---|---|---|
| **0:00 - 0:45** | **The Problem** | Slide / Diagram showing Invoices vs Settlements vs Bank | The $100M 3-way reconciliation gap, MDR fee drift, and hidden revenue leaks. |
| **0:45 - 1:45** | **Smart Ingestion** | Live UI: Upload Panel (`http://localhost:3000`) | Drag-and-drop 3 dirty CSVs, schema alias auto-detection, and formula protection. |
| **1:45 - 2:45** | **Rules Engine (Sub-ms)** | Live UI: Dashboard & Match Table | Instant 90%+ match in <1s, 6 deterministic rules, and penny tolerance band ($\le ₹2.00$). |
| **2:45 - 3:45** | **Finance Verification Engine** | Live UI: Evidence Drawer & AI Trace | Gemini AI reasoning through non-standard MDR fees with Python arithmetic verification. |
| **3:45 - 4:30** | **Exception Queue & Review** | Live UI: Exception Grid & Modal | Honest gap detection (`missing_settlement`, `unmatched_bank_credit`) and 1-click human review. |
| **4:30 - 5:00** | **ROI & Production Architecture** | Terminal: `pytest` / `docker compose` | 100% precision, 0 false positives, 4.8 hrs saved/batch, and production Docker containerization. |

---

## 🎙️ Spoken Script & Screen Actions

### ⏱️ 0:00 – 0:45 | 1. The $100M Reconciliation Problem
* **Screen:** Show system problem slide or the architecture diagram.
* **Voiceover:**
  > *"Hi everyone, welcome to ReconPilot — our submission for the Razorpay AI Buildathon Track 04: AI Finance Controller.*  
  >  
  > *Every high-volume merchant faces a silent, multi-million dollar problem: 3-way financial drift. ERP invoices, Razorpay settlement tranches, and actual bank account credits rarely match 1-to-1 due to payment gateway MDR fees, GST, TDS deductions, timing delays, and chargebacks.*  
  >  
  > *Today, finance teams spend hundreds of hours manually cross-referencing messy spreadsheets. Many AI solutions try to dump whole ledgers into a generic chatbot and hope for the best. ReconPilot takes a strictly engineered approach: **Rules Before AI**, sub-second throughput, measured accuracy, and mathematical validation on every single AI reasoning claim."*

---

### ⏱️ 0:45 – 1:45 | 2. Smart CSV Ingestion & Schema Understanding
* **Screen:** Open `http://localhost:3000`, switch to the **"Upload & Ingest"** tab.
* **Action:** Select a merchant profile (e.g. **D2C Retail**) and drag the 3 sample CSV files (`invoices.csv`, `settlements.csv`, `bank_statements.csv`).
* **Voiceover:**
  > *"Let's look at ReconPilot in action. Ingestion starts with 3 dirty, heterogeneous data sources: the merchant's Internal Invoices, Razorpay Settlement exports, and raw Bank Statements.*  
  >  
  > *Our Safe Schema Mapper uses financial alias dictionaries with strict 0.95 confidence gating. Whether the column is named 'gross_value', 'payout_ref_id', or 'closing_bal', ReconPilot maps and normalizes them automatically. Furthermore, our parser neutralizes CSV formula injection attacks to ensure enterprise security."*

---

### ⏱️ 1:45 – 2:45 | 3. Sub-Second Deterministic Rules Engine
* **Screen:** Click **"Run Recon Engine"** and navigate to the **"Reconciliation Dashboard"**.
* **Action:** Highlight the **KPI Metrics Cards** and the **Recharts Stacked Match Distribution**.
* **Voiceover:**
  > *"When we click 'Run Recon Engine', our 6-Rule Deterministic Engine processes the entire batch in just **0.63 seconds**.*  
  >  
  > *It executes 6 hierarchical rules: Exact Order ID, UTR Reference Number, Exact Amount, T+2 Settlement Windows, Dynamic Merchant Fee Schedules, and our Penny Tolerance Matcher for rounding variances under ₹2.00.*  
  >  
  > *Notice that 90%+ of all transactions are resolved instantly with 100% confidence by deterministic code without making a single unnecessary LLM call."*

---

### ⏱️ 2:45 – 3:45 | 4. Finance Verification Engine & Hard Arithmetic Guard
* **Screen:** In the **"3-Way Match Table"**, click an AI-Verified record (e.g., non-standard fee or commercial adjustment) to open the **Evidence Drawer**.
* **Action:** Point out the **AI Reasoning box**, **Validation Status badge (Passed)**, and the 3-way trace breakdown.
* **Voiceover:**
  > *"What happens to the remaining edge cases that rules couldn't match? They enter our **Finance Verification Engine** powered by Gemini.*  
  >  
  > *Here, the AI examines rate card discrepancies, promotional merchant credits, and one-off fees. But here is the critical rule: **we never trust the AI blindly**.*  
  >  
  > *Every explanation passes through our Python **Deterministic Arithmetic Validator**. If the LLM claims a ₹30 one-off fee accounts for the difference, our solver re-calculates `Gross - Settlement == ₹30.00`. If the math doesn't balance to the exact cent, confidence is downgraded and flagged for human review."*

---

### ⏱️ 3:45 – 4:30 | 5. 3-Way Gap Detection & Controller Review Loop
* **Screen:** Navigate to the **"Exceptions"** tab and open the **Review Modal** on a discrepancy.
* **Action:** Show the categorized exceptions: `Missing Settlement`, `Unmatched Bank Credit`, `Timing Delay`. Click **"Approve Adjustment"**.
* **Voiceover:**
  > *"ReconPilot doesn't hide missing records. Our 3-Way Gap Detector flags invoices that were never settled by the gateway, as well as mystery bank deposits without settlement records.*  
  >  
  > *The human finance controller can review the full 3-way evidence and approve adjustments with one click. These approvals are captured in our **Feedback Memory**, which uses multi-factor similarity ranking to guide future verifications."*

---

### ⏱️ 4:30 – 5:00 | 6. Benchmark Results, ROI & Production Deployment
* **Screen:** Show the terminal running `python -m backend.evaluation.score --adversarial` and `pytest -v`, then show the `docker-compose.yml`.
* **Voiceover:**
  > *"To prove this isn't just a cherry-picked demo, our evaluation suite runs against an independent adversarial benchmark with noisy rounding and gap exceptions. Results: **100% Precision, 100% Recall, Zero False Positives**, saving **4.8 hours of manual labor per batch**.*  
  >  
  > *ReconPilot is fully production-ready, passing all **83 unit tests**, and deployable in 1 command via Docker Compose with PostgreSQL and Next.js.*  
  >  
  > *Thank you, and we look forward to your questions!"*

---

## 💡 Top Tips for Recording:
1. **Resolution:** 1080p (1920x1080) in Dark Mode.
2. **Audio:** Speak clearly and maintain an energetic, confident tone.
3. **Cursor:** Use smooth cursor movements when clicking through the tabs and drawers.
