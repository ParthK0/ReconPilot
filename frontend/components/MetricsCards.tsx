"use client";

import React from "react";
import {
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Zap,
  Target,
  BarChart2,
  Sparkles,
} from "lucide-react";

interface MetricsCardsProps {
  metrics: {
    records_processed: number;
    rule_matches: number;
    ai_verified: number;
    needs_review: number;
    match_rate: number;
    precision: number | null;
    recall: number | null;
    processing_time_seconds: number;
    manual_hours_saved: number;
  };
}

export function MetricsCards({ metrics }: MetricsCardsProps) {
  const formatHours = (hours: number) => {
    if (hours > 0) {
      return `${hours.toFixed(1)}h`;
    }
    return "0.0h";
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
      {/* 1. Total Processed */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3.5 backdrop-blur-md">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-[11px] font-medium uppercase tracking-wider">Processed</span>
          <Zap className="w-3.5 h-3.5 text-indigo-400" />
        </div>
        <div className="text-xl font-black text-slate-100 font-mono">
          {metrics.records_processed.toLocaleString()}
        </div>
        <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
          <span>Settlement tranches</span>
        </div>
      </div>

      {/* 2. Rule Matches (Deterministic) */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3.5 backdrop-blur-md">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-[11px] font-medium uppercase tracking-wider text-emerald-400">Rule Matches</span>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        </div>
        <div className="text-xl font-black text-emerald-400 font-mono">
          {metrics.rule_matches.toLocaleString()}
        </div>
        <div className="text-[10px] text-slate-400 mt-1">
          {metrics.records_processed > 0
            ? `${((metrics.rule_matches / metrics.records_processed) * 100).toFixed(1)}% deterministic`
            : "0%"}
        </div>
      </div>

      {/* 3. AI Verified (Hero Engine) */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3.5 backdrop-blur-md relative overflow-hidden">
        <div className="absolute top-0 right-0 w-12 h-12 bg-indigo-500/10 rounded-full blur-xl pointer-events-none" />
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-[11px] font-medium uppercase tracking-wider text-indigo-400">AI Verified</span>
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
        </div>
        <div className="text-xl font-black text-indigo-400 font-mono">
          {metrics.ai_verified.toLocaleString()}
        </div>
        <div className="text-[10px] text-slate-400 mt-1">
          100% Math Confirmed ✓
        </div>
      </div>

      {/* 4. Exceptions / Review */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3.5 backdrop-blur-md">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-[11px] font-medium uppercase tracking-wider text-amber-400">Exceptions</span>
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
        </div>
        <div className="text-xl font-black text-amber-400 font-mono">
          {metrics.needs_review.toLocaleString()}
        </div>
        <div className="text-[10px] text-slate-400 mt-1">
          Categorized for review
        </div>
      </div>

      {/* 5. Precision */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3.5 backdrop-blur-md">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-[11px] font-medium uppercase tracking-wider">Precision</span>
          <Target className="w-3.5 h-3.5 text-blue-400" />
        </div>
        <div className="text-xl font-black text-slate-100 font-mono">
          {metrics.precision !== null ? `${metrics.precision.toFixed(1)}%` : "N/A"}
        </div>
        <div className="text-[10px] text-slate-400 mt-1">
          Ground-truth tested
        </div>
      </div>

      {/* 6. Processing Time */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-3.5 backdrop-blur-md">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-[11px] font-medium uppercase tracking-wider">Speed</span>
          <Clock className="w-3.5 h-3.5 text-cyan-400" />
        </div>
        <div className="text-xl font-black text-slate-100 font-mono">
          {metrics.processing_time_seconds.toFixed(2)}s
        </div>
        <div className="text-[10px] text-slate-400 mt-1">
          Wall-clock runtime
        </div>
      </div>

      {/* 7. Manual Hours Saved */}
      <div className="bg-gradient-to-br from-indigo-950/40 to-slate-900/60 border border-indigo-500/30 rounded-xl p-3.5 backdrop-blur-md col-span-2 md:col-span-1">
        <div className="flex items-center justify-between text-slate-400 mb-1.5">
          <span className="text-[11px] font-medium uppercase tracking-wider text-indigo-300">ROI Saved</span>
          <TrendingUp className="w-3.5 h-3.5 text-indigo-400" />
        </div>
        <div className="text-xl font-black text-indigo-300 font-mono">
          {formatHours(metrics.manual_hours_saved)}
        </div>
        <div className="text-[10px] text-slate-400 mt-1">
          vs. manual baseline
        </div>
      </div>
    </div>
  );
}
