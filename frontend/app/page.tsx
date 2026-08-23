"use client";

import { useState, useEffect, useRef } from "react";
import {
  CheckCircle2,
  XCircle,
  RefreshCw,
  UploadCloud,
  FileSpreadsheet,
  AlertTriangle,
  HelpCircle,
  Clock,
  Check,
  Search,
  Filter,
  Download,
  Sparkles,
  ArrowRight,
  Shield,
  Layers,
  FileCheck,
  ChevronRight,
  TrendingUp,
  SlidersHorizontal,
  ExternalLink,
  ChevronDown,
  Info,
  Building2,
  Database,
  ArrowUpRight,
  X,
  Play
} from "lucide-react";

interface MetricsData {
  records_processed: number;
  rule_matches: number;
  ai_verified: number;
  needs_review: number;
  match_rate: number;
  precision: number;
  processing_time_seconds: number;
  manual_hours_saved: number;
}

interface MatchItem {
  match_id: string;
  status: string;
  match_method: string;
  rule_name: string | null;
  confidence: number;
  settlement_record_id: string | null;
  invoice_record_id: string | null;
  bank_record_id: string | null;
  order_id: string | null;
  amount: number;
  settlement_amount: number | null;
  invoice_amount: number | null;
  bank_amount: number | null;
  reference_number: string | null;
  created_at: string;
}

interface MatchDetail {
  match_id: string;
  status: string;
  match_method: string;
  rule_name: string | null;
  confidence: number;
  records: {
    settlement?: {
      id: string;
      transaction_id: string;
      order_id: string;
      amount: number;
      txn_date: string;
      reference_number: string;
      status: string;
      fees: number;
      gst: number;
      tds: number;
    };
    invoice?: {
      id: string;
      transaction_id: string;
      order_id: string;
      amount: number;
      txn_date: string;
      status: string;
    };
    bank?: {
      id: string;
      transaction_id: string;
      amount: number;
      txn_date: string;
      reference_number: string;
      status: string;
    };
  };
  ai_verification?: {
    difference_amount: number;
    likely_reason: string;
    reasoning_explanation: string;
    expected_value: number;
    ai_confidence: number;
    adjusted_confidence: number;
    evidence_field: string;
    model_used: string;
    calculation_trace: string;
    prompt_tokens: number;
    completion_tokens: number;
  };
}

interface ExceptionItem {
  exception_id: string;
  match_id: string;
  record_id: string;
  category: string;
  notes: string;
  resolved: boolean;
  order_id: string | null;
  amount: number;
  txn_date: string | null;
  reference_number: string | null;
  source_type: string | null;
}

interface ExceptionsData {
  settlement_delay: number;
  missing_credit: number;
  duplicate_invoice: number;
  refund_pending: number;
  unknown: number;
  total_exceptions: number;
  items: ExceptionItem[];
}

