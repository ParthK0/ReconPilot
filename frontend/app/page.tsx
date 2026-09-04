"use client";

import React, { useState, useEffect } from "react";
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
import { MatchTable, MatchItem } from "../components/MatchTable";
import { ExceptionGrid, ExceptionItem } from "../components/ExceptionGrid";
import { EvidenceDrawer, MatchDetail } from "../components/EvidenceDrawer";
import { ReviewModal } from "../components/ReviewModal";
import { API_BASE_URL } from "../lib/api";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "upload" | "matches" | "exceptions">("dashboard");
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isLoadingMatches, setIsLoadingMatches] = useState<boolean>(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);

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

  // 2. Fetch batch status and details
  const loadBatchData = async (batchId: string) => {
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
    } finally {
      setIsLoadingMatches(false);
    }
  };

  // 3. Generate synthetic archetype batch
  const handleGenerateBatch = async () => {
    setIsGenerating(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/batches/generate?merchant_type=${selectedMerchant}&record_count=100`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentBatchId(data.batch_id);
        await loadBatchData(data.batch_id);
        setActiveTab("dashboard");
      }
    } catch (err) {
      console.error("Error generating batch", err);
    } finally {
      setIsGenerating(false);
    }
  };

  // 4. Initial load demo batch
  useEffect(() => {
    handleGenerateBatch();
  }, []);

  // 5. Inspect match detail
  const handleSelectMatch = async (matchId: string) => {
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
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // 6. Human review submission
  const handleSubmitReview = async (
    exceptionId: string,
    action: "approve" | "reject",
    reason: string,
    notes: string
  ) => {
    if (!currentBatchId) return;
    try {
      await fetch(`${API_BASE_URL}/api/v1/matches/${exceptionId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          reason,
          notes,
          merchant_type: selectedMerchant,
        }),
      });
      await loadBatchData(currentBatchId);
    } catch (err) {
      console.error("Error submitting review", err);
    }
  };

  const handleExportCsv = () => {
    if (!currentBatchId) return;
    window.open(`${API_BASE_URL}/api/v1/batches/${currentBatchId}/export/csv`, "_blank");
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 selection:bg-indigo-500 selection:text-white pb-16">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center shadow-lg shadow-indigo-600/30">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-black tracking-tight text-white">ReconPilot</h1>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-400 border border-indigo-800/40">
                  Track 04: AI Finance Controller
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Deterministic Rules &bull; Math-Proven AI &bull; Honest Exceptions
              </p>
            </div>
          </div>

          {/* Quick Actions & Vertical Selector */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg p-1">
              <Building2 className="w-3.5 h-3.5 text-slate-400 ml-2" />
              <select
                value={selectedMerchant}
                onChange={(e) => setSelectedMerchant(e.target.value)}
                className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none pr-2"
              >
                {merchants.map((m) => (
                  <option key={m.merchant_type} value={m.merchant_type} className="bg-slate-900">
                    {m.display_name}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleGenerateBatch}
              disabled={isGenerating}
              className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-md shadow-indigo-600/20 transition-all flex items-center gap-2"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? "animate-spin" : ""}`} />
              <span>{isGenerating ? "Simulating..." : "Run Demo Batch"}</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6 space-y-6">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-800/80 pb-2">
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === "dashboard"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Reconciliation Dashboard</span>
          </button>

          <button
            onClick={() => setActiveTab("upload")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === "upload"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Upload 3-Way CSVs</span>
          </button>

          <button
            onClick={() => setActiveTab("matches")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === "matches"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Matched Ledger ({matches.length})</span>
          </button>

          <button
            onClick={() => setActiveTab("exceptions")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeTab === "exceptions"
                ? "bg-amber-600 text-white shadow-lg shadow-amber-600/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Exceptions ({exceptions.length})</span>
          </button>
        </div>

        {/* Tab 1: Dashboard View */}
        {activeTab === "dashboard" && (
          <div className="space-y-6">
            <MetricsCards metrics={metrics} />
            <AnalyticsCharts metrics={metrics} exceptionCounts={exceptionCounts} />
            <CashPositionBanner cashPosition={cashPosition} />
            <MatchTable
              matches={matches}
              selectedMatchId={selectedMatchId}
              onSelectMatch={handleSelectMatch}
              onExportCsv={handleExportCsv}
            />
          </div>
        )}

        {/* Tab 2: Upload CSVs View */}
        {activeTab === "upload" && (
          <div className="space-y-6">
            <UploadPanel
              merchants={merchants}
              onUploadSuccess={(batchId) => {
                setCurrentBatchId(batchId);
                loadBatchData(batchId);
                setActiveTab("dashboard");
              }}
            />
          </div>
        )}

        {/* Tab 3: Matched Ledger View */}
        {activeTab === "matches" && (
          <div className="space-y-6">
            <MatchTable
              matches={matches}
              selectedMatchId={selectedMatchId}
              onSelectMatch={handleSelectMatch}
              onExportCsv={handleExportCsv}
            />
          </div>
        )}

        {/* Tab 4: Exceptions View */}
        {activeTab === "exceptions" && (
          <div className="space-y-6">
            <ExceptionGrid
              exceptions={exceptions}
              onOpenReview={(exc) => setReviewingException(exc)}
            />
          </div>
        )}
      </div>

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
    </main>
  );
}
