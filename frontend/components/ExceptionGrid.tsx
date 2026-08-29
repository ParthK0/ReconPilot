"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  Clock,
  HelpCircle,
  ArrowRight,
  ShieldAlert,
  ChevronDown,
  UserCheck,
} from "lucide-react";

export interface ExceptionItem {
  exception_id: string;
  category: string;
  source_record_id: string;
  order_id: string | null;
  amount: number | null;
  discrepancy_amount: number | null;
  notes: string | null;
  status: string;
  created_at: string;
}

interface ExceptionGridProps {
  exceptions: ExceptionItem[];
  onOpenReview: (exception: ExceptionItem) => void;
}

export function ExceptionGrid({ exceptions, onOpenReview }: ExceptionGridProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const categories = Array.from(new Set(exceptions.map((e) => e.category)));

  const filteredExceptions = exceptions.filter(
    (e) => selectedCategory === "all" || e.category === selectedCategory
  );

  const formatCategory = (cat: string) => {
    return cat.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const formatCurrency = (val: number | null) => {
    if (val === null || val === undefined) return "-";
    return `₹${val.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-xl backdrop-blur-md">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <AlertTriangle className="w-4 h-4" />
            </span>
            <h3 className="text-sm font-bold text-slate-100">Operational Exceptions Queue</h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Discrepancies that failed deterministic rate schedules and AI math validation, routed for human review.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-amber-500"
          >
            <option value="all">All Exception Types ({exceptions.length})</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {formatCategory(c)} ({exceptions.filter((e) => e.category === c).length})
              </option>
            ))}
          </select>
        </div>
      </div>

      {filteredExceptions.length === 0 ? (
        <div className="py-12 text-center text-slate-500 italic text-xs">
          No exceptions in the selected filter. All records reconciled.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 mt-4">
          {filteredExceptions.map((exc) => (
            <div
              key={exc.exception_id}
              className="bg-slate-950/60 border border-slate-800/90 hover:border-amber-500/40 rounded-xl p-4 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-950/80 text-amber-400 border border-amber-800/40">
                    {formatCategory(exc.category)}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {exc.exception_id.substring(0, 8)}
                  </span>
                </div>

                <div className="flex items-baseline justify-between mt-2">
                  <span className="text-xs font-semibold text-slate-200 font-mono">
                    {exc.order_id || "ID: " + exc.source_record_id.substring(0, 10)}
                  </span>
                  <span className="text-xs font-bold text-amber-300 font-mono">
                    {formatCurrency(exc.amount)}
                  </span>
                </div>

                {exc.discrepancy_amount !== null && exc.discrepancy_amount !== undefined && (
                  <div className="text-[11px] text-rose-400 font-mono mt-1">
                    Variance Delta: {formatCurrency(exc.discrepancy_amount)}
                  </div>
                )}

                <p className="text-xs text-slate-400 mt-2 bg-slate-900/80 p-2 rounded-lg border border-slate-800/60 line-clamp-3">
                  {exc.notes || "Awaiting human controller investigation and feedback recording."}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-900 flex items-center justify-between">
                <span className="text-[10px] text-slate-500 font-mono">
                  Status: {exc.status}
                </span>
                <button
                  onClick={() => onOpenReview(exc)}
                  className="px-3 py-1 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                >
                  <UserCheck className="w-3.5 h-3.5" />
                  <span>Review & Learn</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