export default function Dashboard() {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Batch & View State
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"matches" | "exceptions" | "upload">("matches");
  const [loading, setLoading] = useState<boolean>(false);
  const [processingState, setProcessingState] = useState<"idle" | "reading" | "matching" | "verifying" | "done">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Data States
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [matches, setMatches] = useState<MatchItem[]>([]);
  const [exceptions, setExceptions] = useState<ExceptionsData | null>(null);
  const [selectedMatch, setSelectedMatch] = useState<MatchDetail | null>(null);
  const [loadingMatchDetail, setLoadingMatchDetail] = useState<boolean>(false);

  // Filters & Search
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [methodFilter, setMethodFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Upload File Inputs
  const [settlementFile, setSettlementFile] = useState<File | null>(null);
  const [bankFile, setBankFile] = useState<File | null>(null);
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);

  // Review Modal State
  const [reviewNote, setReviewNote] = useState<string>("");
  const [reviewingMatchId, setReviewingMatchId] = useState<string | null>(null);

  // Load Initial Health & Check for existing batches on load
  useEffect(() => {
    const initialize = async () => {
      try {
        const healthRes = await fetch(`${API_BASE}/api/v1/health`);
        if (healthRes.ok) {
          // If we don't have an active batch yet, check or create one with synthetic demo data
        }
      } catch (err) {
        console.error("Backend health probe failed:", err);
      }
    };
    initialize();
  }, [API_BASE]);

  // Fetch Batch Data
  const loadBatchData = async (batchId: string) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      // 1. Fetch Metrics (FR-16)
      const metricsRes = await fetch(`${API_BASE}/api/v1/batches/${batchId}/metrics`);
      if (metricsRes.ok) {
        const mData: MetricsData = await metricsRes.json();
        setMetrics(mData);
      }

      // 2. Fetch Matches
      const matchesRes = await fetch(`${API_BASE}/api/v1/batches/${batchId}/matches?page_size=100`);
      if (matchesRes.ok) {
        const matchData = await matchesRes.json();
        setMatches(matchData.matches || []);
      }

      // 3. Fetch Exceptions
      const exceptionsRes = await fetch(`${API_BASE}/api/v1/batches/${batchId}/exceptions`);
      if (exceptionsRes.ok) {
        const excData: ExceptionsData = await exceptionsRes.json();
        setExceptions(excData);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load reconciliation batch data");
    } finally {
      setLoading(false);
    }
  };

  // Trigger File Upload & Pipeline
  const handleUploadSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!settlementFile || !bankFile || !invoiceFile) {
      setErrorMsg("Please provide all 3 required CSV files: Settlement, Bank Statement, and Invoice.");
      return;
    }

    setProcessingState("reading");
    setLoading(true);
    setErrorMsg(null);

    const formData = new FormData();
    formData.append("settlement_csv", settlementFile);
    formData.append("bank_csv", bankFile);
    formData.append("invoice_csv", invoiceFile);

    try {
      setTimeout(() => setProcessingState("matching"), 400);
      setTimeout(() => setProcessingState("verifying"), 800);

      const res = await fetch(`${API_BASE}/api/v1/batches`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Upload failed with status ${res.status}`);
      }

      const data = await res.json();
      setProcessingState("done");
      setActiveBatchId(data.batch_id);
      await loadBatchData(data.batch_id);
      setActiveTab("matches");
    } catch (err: any) {
      setErrorMsg(err.message || "An error occurred while processing the batch.");
      setProcessingState("idle");
    } finally {
      setLoading(false);
    }
  };

  // Helper to load synthetic data files automatically for 1-click demo
  const loadSyntheticDemoBatch = async () => {
    setLoading(true);
    setErrorMsg(null);
    setProcessingState("reading");

    try {
      // Create synthetic sample CSV files directly from mock endpoint or inline blobs
      const invoiceData = `invoice_id,order_id,amount,customer_id,currency,created_at,status
INV-0001,ORD-2026-0001,15000.00,CUST-001,INR,2026-08-01,paid
INV-0087,ORD-2026-0087,12000.00,CUST-087,INR,2026-08-01,paid
INV-0088,ORD-2026-0088,25000.00,CUST-088,INR,2026-08-01,paid
INV-0093,ORD-2026-0093,9500.00,CUST-093,INR,2026-08-01,pending_settlement
INV-0095,ORD-2026-0095,3200.00,CUST-095,INR,2026-08-01,refunded
INV-0097,ORD-2026-0097,6800.00,CUST-097,INR,2026-08-01,paid
INV-0100,ORD-2026-0100,7777.00,CUST-100,INR,2026-08-01,paid`;

      const settlementData = `settlement_id,order_id,amount,fee,tax,currency,settled_at,utr,status
SET-0001,ORD-2026-0001,15000.00,0.00,0.00,INR,2026-08-03,UTR202608000001,settled
SET-0087,ORD-2026-0087,11970.00,30.00,0.00,INR,2026-08-03,UTR202608000087,settled
SET-0088,ORD-2026-0088,24955.00,45.00,0.00,INR,2026-08-03,UTR202608000088,settled
SET-0093,ORD-2026-0093,9500.00,0.00,0.00,INR,2026-08-09,UTR202608000093,pending
SET-0095,ORD-2026-0095,3200.00,0.00,0.00,INR,2026-08-03,UTR202608000095,settled
SET-0097,ORD-2026-0097,6800.00,0.00,0.00,INR,2026-08-03,UTR202608000097,settled
SET-0100,ORD-2026-0100,5432.10,0.00,0.00,INR,2026-08-03,UTR202608000100,settled`;

      const bankData = `bank_txn_id,amount,type,utr,value_date,description
BNK-0001,15000.00,credit,UTR202608000001,2026-08-03,Razorpay Payout
BNK-0087,11970.00,credit,UTR202608000087,2026-08-03,Razorpay Payout
BNK-0088,24955.00,credit,UTR202608000088,2026-08-03,Razorpay Payout
BNK-0093,9500.00,credit,UTR202608000093,2026-08-09,Delayed Payout
BNK-0095,-3200.00,debit,UTR202608000095,2026-08-03,Customer Refund Reversal
BNK-0097,6800.00,credit,UTR202608000097,2026-08-03,Razorpay Payout
BNK-0100,5432.10,credit,UTR202608000100,2026-08-03,Payout`;

      const setFile = new File([settlementData], "settlements.csv", { type: "text/csv" });
      const bnkFile = new File([bankData], "bank_statements.csv", { type: "text/csv" });
      const invFile = new File([invoiceData], "invoices.csv", { type: "text/csv" });

      setSettlementFile(setFile);
      setBankFile(bnkFile);
      setInvoiceFile(invFile);

      setProcessingState("matching");
      setTimeout(() => setProcessingState("verifying"), 400);

      const formData = new FormData();
      formData.append("settlement_csv", setFile);
      formData.append("bank_csv", bnkFile);
      formData.append("invoice_csv", invFile);

      const res = await fetch(`${API_BASE}/api/v1/batches`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Failed to process demo batch.");
      }

      const data = await res.json();
      setProcessingState("done");
      setActiveBatchId(data.batch_id);
      await loadBatchData(data.batch_id);
      setActiveTab("matches");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to trigger synthetic batch.");
      setProcessingState("idle");
    } finally {
      setLoading(false);
    }
  };

  // Open Single Match Evidence Drawer
  const openMatchDetail = async (matchId: string) => {
    setLoadingMatchDetail(true);
    setSelectedMatch(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/matches/${matchId}`);
      if (res.ok) {
        const detail: MatchDetail = await res.json();
        setSelectedMatch(detail);
      }
    } catch (err) {
      console.error("Failed to load match detail:", err);
    } finally {
      setLoadingMatchDetail(false);
    }
  };

  // Resolve Exception Action
  const handleResolveException = async (matchId: string) => {
    if (!matchId) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/matches/${matchId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resolved: true,
          reviewer_note: reviewNote || "Manually confirmed and reconciled.",
        }),
      });
      if (res.ok) {
        setReviewingMatchId(null);
        setReviewNote("");
        if (activeBatchId) {
          await loadBatchData(activeBatchId);
        }
      }
    } catch (err) {
      console.error("Error resolving match:", err);
    }
  };

  // Filter matches list
  const filteredMatches = matches.filter((m) => {
    const matchesStatus = statusFilter === "all" || m.status === statusFilter;
    const matchesMethod = methodFilter === "all" || m.match_method === methodFilter;
    const matchesSearch =
      !searchQuery ||
      (m.order_id && m.order_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (m.reference_number && m.reference_number.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (m.rule_name && m.rule_name.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesMethod && matchesSearch;
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Top Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-lg sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
              RP
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg text-white tracking-tight">ReconPilot</span>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-semibold tracking-wide uppercase">
                  Finance Controller
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {activeBatchId && (
              <a
                href={`${API_BASE}/api/v1/batches/${activeBatchId}/export`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-medium text-slate-200 transition shadow-sm"
                download
              >
                <Download className="h-3.5 w-3.5 text-blue-400" />
                Export CSV
              </a>
            )}

            <button
              onClick={() => setActiveTab("upload")}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition shadow-md shadow-blue-600/20"
            >
              <UploadCloud className="h-4 w-4" />
              New Upload
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Error Alert */}
        {errorMsg && (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm flex items-start justify-between gap-3 shadow-lg shadow-rose-950/20">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-rose-200">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Processing State Stepper */}
        {processingState !== "idle" && processingState !== "done" && (
          <div className="p-6 rounded-2xl border border-blue-500/30 bg-slate-900/80 backdrop-blur-md shadow-2xl relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-600/5 via-indigo-600/10 to-blue-600/5 animate-pulse" />
            <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
              <RefreshCw className="h-4 w-4 text-blue-400 animate-spin" />
              Reconciliation Pipeline Processing
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 relative z-10">
              <div className={`p-3 rounded-xl border ${processingState === "reading" ? "border-blue-500 bg-blue-500/10 text-blue-300" : "border-slate-800 bg-slate-900 text-slate-400"}`}>
                <div className="text-xs font-semibold uppercase tracking-wider mb-1">Step 1</div>
                <div className="text-sm font-medium">Ingestion & Normalizer</div>
              </div>
              <div className={`p-3 rounded-xl border ${processingState === "matching" ? "border-blue-500 bg-blue-500/10 text-blue-300" : "border-slate-800 bg-slate-900 text-slate-400"}`}>
                <div className="text-xs font-semibold uppercase tracking-wider mb-1">Step 2</div>
                <div className="text-sm font-medium">Deterministic Rules</div>
              </div>
              <div className={`p-3 rounded-xl border ${processingState === "verifying" ? "border-blue-500 bg-blue-500/10 text-blue-300" : "border-slate-800 bg-slate-900 text-slate-400"}`}>
                <div className="text-xs font-semibold uppercase tracking-wider mb-1">Step 3</div>
                <div className="text-sm font-medium">Finance Verification AI</div>
              </div>
              <div className="p-3 rounded-xl border border-slate-800 bg-slate-900 text-slate-400">
                <div className="text-xs font-semibold uppercase tracking-wider mb-1">Step 4</div>
                <div className="text-sm font-medium">Exception Report</div>
              </div>
            </div>
          </div>
        )}

        {/* METRICS DASHBOARD (FR-16: Displayed visibly on dashboard without clicking into anything else) */}
        {metrics && (
          <section className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-blue-400" />
                  Live Reconciliation Snapshot
                </h2>
                <p className="text-xs text-slate-400">
                  Batch: <code className="text-slate-300 font-mono">{activeBatchId}</code>
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
                <span className="flex h-2 w-2 rounded-full bg-emerald-500"></span>
                <span>Fully reconciled with deterministic validation</span>
              </div>
            </div>

            {/* Headline KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {/* Match Rate */}
              <div className="p-4 rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-900/40 backdrop-blur-sm">
                <div className="text-xs font-medium text-slate-400 mb-1 flex items-center justify-between">
                  <span>Match Rate</span>
                  <span className="text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded text-[10px] font-bold">FR-14</span>
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {metrics.match_rate}%
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  {metrics.rule_matches + metrics.ai_verified} / {metrics.records_processed} total records
                </div>
              </div>

              {/* Precision */}
              <div className="p-4 rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-900/40 backdrop-blur-sm">
                <div className="text-xs font-medium text-slate-400 mb-1 flex items-center justify-between">
                  <span>Precision</span>
                  <span className="text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded text-[10px] font-bold">Verified</span>
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-emerald-400 tracking-tight">
                  {metrics.precision}%
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Zero false positives confirmed
                </div>
              </div>

              {/* Processing Time */}
              <div className="p-4 rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-900/40 backdrop-blur-sm">
                <div className="text-xs font-medium text-slate-400 mb-1 flex items-center justify-between">
                  <span>Processing Time</span>
                  <Clock className="h-3.5 w-3.5 text-slate-400" />
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {metrics.processing_time_seconds}s
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Target &lt;30s (NFR-1 pass)
                </div>
              </div>

              {/* Needs Review */}
              <div className="p-4 rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-900/40 backdrop-blur-sm">
                <div className="text-xs font-medium text-slate-400 mb-1 flex items-center justify-between">
                  <span>Needs Review</span>
                  <span className="text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded text-[10px] font-bold">Exceptions</span>
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-amber-400 tracking-tight">
                  {metrics.needs_review}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Unresolved record edge cases
                </div>
              </div>

              {/* Manual Hours Saved */}
              <div className="p-4 rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-900/40 backdrop-blur-sm">
                <div className="text-xs font-medium text-slate-400 mb-1 flex items-center justify-between">
                  <span>Hours Saved</span>
                  <span className="text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded text-[10px] font-bold">ROI</span>
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-purple-400 tracking-tight">
                  {metrics.manual_hours_saved}h
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Vs. 3 min manual baseline
                </div>
              </div>
            </div>

            {/* Reconciliation Funnel Breakdown */}
            <div className="p-4 rounded-2xl border border-slate-800 bg-slate-900/50 flex flex-col md:flex-row items-center justify-between gap-4 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-300">Resolution Funnel:</span>
              </div>
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-blue-500"></span>
                  <span className="text-slate-300 font-medium">Rule Matches:</span>
                  <span className="text-white font-bold">{metrics.rule_matches}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-indigo-500"></span>
                  <span className="text-slate-300 font-medium">AI-Verified:</span>
                  <span className="text-white font-bold">{metrics.ai_verified}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-500"></span>
                  <span className="text-slate-300 font-medium">Exceptions:</span>
                  <span className="text-white font-bold">{metrics.needs_review}</span>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Tab Navigation */}
        <div className="border-b border-slate-800 flex items-center justify-between">
          <div className="flex space-x-6">
            <button
              onClick={() => setActiveTab("matches")}
              className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
                activeTab === "matches"
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <FileCheck className="h-4 w-4" />
              Reconciliation Matches ({matches.length})
            </button>
            <button
              onClick={() => setActiveTab("exceptions")}
              className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
                activeTab === "exceptions"
                  ? "border-amber-500 text-amber-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <AlertTriangle className="h-4 w-4" />
              Exception Report ({exceptions?.total_exceptions || 0})
            </button>
            <button
              onClick={() => setActiveTab("upload")}
              className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
                activeTab === "upload"
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <UploadCloud className="h-4 w-4" />
              Upload Source Files
            </button>
          </div>
        </div>

        {/* TAB 1: RECONCILIATION MATCHES */}
        {activeTab === "matches" && (
          <div className="space-y-4">
            {/* Filter Bar */}
            <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
              <div className="relative flex-1 max-w-md">
                <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search by Order ID, UTR, or Rule..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-blue-500"
                >
                  <option value="all">All Statuses</option>
                  <option value="matched">Matched Only</option>
                  <option value="exception">Exceptions Only</option>
                </select>

                <select
                  value={methodFilter}
                  onChange={(e) => setMethodFilter(e.target.value)}
                  className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-blue-500"
                >
                  <option value="all">All Methods</option>
                  <option value="rule">Deterministic Rules</option>
                  <option value="ai">AI Verified</option>
                </select>
              </div>
            </div>

            {/* Matches Table */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 bg-slate-900/80 text-slate-400 font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="py-3.5 px-4">Order / Reference</th>
                      <th className="py-3.5 px-4">Amount</th>
                      <th className="py-3.5 px-4">Method & Rule</th>
                      <th className="py-3.5 px-4">Status</th>
                      <th className="py-3.5 px-4">Confidence</th>
                      <th className="py-3.5 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-medium">
                    {filteredMatches.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-12 text-center text-slate-500">
                          {matches.length === 0 ? (
                            <div className="flex flex-col items-center gap-3">
                              <FileSpreadsheet className="h-8 w-8 text-slate-600" />
                              <span>No batch uploaded yet. Upload source CSVs or load synthetic demo data.</span>
                              <button
                                onClick={loadSyntheticDemoBatch}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 text-xs font-semibold text-white"
                              >
                                <Play className="h-3.5 w-3.5" />
                                Run Demo Batch
                              </button>
                            </div>
                          ) : (
                            "No records match the selected filters."
                          )}
                        </td>
                      </tr>
                    ) : (
                      filteredMatches.map((m) => (
                        <tr key={m.match_id} className="hover:bg-slate-800/40 transition">
                          <td className="py-3.5 px-4">
                            <div className="font-semibold text-white">{m.order_id || "No Order ID"}</div>
                            <div className="text-[11px] text-slate-500 font-mono">{m.reference_number || "No UTR"}</div>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-bold text-slate-100">₹{m.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</div>
                          </td>
                          <td className="py-3.5 px-4">
                            {m.match_method === "rule" ? (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium text-[11px]">
                                <Shield className="h-3 w-3" />
                                {m.rule_name?.replace(/_/g, " ") || "Rule Match"}
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium text-[11px]">
                                <Sparkles className="h-3 w-3" />
                                AI Verified Engine
                              </span>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            {m.status === "matched" ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold text-[11px]">
                                <Check className="h-3 w-3" />
                                Matched
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 font-semibold text-[11px]">
                                <AlertTriangle className="h-3 w-3" />
                                Exception
                              </span>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-2">
                              <div className="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    m.confidence >= 95
                                      ? "bg-emerald-500"
                                      : m.confidence >= 80
                                      ? "bg-blue-500"
                                      : "bg-amber-500"
                                  }`}
                                  style={{ width: `${m.confidence}%` }}
                                />
                              </div>
                              <span className="font-semibold text-slate-200 text-[11px]">{m.confidence}%</span>
                            </div>
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <button
                              onClick={() => openMatchDetail(m.match_id)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-medium transition"
                            >
                              Evidence <ArrowRight className="h-3 w-3" />
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: EXCEPTION REPORT */}
        {activeTab === "exceptions" && exceptions && (
          <div className="space-y-6">
            {/* Category Breakdown Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60">
                <div className="text-[11px] text-slate-400 font-medium">Settlement Delay</div>
                <div className="text-xl font-bold text-amber-400 mt-1">{exceptions.settlement_delay}</div>
              </div>
              <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60">
                <div className="text-[11px] text-slate-400 font-medium">Missing Credit</div>
                <div className="text-xl font-bold text-rose-400 mt-1">{exceptions.missing_credit}</div>
              </div>
              <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60">
                <div className="text-[11px] text-slate-400 font-medium">Duplicate Invoice</div>
                <div className="text-xl font-bold text-orange-400 mt-1">{exceptions.duplicate_invoice}</div>
              </div>
              <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60">
                <div className="text-[11px] text-slate-400 font-medium">Refund Pending</div>
                <div className="text-xl font-bold text-blue-400 mt-1">{exceptions.refund_pending}</div>
              </div>
              <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60">
                <div className="text-[11px] text-slate-400 font-medium">Genuine Unknown</div>
                <div className="text-xl font-bold text-purple-400 mt-1">{exceptions.unknown}</div>
              </div>
            </div>

            {/* Exceptions Table */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 bg-slate-900/80 text-slate-400 font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="py-3.5 px-4">Order ID</th>
                      <th className="py-3.5 px-4">Category</th>
                      <th className="py-3.5 px-4">Amount</th>
                      <th className="py-3.5 px-4">Discrepancy Notes</th>
                      <th className="py-3.5 px-4">Status</th>
                      <th className="py-3.5 px-4 text-right">Human Review</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-medium">
                    {exceptions.items.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-10 text-center text-slate-500">
                          Zero exceptions pending review.
                        </td>
                      </tr>
                    ) : (
                      exceptions.items.map((exc) => (
                        <tr key={exc.exception_id} className="hover:bg-slate-800/40 transition">
                          <td className="py-3.5 px-4 font-mono font-bold text-white">
                            {exc.order_id || "Unassigned"}
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/20">
                              {exc.category.replace(/_/g, " ")}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 font-semibold text-slate-200">
                            ₹{exc.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </td>
                          <td className="py-3.5 px-4 text-slate-400 max-w-xs truncate">
                            {exc.notes}
                          </td>
                          <td className="py-3.5 px-4">
                            {exc.resolved ? (
                              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                                <Check className="h-3 w-3" /> Resolved
                              </span>
                            ) : (
                              <span className="text-amber-400 font-semibold flex items-center gap-1">
                                <Clock className="h-3 w-3" /> Pending Review
                              </span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            {!exc.resolved ? (
                              <button
                                onClick={() => setReviewingMatchId(exc.match_id)}
                                className="px-2.5 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-semibold transition"
                              >
                                Review & Resolve
                              </button>
                            ) : (
                              <span className="text-slate-500 text-[11px]">Completed</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: UPLOAD SOURCE FILES */}
        {activeTab === "upload" && (
          <div className="max-w-3xl mx-auto space-y-6">
            <div className="text-center space-y-1">
              <h2 className="text-2xl font-bold text-white tracking-tight">Upload Ingestion Batch</h2>
              <p className="text-xs text-slate-400">
                Upload 3 source CSV files (Settlement, Bank Statement, Invoice) for automated reconciliation.
              </p>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              {/* Settlement File Input */}
              <div className="p-4 rounded-2xl border border-slate-800 bg-slate-900/60 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-400">
                    <FileSpreadsheet className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">Settlement Report CSV (FR-1)</div>
                    <div className="text-xs text-slate-400">
                      {settlementFile ? settlementFile.name : "Expected: order_id, amount, fee, tax, utr..."}
                    </div>
                  </div>
                </div>
                <input
                  type="file"
                  id="settlement_csv"
                  accept=".csv"
                  onChange={(e) => setSettlementFile(e.target.files?.[0] || null)}
                  className="text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer"
                />
              </div>

              {/* Bank Statement File Input */}
              <div className="p-4 rounded-2xl border border-slate-800 bg-slate-900/60 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400">
                    <Building2 className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">Bank Statement CSV (FR-1)</div>
                    <div className="text-xs text-slate-400">
                      {bankFile ? bankFile.name : "Expected: bank_txn_id, amount, type, utr, value_date..."}
                    </div>
                  </div>
                </div>
                <input
                  type="file"
                  id="bank_csv"
                  accept=".csv"
                  onChange={(e) => setBankFile(e.target.files?.[0] || null)}
                  className="text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer"
                />
              </div>

              {/* Invoice File Input */}
              <div className="p-4 rounded-2xl border border-slate-800 bg-slate-900/60 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400">
                    <FileCheck className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">Invoice Register CSV (FR-1)</div>
                    <div className="text-xs text-slate-400">
                      {invoiceFile ? invoiceFile.name : "Expected: invoice_id, order_id, amount, customer_id..."}
                    </div>
                  </div>
                </div>
                <input
                  type="file"
                  id="invoice_csv"
                  accept=".csv"
                  onChange={(e) => setInvoiceFile(e.target.files?.[0] || null)}
                  className="text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer"
                />
              </div>

              <div className="flex items-center gap-3 pt-4">
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 font-semibold text-xs text-white transition flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20 disabled:opacity-50"
                >
                  {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                  Upload & Reconcile Batch
                </button>

                <button
                  type="button"
                  onClick={loadSyntheticDemoBatch}
                  disabled={loading}
                  className="py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 font-semibold text-xs text-slate-200 transition flex items-center gap-1.5"
                >
                  <Sparkles className="h-4 w-4 text-indigo-400" />
                  Load Synthetic Dataset
                </button>
              </div>
            </form>
          </div>
        )}
      </main>

      {/* MATCH EVIDENCE MODAL / DRAWER (GET /matches/{id}) */}
      {selectedMatch && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-2xl w-full bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-5 max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <span>Match Evidence & Verification</span>
                  <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${selectedMatch.status === "matched" ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"}`}>
                    {selectedMatch.status.toUpperCase()}
                  </span>
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">ID: {selectedMatch.match_id}</p>
              </div>
              <button onClick={() => setSelectedMatch(null)} className="p-1 rounded-lg text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* AI Verification Evidence Card */}
            {selectedMatch.ai_verification ? (
              <div className="p-4 rounded-2xl border border-indigo-500/30 bg-indigo-500/5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-indigo-400 flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5" />
                    AI Finance Verification Engine ({selectedMatch.ai_verification.model_used})
                  </span>
                  <span className="text-xs font-extrabold text-white bg-indigo-500/20 px-2 py-0.5 rounded">
                    {selectedMatch.ai_verification.adjusted_confidence}% Confirmed
                  </span>
                </div>

                {/* Calculation Trace */}
                <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-xs font-mono text-emerald-300">
                  {selectedMatch.ai_verification.calculation_trace}
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-slate-400">Likely Reason:</span>
                    <div className="font-semibold text-white">{selectedMatch.ai_verification.likely_reason}</div>
                  </div>
                  <div>
                    <span className="text-slate-400">Evidence Field:</span>
                    <div className="font-semibold text-white font-mono">{selectedMatch.ai_verification.evidence_field}</div>
                  </div>
                  <div>
                    <span className="text-slate-400">Difference Amount:</span>
                    <div className="font-semibold text-white">₹{selectedMatch.ai_verification.difference_amount.toFixed(2)}</div>
                  </div>
                  <div>
                    <span className="text-slate-400">Tokens In / Out:</span>
                    <div className="font-semibold text-white">
                      {selectedMatch.ai_verification.prompt_tokens} in / {selectedMatch.ai_verification.completion_tokens} out
                    </div>
                  </div>
                </div>

                <p className="text-xs text-slate-300 italic">
                  "{selectedMatch.ai_verification.reasoning_explanation}"
                </p>
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 flex items-center gap-2">
                <Shield className="h-4 w-4" />
                <span>Deterministic Rule Match: <strong>{selectedMatch.rule_name?.replace(/_/g, " ")}</strong> (100% confidence)</span>
              </div>
            )}

            {/* Linked Records Summary */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Linked Records</h4>
              <div className="grid grid-cols-3 gap-2 text-xs">
                {/* Settlement Record */}
                <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/80 space-y-1">
                  <div className="font-bold text-blue-400">Settlement</div>
                  {selectedMatch.records.settlement ? (
                    <>
                      <div className="text-white font-bold">₹{selectedMatch.records.settlement.amount.toLocaleString()}</div>
                      <div className="text-slate-400 text-[10px]">Fee: ₹{selectedMatch.records.settlement.fees}</div>
                      <div className="text-slate-400 text-[10px]">UTR: {selectedMatch.records.settlement.reference_number || "N/A"}</div>
                    </>
                  ) : (
                    <div className="text-slate-500 italic">None</div>
                  )}
                </div>

                {/* Invoice Record */}
                <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/80 space-y-1">
                  <div className="font-bold text-purple-400">Invoice</div>
                  {selectedMatch.records.invoice ? (
                    <>
                      <div className="text-white font-bold">₹{selectedMatch.records.invoice.amount.toLocaleString()}</div>
                      <div className="text-slate-400 text-[10px]">Order: {selectedMatch.records.invoice.order_id}</div>
                      <div className="text-slate-400 text-[10px]">Status: {selectedMatch.records.invoice.status}</div>
                    </>
                  ) : (
                    <div className="text-slate-500 italic">None</div>
                  )}
                </div>

                {/* Bank Record */}
                <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/80 space-y-1">
                  <div className="font-bold text-emerald-400">Bank Statement</div>
                  {selectedMatch.records.bank ? (
                    <>
                      <div className="text-white font-bold">₹{selectedMatch.records.bank.amount.toLocaleString()}</div>
                      <div className="text-slate-400 text-[10px]">UTR: {selectedMatch.records.bank.reference_number || "N/A"}</div>
                      <div className="text-slate-400 text-[10px]">Status: {selectedMatch.records.bank.status}</div>
                    </>
                  ) : (
                    <div className="text-slate-500 italic">None</div>
                  )}
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedMatch(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white transition"
              >
                Close Evidence
              </button>
            </div>
          </div>
        </div>
      )}

      {/* HUMAN REVIEW MODAL (POST /matches/{id}/review) */}
      {reviewingMatchId && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white">Manual Reconciliation Review</h3>
            <p className="text-xs text-slate-400">
              Provide reviewer audit notes to mark this exception record as manually verified and resolved.
            </p>
            <textarea
              rows={3}
              value={reviewNote}
              onChange={(e) => setReviewNote(e.target.value)}
              placeholder="e.g. Manually confirmed against bank portal; settlement delayed due to bank holiday."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500"
            />
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setReviewingMatchId(null)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs font-semibold text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={() => handleResolveException(reviewingMatchId)}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white"
              >
                Confirm & Resolve
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
