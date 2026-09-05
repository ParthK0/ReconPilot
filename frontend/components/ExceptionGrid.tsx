"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  Clock,
  UserCheck,
  CheckCircle2,
  Filter,
} from "lucide-react";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";
import { EmptyState } from "./ui/EmptyState";

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
  isLoading?: boolean;
}

export function ExceptionGrid({
  exceptions,
  onOpenReview,
  isLoading = false,
}: ExceptionGridProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const categories = Array.from(new Set(exceptions.map((e) => e.category)));

  const filteredExceptions = exceptions.filter(
    (e) => selectedCategory === "all" || e.category === selectedCategory
  );

  const formatCategory = (cat: string) => {
    return cat.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const formatCurrency = (val: number | null) => {
    if (val === null || val === undefined) return "—";
    return `₹${val.toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 shadow-xl backdrop-blur-md space-y-5">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-sm sm:text-base font-bold text-slate-100">Operational Exceptions Queue</h2>
            <p className="text-xs text-slate-400">
              Discrepancies flagged by deterministic rules or arithmetic validator awaiting controller action
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="warning" size="md">
            {exceptions.length} Pending Actions
          </Badge>
        </div>
      </div>

      {/* Category Filter Chips */}
      {categories.length > 0 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Filter exceptions by category">
          <button
            role="tab"
            aria-selected={selectedCategory === "all"}
            onClick={() => setSelectedCategory("all")}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
              selectedCategory === "all"
                ? "bg-amber-600 text-white shadow-md shadow-amber-600/20"
                : "bg-slate-950/80 text-slate-400 hover:text-slate-200 border border-slate-800"
            }`}
          >
            All Exceptions ({exceptions.length})
          </button>
          {categories.map((cat) => {
            const count = exceptions.filter((e) => e.category === cat).length;
            const isSelected = selectedCategory === cat;
            return (
              <button
                key={cat}
                role="tab"
                aria-selected={isSelected}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-amber-600 text-white shadow-md shadow-amber-600/20"
                    : "bg-slate-950/80 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                <span>{formatCategory(cat)}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-800/80 font-mono">
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Exceptions Grid Cards */}
      {filteredExceptions.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredExceptions.map((exc) => (
            <div
              key={exc.exception_id}
              className="bg-slate-950/60 border border-slate-800/80 hover:border-amber-500/40 rounded-2xl p-4 flex flex-col justify-between gap-4 transition-all duration-150 hover:shadow-lg hover:shadow-amber-950/10"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <Badge variant="warning" size="sm">
                    {formatCategory(exc.category)}
                  </Badge>
                  <span className="text-[10px] font-mono text-slate-500">
                    {exc.created_at ? new Date(exc.created_at).toLocaleTimeString() : "Pending"}
                  </span>
                </div>

                <div>
                  <div className="text-xs text-slate-400">Order Reference:</div>
                  <div className="text-sm font-bold font-mono text-slate-100">
                    {exc.order_id || "Unlinked Record"}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 bg-slate-900/60 border border-slate-800/60 rounded-xl p-2.5 text-xs font-mono">
                  <div>
                    <span className="text-[10px] text-slate-400 block">Gross Amount</span>
                    <span className="font-bold text-slate-200">{formatCurrency(exc.amount)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-amber-400 block">Variance (Δ)</span>
                    <span className="font-bold text-amber-300">
                      {formatCurrency(exc.discrepancy_amount)}
                    </span>
                  </div>
                </div>

                {exc.notes && (
                  <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/40 rounded-lg p-2 border border-slate-800/50">
                    {exc.notes}
                  </p>
                )}
              </div>

              <Button
                variant="subtle"
                size="sm"
                className="w-full justify-center"
                leftIcon={<UserCheck className="w-3.5 h-3.5" />}
                onClick={() => onOpenReview(exc)}
              >
                Review & Resolve Exception
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<CheckCircle2 className="w-8 h-8 text-emerald-400" />}
          title="Zero Pending Exceptions"
          description="All financial discrepancies for this batch have been resolved or confirmed."
          action={
            selectedCategory !== "all" && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedCategory("all")}
              >
                Show All Categories
              </Button>
            )
          }
        />
      )}
    </div>
  );
}
