"use client";

import React from "react";
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
} from "lucide-react";

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
    calculation_trace: string;
    supporting_rules?: string[];
    similar_past_cases?: HistoricalPrecedent[];
    prompt_tokens: number;
    completion_tokens: number;
  };
}

interface EvidenceDrawerProps {
  detail: MatchDetail | null;
  isLoading: boolean;
  onClose: () => void;
}

export function EvidenceDrawer({ detail, isLoading, onClose }: EvidenceDrawerProps) {
  if (!detail && !isLoading) return null;

  const formatCurrency = (val: number | null | undefined) => {
    if (val === null || val === undefined) return "-";
    return `₹${val.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="fixed inset-y-0 right-0 w-full md:w-[540px] bg-slate-950/95 border-l border-slate-800 shadow-2xl backdrop-blur-xl z-50 flex flex-col">
      {/* Header */}
      <div className="p-5 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/50">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Calculator className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100">Audit & Validation Evidence Drawer</h3>
            <span className="text-[10px] text-slate-400 font-mono">
              Match ID: {detail?.match_id.substring(0, 16)}...
            </span>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Body content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {isLoading ? (
          <div className="py-20 text-center">
            <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <span className="text-xs text-slate-400">Loading audit trail...</span>
          </div>
        ) : detail ? (
          <>
            {/* Status & Method Badge */}
            <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                  Reconciliation Status
                </div>
                <div className="text-sm font-bold text-slate-200 mt-0.5 capitalize flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>{detail.status}</span>
                </div>
              </div>

              <div className="text-right">
                <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                  Confidence Score
                </div>
                <div className="text-sm font-bold text-indigo-400 font-mono mt-0.5">
                  {(detail.confidence * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            {/* AI Verification & Mathematical Proof Box */}
            {detail.ai_verification && (
              <div className="p-4 bg-gradient-to-br from-indigo-950/40 via-slate-900/60 to-slate-950 border border-indigo-500/40 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-bold text-indigo-300">
                      Finance Verification Engine (AI)
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                    Model: {detail.ai_verification.model_used}
                  </span>
                </div>

                <div>
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Reasoning Explanation:
                  </div>
                  <p className="text-xs text-slate-200 mt-1 leading-relaxed bg-slate-950/80 p-2.5 rounded-lg border border-slate-800/80">
                    {detail.ai_verification.reasoning_explanation}
                  </p>
                </div>

                {/* Deterministic Equation Trace */}
                <div>
                  <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5 mb-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Deterministic Validator Equation Check:</span>
                  </div>
                  <pre className="text-[11px] font-mono bg-slate-950 p-2.5 rounded-lg text-emerald-300 border border-emerald-900/40 overflow-x-auto whitespace-pre-wrap">
                    {detail.ai_verification.calculation_trace}
                  </pre>
                </div>

                {/* Supporting Rules if any */}
                {detail.ai_verification.supporting_rules && detail.ai_verification.supporting_rules.length > 0 && (
                  <div>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                      Dynamic Rate Schedule Variances:
                    </div>
                    <ul className="text-xs space-y-1 text-slate-300">
                      {detail.ai_verification.supporting_rules.map((rule, idx) => (
                        <li key={idx} className="flex items-start gap-1.5 text-[11px]">
                          <span className="text-indigo-400">•</span>
                          <span>{rule}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* 3-Way Records Comparison */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
                3-Way Ingested Records
              </h4>

              {/* Settlement */}
              {detail.records.settlement && (
                <div className="p-3.5 bg-slate-900/40 border border-slate-800 rounded-xl space-y-1.5 font-mono text-xs">
                  <div className="flex items-center justify-between text-indigo-400 font-sans font-bold text-[11px]">
                    <span>1. Razorpay Settlement Record</span>
                    <span>{formatCurrency(detail.records.settlement.amount)}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300 pt-1 border-t border-slate-800/60">
                    <div>Order ID: <span className="text-slate-100">{detail.records.settlement.order_id}</span></div>
                    <div>UTR: <span className="text-slate-100">{detail.records.settlement.reference_number || "-"}</span></div>
                    <div>Fees: <span className="text-slate-100">{formatCurrency(detail.records.settlement.fees)}</span></div>
                    <div>GST: <span className="text-slate-100">{formatCurrency(detail.records.settlement.gst)}</span></div>
                    <div>TDS: <span className="text-slate-100">{formatCurrency(detail.records.settlement.tds)}</span></div>
                    <div>Date: <span className="text-slate-100">{detail.records.settlement.txn_date}</span></div>
                  </div>
                </div>
              )}

              {/* Bank Statement */}
              {detail.records.bank && (
                <div className="p-3.5 bg-slate-900/40 border border-slate-800 rounded-xl space-y-1.5 font-mono text-xs">
                  <div className="flex items-center justify-between text-cyan-400 font-sans font-bold text-[11px]">
                    <span>2. Bank Credit Record</span>
                    <span>{formatCurrency(detail.records.bank.amount)}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300 pt-1 border-t border-slate-800/60">
                    <div>Txn ID: <span className="text-slate-100">{detail.records.bank.transaction_id}</span></div>
                    <div>UTR Reference: <span className="text-slate-100">{detail.records.bank.reference_number}</span></div>
                    <div>Date: <span className="text-slate-100">{detail.records.bank.txn_date}</span></div>
                    <div>Status: <span className="text-slate-100">{detail.records.bank.status}</span></div>
                  </div>
                </div>
              )}

              {/* ERP Invoice */}
              {detail.records.invoice && (
                <div className="p-3.5 bg-slate-900/40 border border-slate-800 rounded-xl space-y-1.5 font-mono text-xs">
                  <div className="flex items-center justify-between text-emerald-400 font-sans font-bold text-[11px]">
                    <span>3. ERP Invoice Record</span>
                    <span>{formatCurrency(detail.records.invoice.amount)}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300 pt-1 border-t border-slate-800/60">
                    <div>Invoice Txn: <span className="text-slate-100">{detail.records.invoice.transaction_id}</span></div>
                    <div>Order ID: <span className="text-slate-100">{detail.records.invoice.order_id}</span></div>
                    <div>Date: <span className="text-slate-100">{detail.records.invoice.txn_date}</span></div>
                    <div>Status: <span className="text-slate-100">{detail.records.invoice.status}</span></div>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
