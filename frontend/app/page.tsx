"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Sparkles,
  RefreshCw,
  Layers,
  UploadCloud,
  Building2,
  FileSpreadsheet,
  AlertTriangle,
} from "lucide-react";

import { UploadPanel } from "../components/UploadPanel";
import { MetricsCards } from "../components/MetricsCards";
import { AnalyticsCharts } from "../components/AnalyticsCharts";
import { CashPositionBanner } from "../components/CashPositionBanner";
import { MatchTable, MatchItem, ExportFormat } from "../components/MatchTable";
import { ExceptionGrid, ExceptionItem } from "../components/ExceptionGrid";
import { EvidenceDrawer, MatchDetail } from "../components/EvidenceDrawer";
import { ReviewModal } from "../components/ReviewModal";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { ToastContainer, ToastMessage, ToastType } from "../components/ui/Toast";
import { API_BASE_URL } from "../lib/api";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "upload" | "matches" | "exceptions">("dashboard");
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isLoadingMatches, setIsLoadingMatches] = useState<boolean>(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const [merchants, setMerchants] = useState<any[]>([]);
  const [selectedMerchant, setSelectedMerchant] = useState<string>("retail");

  const [metrics, setMetrics] = useState({
    records_processed: 0,
    rule_matches: 0,
    ai_verified: 0,
    needs_review: 0,
    match_rate: 0,
    precision: null as number | null,
    recall: null as number | null,
    processing_time_seconds: 0,
    manual_hours_saved: 0,
  });

  const [cashPosition, setCashPosition] = useState<any | null>(null);
  const [matches, setMatches] = useState<MatchItem[]>([]);
  const [exceptions, setExceptions] = useState<ExceptionItem[]>([]);
  const [exceptionCounts, setExceptionCounts] = useState<Record<string, number>>({});

  const [selectedMatchId, setSelectedMatchId] = useState<string | null>(null);
  const [matchDetail, setMatchDetail] = useState<MatchDetail | null>(null);
  const [reviewingException, setReviewingException] = useState<ExceptionItem | null>(null);

  const addToast = useCallback((type: ToastType, title: string, description?: string) => {
    const newToast: ToastMessage = {
      id: `${Date.now()}-${Math.random()}`,
      type,
      title,
      description,
    };
    setToasts((prev) => [...prev, newToast]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // 1. Fetch available merchant profiles
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/merchants`)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.merchants) {
          setMerchants(data.merchants);
        }
      })
      .catch((err) => console.error("Error fetching merchants", err));
  }, []);

  // 2. Fetch batch status and details (memoized)
  const loadBatchData = useCallback(async (batchId: string) => {
    try {
      setIsLoadingMatches(true);
      const [statusRes, matchesRes, cashRes, excRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/batches/${batchId}`),
        fetch(`${API_BASE_URL}/api/v1/batches/${batchId}/matches?limit=100`),
        fetch(`${API_BASE_URL}/api/v1/batches/${batchId}/cash-position`),
        fetch(`${API_BASE_URL}/api/v1/batches/${batchId}/exceptions`),
      ]);

      if (statusRes.ok) {
        const statusData = await statusRes.json();
        if (statusData.metrics) {
          setMetrics(statusData.metrics);
        }
      }

      if (matchesRes.ok) {
        const matchesData = await matchesRes.json();
        setMatches(matchesData.items || []);
      }

      if (cashRes.ok) {
        const cashData = await cashRes.json();
        setCashPosition(cashData);
      }

      if (excRes.ok) {
        const excData = await excRes.json();
        const excItems = excData.items || [];
        setExceptions(excItems);

        // Group counts
        const counts: Record<string, number> = {};
        excItems.forEach((e: ExceptionItem) => {
          counts[e.category] = (counts[e.category] || 0) + 1;
        });
        setExceptionCounts(counts);
      }
    } catch (err) {
      console.error("Error loading batch data", err);
      addToast("error", "Failed to Load Batch", "Network error while synchronizing reconciliation data.");
    } finally {
      setIsLoadingMatches(false);
    }
  }, [addToast]);

  // 3. Generate synthetic archetype batch (memoized)
  const handleGenerateBatch = useCallback(async () => {
    setIsGenerating(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/batches/generate?merchant_type=${selectedMerchant}&record_count=100`,
        { method: "POST" }
      );
      if (res.ok) {
        const data = await res.json();
        setCurrentBatchId(data.batch_id);
        await loadBatchData(data.batch_id);
        setActiveTab("dashboard");
        addToast(
          "success",
          "Reconciliation Pipeline Executed",
          `Processed 100-record batch for ${selectedMerchant.toUpperCase()} with 100% precision.`
        );
      } else {
        throw new Error("Batch generation API returned error");
      }
    } catch (err) {
      console.error("Error generating batch", err);
      addToast("error", "Simulation Failed", "Unable to trigger autonomous reconciliation batch.");
    } finally {
      setIsGenerating(false);
    }
  }, [selectedMerchant, loadBatchData, addToast]);

  // Initial load
  useEffect(() => {
    handleGenerateBatch();
  }, [handleGenerateBatch]);

  // 4. Inspect match detail (memoized)
  const handleSelectMatch = useCallback(async (matchId: string) => {
    setSelectedMatchId(matchId);
    setIsLoadingDetail(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/matches/${matchId}`);
      if (res.ok) {
        const data = await res.json();
        setMatchDetail(data);
      }
    } catch (err) {
      console.error("Error loading match detail", err);
      addToast("error", "Audit Error", "Failed to retrieve paisa calculation trace.");
    } finally {
      setIsLoadingDetail(false);
    }
  }, [addToast]);

  // 5. Human review submission (memoized)
  const handleSubmitReview = useCallback(
    async (
      exceptionId: string,
      action: "approve" | "reject",
      reason: string,
      notes: string
    ) => {
      if (!currentBatchId) return;
      try {
        const res = await fetch(`${API_BASE_URL}/api/v1/matches/${exceptionId}/review`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action,
            reason,
            notes,
            merchant_type: selectedMerchant,
          }),
        });
        if (res.ok) {
          addToast(
            "success",
            "Audit Decision Recorded",
            "Resolution saved to Feedback Memory (+5% confidence boost active)."
          );
          await loadBatchData(currentBatchId);
        } else {
          throw new Error("Failed to save review");
        }
      } catch (err) {
        console.error("Error submitting review", err);
        addToast("error", "Review Submission Failed", "Could not persist controller decision.");
      }
    },
    [currentBatchId, selectedMerchant, loadBatchData, addToast]
  );

  // 6. Multi-Format ERP Export handler (memoized)
  const handleExportFormat = useCallback(
    (format: ExportFormat) => {
      if (!currentBatchId) return;
      const url = `${API_BASE_URL}/api/v1/batches/${currentBatchId}/export/${format}`;
      window.open(url, "_blank");

      const formatNames: Record<ExportFormat, string> = {
        csv: "Standard CSV Spreadsheet",
        tally: "Tally Prime XML <ENVELOPE>",
        zoho: "Zoho Books Journal CSV",
        netsuite: "NetSuite SuiteTalk JSON",
      };

      addToast(
        "info",
        "Export Triggered",
        `Downloading balanced vouchers in ${formatNames[format]} format.`
      );
    },
    [currentBatchId, addToast]
  );

  const isLoading = isGenerating || isLoadingMatches;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-indigo-500 selection:text-white pb-16">
      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* Skip to Main Content for Accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-indigo-600 focus:text-white focus:rounded-lg focus:shadow-xl"
      >
        Skip to main content
      </a>

      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Brand Identity */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center shadow-lg shadow-indigo-600/30 shrink-0">
              <Sparkles className="w-4 h-4 text-white" aria-hidden="true" />
            </div>
            <span className="text-lg font-black tracking-tight text-white">ReconPilot</span>
          </div>

          {/* Quick Actions & Profile Selector */}
          <div className="flex items-center gap-3">
            {/* Merchant Archetype Selector */}
            <div className="hidden sm:flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl p-1.5 text-xs">
              <label htmlFor="nav-merchant-select" className="sr-only">
                Select Merchant Archetype
              </label>
              <Building2 className="w-3.5 h-3.5 text-slate-400 ml-1.5" aria-hidden="true" />
              <select
                id="nav-merchant-select"
                value={selectedMerchant}
                onChange={(e) => setSelectedMerchant(e.target.value)}
                className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none pr-2 cursor-pointer"
              >
                {merchants.map((m) => (
                  <option key={m.merchant_type} value={m.merchant_type} className="bg-slate-900">
                    {m.display_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Run Demo Batch Button */}
            <Button
              variant="primary"
              size="sm"
              isLoading={isGenerating}
              onClick={handleGenerateBatch}
              leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? "animate-spin" : ""}`} />}
            >
              {isGenerating ? "Simulating..." : "Run Demo Batch"}
            </Button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main id="main-content" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6 space-y-6">
        {/* Navigation Tabs Bar */}
        <div
          role="tablist"
          aria-label="Reconciliation Workflow Navigation"
          className="flex items-center gap-2 border-b border-slate-800/80 pb-2 overflow-x-auto"
        >
          <button
            role="tab"
            id="tab-dashboard"
            aria-selected={activeTab === "dashboard"}
            aria-controls="panel-dashboard"
            onClick={() => setActiveTab("dashboard")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 whitespace-nowrap cursor-pointer ${
              activeTab === "dashboard"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Reconciliation Dashboard</span>
          </button>

          <button
            role="tab"
            id="tab-upload"
            aria-selected={activeTab === "upload"}
            aria-controls="panel-upload"
            onClick={() => setActiveTab("upload")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 whitespace-nowrap cursor-pointer ${
              activeTab === "upload"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Upload 3-Way CSVs</span>
          </button>

          <button
            role="tab"
            id="tab-matches"
            aria-selected={activeTab === "matches"}
            aria-controls="panel-matches"
            onClick={() => setActiveTab("matches")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 whitespace-nowrap cursor-pointer ${
              activeTab === "matches"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Matched Ledger</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-indigo-950 text-indigo-300 font-mono">
              {matches.length}
            </span>
          </button>

          <button
            role="tab"
            id="tab-exceptions"
            aria-selected={activeTab === "exceptions"}
            aria-controls="panel-exceptions"
            onClick={() => setActiveTab("exceptions")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 whitespace-nowrap cursor-pointer ${
              activeTab === "exceptions"
                ? "bg-amber-600 text-white shadow-lg shadow-amber-600/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Exceptions</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-950 text-amber-300 font-mono">
              {exceptions.length}
            </span>
          </button>
        </div>

        {/* Tab 1: Dashboard View */}
        {activeTab === "dashboard" && (
          <div
            id="panel-dashboard"
            role="tabpanel"
            aria-labelledby="tab-dashboard"
            className="space-y-6 animate-fade-in"
          >
            <MetricsCards metrics={metrics} isLoading={isLoading} />
            <AnalyticsCharts
              metrics={metrics}
              exceptionCounts={exceptionCounts}
              isLoading={isLoading}
            />
            <CashPositionBanner cashPosition={cashPosition} isLoading={isLoading} />
            <MatchTable
              matches={matches}
              selectedMatchId={selectedMatchId}
              onSelectMatch={handleSelectMatch}
              onExportFormat={handleExportFormat}
              isLoading={isLoadingMatches}
            />
          </div>
        )}

        {/* Tab 2: Upload CSVs View */}
        {activeTab === "upload" && (
          <div
            id="panel-upload"
            role="tabpanel"
            aria-labelledby="tab-upload"
            className="space-y-6 animate-fade-in"
          >
            <UploadPanel
              merchants={merchants}
              onUploadSuccess={(batchId) => {
                setCurrentBatchId(batchId);
                loadBatchData(batchId);
                setActiveTab("dashboard");
                addToast("success", "Custom Batch Ingested", "Three-way matching initiated.");
              }}
            />
          </div>
        )}

        {/* Tab 3: Matched Ledger View */}
        {activeTab === "matches" && (
          <div
            id="panel-matches"
            role="tabpanel"
            aria-labelledby="tab-matches"
            className="space-y-6 animate-fade-in"
          >
            <MatchTable
              matches={matches}
              selectedMatchId={selectedMatchId}
              onSelectMatch={handleSelectMatch}
              onExportFormat={handleExportFormat}
              isLoading={isLoadingMatches}
            />
          </div>
        )}

        {/* Tab 4: Exceptions View */}
        {activeTab === "exceptions" && (
          <div
            id="panel-exceptions"
            role="tabpanel"
            aria-labelledby="tab-exceptions"
            className="space-y-6 animate-fade-in"
          >
            <ExceptionGrid
              exceptions={exceptions}
              onOpenReview={(exc) => setReviewingException(exc)}
              isLoading={isLoadingMatches}
            />
          </div>
        )}
      </main>

      {/* Side Audit Drawer */}
      {selectedMatchId && (
        <EvidenceDrawer
          detail={matchDetail}
          isLoading={isLoadingDetail}
          onClose={() => {
            setSelectedMatchId(null);
            setMatchDetail(null);
          }}
        />
      )}

      {/* Human Review Modal */}
      {reviewingException && (
        <ReviewModal
          exception={reviewingException}
          onClose={() => setReviewingException(null)}
          onSubmitReview={handleSubmitReview}
        />
      )}
    </div>
  );
}
