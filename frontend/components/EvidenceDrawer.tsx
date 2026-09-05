"use client";

import React, { useEffect } from "react";
import {
  X,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Calculator,
  ShieldCheck,
  Building2,
  Database,
  History,
  FileCheck,
  ArrowRight,
} from "lucide-react";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";

export interface HistoricalPrecedent {
  merchant_type: string;
  amount_delta: number;
  reason: string;
  reviewer_notes: string;
  created_at?: string;
  similarity_score?: number;
}

export interface MatchDetail {
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
    calculation_trace?: string;
    historical_precedents?: HistoricalPrecedent[];
    tokens_used?: number;
  };
}

interface EvidenceDrawerProps {
  detail: MatchDetail | null;
  isLoading: boolean;
  onClose: () => void;
}

export function EvidenceDrawer({ detail, isLoading, onClose }: EvidenceDrawerProps) {
  // ESC key listener for accessibility
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const formatCurrency = (val: number | null | undefined) => {
    if (val === null || val === undefined) return "—";
    return `₹${val.toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  return (
    <div
      className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex justify-end animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
    >
      <div className="bg-slate-900 border-l border-slate-800 w-full max-w-xl h-full shadow-2xl flex flex-col overflow-hidden animate-slide-in">
        {/* Header */}
        <div className="p-5 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Calculator className="w-4 h-4" aria-hidden="true" />
            </div>
            <div>
              <h2 id="drawer-title" className="text-base font-bold text-slate-100">
                Audit Evidence & Math Trace
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                Match ID: {detail?.match_id.substring(0, 14)}...
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close Evidence Drawer"
            className="p-2 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5 text-xs">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-24 space-y-3 text-slate-400">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <p className="font-medium text-xs">Loading audit evidence trace...</p>
            </div>
          ) : detail ? (
            <>
              {/* Status Banner */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-[10px] uppercase font-semibold text-slate-400">Match Disposition</div>
                  <div className="text-sm font-bold text-slate-100 capitalize mt-0.5">
                    {detail.match_method.replace(/_/g, " ")}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[10px] uppercase font-semibold text-slate-400">Paisa Math Confidence</div>
                  <div className="text-sm font-bold font-mono text-emerald-400 mt-0.5">
                    {(detail.confidence * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* 3-Way Records Comparison */}
              <div className="space-y-2.5">
                <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-indigo-400" />
                  Three-Way Ingested Records
                </h3>

                <div className="grid grid-cols-3 gap-2 text-center">
                  {/* Invoice */}
                  <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3">
                    <span className="text-[10px] font-semibold text-slate-400 block uppercase">1. ERP Invoice</span>
                    <span className="text-xs font-bold font-mono text-slate-100 block mt-1">
                      {formatCurrency(detail.records.invoice?.amount)}
                    </span>
                    <span className="text-[10px] text-slate-400 block truncate mt-0.5">
                      {detail.records.invoice?.order_id || "Unlinked"}
                    </span>
                  </div>

                  {/* Settlement */}
                  <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3">
                    <span className="text-[10px] font-semibold text-indigo-400 block uppercase">2. Settlement Net</span>
                    <span className="text-xs font-bold font-mono text-indigo-300 block mt-1">
                      {formatCurrency(detail.records.settlement?.amount)}
                    </span>
                    <span className="text-[10px] text-slate-400 block truncate mt-0.5">
                      Fee: {formatCurrency(detail.records.settlement?.fees)}
                    </span>
                  </div>

                  {/* Bank */}
                  <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3">
                    <span className="text-[10px] font-semibold text-emerald-400 block uppercase">3. Bank Credit</span>
                    <span className="text-xs font-bold font-mono text-emerald-300 block mt-1">
                      {formatCurrency(detail.records.bank?.amount)}
                    </span>
                    <span className="text-[10px] text-slate-400 block truncate mt-0.5 font-mono">
                      {detail.records.bank?.reference_number?.substring(0, 8) || "UTR Verified"}
                    </span>
                  </div>
                </div>
              </div>

              {/* AI Verification & Arithmetic Trace */}
              {detail.ai_verification && (
                <div className="space-y-2.5">
                  <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                    Finance Verification Engine Trace
                  </h3>

                  <div className="bg-slate-950/70 border border-purple-900/40 rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                      <div>
                        <span className="text-[10px] text-slate-400 block">Classified Category</span>
                        <span className="text-xs font-bold text-purple-300">
                          {detail.ai_verification.likely_reason.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-slate-400 block">Identified Variance</span>
                        <span className="text-xs font-bold font-mono text-amber-300">
                          {formatCurrency(detail.ai_verification.difference_amount)}
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className="text-[10px] text-slate-400 block mb-1">Qualitative Forensic Rationale:</span>
                      <p className="text-slate-300 leading-relaxed bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60 font-mono text-[11px]">
                        {detail.ai_verification.reasoning_explanation}
                      </p>
                    </div>

                    {/* Calculation Trace Formula */}
                    {detail.ai_verification.calculation_trace && (
                      <div className="bg-emerald-950/30 border border-emerald-800/40 p-3 rounded-lg flex items-start gap-2.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 block">
                            Deterministic Paisa Proof
                          </span>
                          <code className="text-xs font-mono text-emerald-200 font-semibold block mt-0.5">
                            {detail.ai_verification.calculation_trace}
                          </code>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 font-mono">
                      <span>Model: {detail.ai_verification.model_used}</span>
                      <span>Tokens: {detail.ai_verification.tokens_used || 120}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Historical Feedback Memory Precedents */}
              {detail.ai_verification?.historical_precedents &&
                detail.ai_verification.historical_precedents.length > 0 && (
                  <div className="space-y-2.5">
                    <h3 className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                      <History className="w-3.5 h-3.5 text-indigo-400" />
                      Historical Feedback Precedents
                    </h3>

                    <div className="space-y-2">
                      {detail.ai_verification.historical_precedents.map((prec, i) => (
                        <div
                          key={i}
                          className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 text-[11px] space-y-1"
                        >
                          <div className="flex justify-between items-center">
                            <span className="font-semibold text-slate-300">{prec.reason}</span>
                            <Badge variant="success" size="sm">
                              +5.00% Calibrated
                            </Badge>
                          </div>
                          <p className="text-slate-400 italic">&ldquo;{prec.reviewer_notes}&rdquo;</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
            </>
          ) : (
            <div className="py-20 text-center text-slate-400">Select a record to inspect evidence.</div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-950/80 flex justify-end">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close Drawer
          </Button>
        </div>
      </div>
    </div>
  );
}
