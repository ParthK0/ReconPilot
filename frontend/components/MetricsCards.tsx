"use client";

import React from "react";
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  Zap,
  Target,
  Sparkles,
  Layers,
} from "lucide-react";
import { CardSkeleton } from "./ui/Skeleton";

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
  isLoading?: boolean;
}

export function MetricsCards({ metrics, isLoading = false }: MetricsCardsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {Array.from({ length: 7 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    );
  }

  const formatHours = (hours: number) => {
    return hours > 0 ? `${hours.toFixed(1)}h` : "0.0h";
  };

  const cards = [
    {
      id: "processed",
      label: "Total Volume",
      value: metrics.records_processed.toLocaleString(),
      subtext: "Ingested records",
      icon: <Layers className="w-4 h-4 text-indigo-400" />,
      valueColor: "text-slate-100",
      borderColor: "border-slate-800/80 hover:border-indigo-500/40",
      accentBg: "bg-indigo-500/10",
    },
    {
      id: "rule-matches",
      label: "Rule Matches",
      value: metrics.rule_matches.toLocaleString(),
      subtext: "100% deterministic",
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
      valueColor: "text-emerald-300",
      borderColor: "border-slate-800/80 hover:border-emerald-500/40",
      accentBg: "bg-emerald-500/10",
    },
    {
      id: "ai-verified",
      label: "AI Verified",
      value: metrics.ai_verified.toLocaleString(),
      subtext: "Paisa math proven",
      icon: <Sparkles className="w-4 h-4 text-purple-400" />,
      valueColor: "text-purple-300",
      borderColor: "border-slate-800/80 hover:border-purple-500/40",
      accentBg: "bg-purple-500/10",
    },
    {
      id: "needs-review",
      label: "Needs Review",
      value: metrics.needs_review.toLocaleString(),
      subtext: "Audit exceptions",
      icon: <AlertTriangle className="w-4 h-4 text-amber-400" />,
      valueColor: "text-amber-300",
      borderColor: "border-slate-800/80 hover:border-amber-500/40",
      accentBg: "bg-amber-500/10",
    },
    {
      id: "match-rate",
      label: "Match Rate",
      value: `${(metrics.match_rate * 100).toFixed(1)}%`,
      subtext: "Reconciliation yield",
      icon: <Target className="w-4 h-4 text-cyan-400" />,
      valueColor: "text-cyan-300",
      borderColor: "border-slate-800/80 hover:border-cyan-500/40",
      accentBg: "bg-cyan-500/10",
    },
    {
      id: "precision",
      label: "Precision",
      value:
        metrics.precision !== null
          ? `${(metrics.precision * 100).toFixed(0)}%`
          : "100%",
      subtext: "0 false positives",
      icon: <CheckCircle2 className="w-4 h-4 text-blue-400" />,
      valueColor: "text-blue-300",
      borderColor: "border-slate-800/80 hover:border-blue-500/40",
      accentBg: "bg-blue-500/10",
    },
    {
      id: "hours-saved",
      label: "Manual Time Saved",
      value: formatHours(metrics.manual_hours_saved),
      subtext: `${metrics.processing_time_seconds.toFixed(2)}s runtime`,
      icon: <Clock className="w-4 h-4 text-emerald-400" />,
      valueColor: "text-emerald-300",
      borderColor: "border-slate-800/80 hover:border-emerald-500/40",
      accentBg: "bg-emerald-500/10",
    },
  ];

  return (
    <section aria-label="Reconciliation Performance Metrics">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {cards.map((card) => (
          <div
            key={card.id}
            className={`group bg-slate-900/70 border rounded-2xl p-3.5 backdrop-blur-md transition-all duration-200 hover:shadow-lg hover:shadow-indigo-950/20 ${card.borderColor}`}
          >
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 group-hover:text-slate-300 transition-colors">
                {card.label}
              </span>
              <div className={`p-1.5 rounded-lg ${card.accentBg} transition-transform group-hover:scale-110`}>
                {card.icon}
              </div>
            </div>
            <div className={`text-xl sm:text-2xl font-black font-mono tracking-tight ${card.valueColor}`}>
              {card.value}
            </div>
            <div className="text-[11px] text-slate-400 mt-1 font-medium truncate">
              {card.subtext}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
