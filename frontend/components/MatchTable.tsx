"use client";

import React, { useState } from "react";
import {
  Search,
  Filter,
  CheckCircle2,
  Sparkles,
  AlertTriangle,
  ArrowRight,
  Download,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  X,
} from "lucide-react";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";
import { TableRowSkeleton } from "./ui/Skeleton";
import { EmptyState } from "./ui/EmptyState";

export interface MatchItem {
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

interface MatchTableProps {
  matches: MatchItem[];
  selectedMatchId: string | null;
  onSelectMatch: (matchId: string) => void;
  onExportCsv: () => void;
  isLoading?: boolean;
}

export function MatchTable({
  matches,
  selectedMatchId,
  onSelectMatch,
  onExportCsv,
  isLoading = false,
}: MatchTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [methodFilter, setMethodFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 12;

  const filteredMatches = matches.filter((m) => {
    const matchesSearch =
      (m.order_id && m.order_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (m.reference_number && m.reference_number.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (m.match_id && m.match_id.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesStatus = statusFilter === "all" || m.status === statusFilter;
    const matchesMethod =
      methodFilter === "all" ||
      (methodFilter === "rule" && m.match_method === "rule") ||
      (methodFilter === "ai" && m.match_method === "ai_verified") ||
      (methodFilter === "manual" && m.match_method === "manual_approved");

    return matchesSearch && matchesStatus && matchesMethod;
  });

  const totalPages = Math.ceil(filteredMatches.length / pageSize) || 1;
  const paginatedMatches = filteredMatches.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const formatCurrency = (val: number | null) => {
    if (val === null || val === undefined) return "—";
    return `₹${val.toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const getMethodBadge = (method: string) => {
    switch (method) {
      case "rule":
        return (
          <Badge variant="success" size="sm">
            <CheckCircle2 className="w-3 h-3" />
            Rule Match
          </Badge>
        );
      case "ai_verified":
        return (
          <Badge variant="ai" size="sm">
            <Sparkles className="w-3 h-3" />
            AI Verified
          </Badge>
        );
      case "manual_approved":
        return (
          <Badge variant="default" size="sm">
            Controller Approved
          </Badge>
        );
      default:
        return (
          <Badge variant="neutral" size="sm">
            {method}
          </Badge>
        );
    }
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl shadow-xl backdrop-blur-md overflow-hidden flex flex-col">
      {/* Header & Controls Toolbar */}
      <div className="p-4 sm:p-5 border-b border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <FileSpreadsheet className="w-4 h-4" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-sm sm:text-base font-bold text-slate-100">Reconciliation Match Ledger</h2>
            <p className="text-xs text-slate-400">
              {filteredMatches.length} matching transactions across ERP, Gateway, and Bank
            </p>
          </div>
        </div>

        {/* Action Buttons & Filters */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search Bar */}
          <div className="relative min-w-[200px] sm:min-w-[240px]">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search Order ID, UTR..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              aria-label="Search transactions by Order ID or UTR"
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-8 pr-8 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm("")}
                aria-label="Clear search"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Method Filter */}
          <select
            value={methodFilter}
            onChange={(e) => {
              setMethodFilter(e.target.value);
              setCurrentPage(1);
            }}
            aria-label="Filter by matching method"
            className="bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Methods</option>
            <option value="rule">Rule Matches</option>
            <option value="ai">AI Verified</option>
            <option value="manual">Controller Approved</option>
          </select>

          {/* Export CSV Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={onExportCsv}
            leftIcon={<Download className="w-3.5 h-3.5" />}
          >
            Export CSV
          </Button>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300 border-collapse" aria-label="Reconciliation transactions">
          <thead className="bg-slate-950/70 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider sticky top-0 backdrop-blur z-10">
            <tr>
              <th scope="col" className="py-3 px-4">Order ID & Date</th>
              <th scope="col" className="py-3 px-4">Method & Rule</th>
              <th scope="col" className="py-3 px-4 text-right">Invoice Billed</th>
              <th scope="col" className="py-3 px-4 text-right">Settlement Net</th>
              <th scope="col" className="py-3 px-4 text-right">Bank Credit</th>
              <th scope="col" className="py-3 px-4 text-center">Confidence</th>
              <th scope="col" className="py-3 px-4 text-right">Audit Trace</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => <TableRowSkeleton key={i} cols={7} />)
            ) : paginatedMatches.length > 0 ? (
              paginatedMatches.map((match) => {
                const isSelected = selectedMatchId === match.match_id;
                return (
                  <tr
                    key={match.match_id}
                    tabIndex={0}
                    role="button"
                    aria-selected={isSelected}
                    onClick={() => onSelectMatch(match.match_id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelectMatch(match.match_id);
                      }
                    }}
                    className={`cursor-pointer transition-colors duration-150 ${
                      isSelected
                        ? "bg-indigo-950/40 border-l-2 border-indigo-500"
                        : "hover:bg-slate-800/40 focus:bg-slate-800/60"
                    }`}
                  >
                    <td className="py-3.5 px-4">
                      <div className="font-mono font-semibold text-slate-200">
                        {match.order_id || "Unlinked Order"}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                        {match.reference_number || match.match_id.substring(0, 10)}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5">
                        {getMethodBadge(match.match_method)}
                      </div>
                      {match.rule_name && (
                        <div className="text-[10px] text-slate-400 font-mono mt-1 truncate max-w-[140px]">
                          {match.rule_name}
                        </div>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-right font-mono text-slate-200 font-medium">
                      {formatCurrency(match.invoice_amount)}
                    </td>

                    <td className="py-3.5 px-4 text-right font-mono text-indigo-300 font-medium">
                      {formatCurrency(match.settlement_amount)}
                    </td>

                    <td className="py-3.5 px-4 text-right font-mono text-emerald-300 font-medium">
                      {formatCurrency(match.bank_amount)}
                    </td>

                    <td className="py-3.5 px-4 text-center">
                      <span
                        className={`inline-block font-mono font-bold text-[11px] px-2 py-0.5 rounded-full ${
                          match.confidence >= 0.95
                            ? "bg-emerald-950 text-emerald-300 border border-emerald-800/40"
                            : match.confidence >= 0.8
                            ? "bg-indigo-950 text-indigo-300 border border-indigo-800/40"
                            : "bg-amber-950 text-amber-300 border border-amber-800/40"
                        }`}
                      >
                        {(match.confidence * 100).toFixed(0)}%
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-400 hover:text-indigo-300">
                        Inspect
                        <ArrowRight className="w-3.5 h-3.5" />
                      </span>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={7} className="py-10">
                  <EmptyState
                    title="No Matching Transactions"
                    description="No records match your active search and filter criteria."
                    action={
                      (searchTerm || methodFilter !== "all") && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setSearchTerm("");
                            setMethodFilter("all");
                          }}
                        >
                          Clear Filters
                        </Button>
                      )
                    }
                  />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="p-4 border-t border-slate-800/80 bg-slate-950/40 flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing <span className="font-semibold text-slate-200">{(currentPage - 1) * pageSize + 1}</span> to{" "}
            <span className="font-semibold text-slate-200">
              {Math.min(currentPage * pageSize, filteredMatches.length)}
            </span>{" "}
            of <span className="font-semibold text-slate-200">{filteredMatches.length}</span> entries
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              aria-label="Previous Page"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </Button>
            <span className="font-mono text-slate-300 px-2">
              {currentPage} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              aria-label="Next Page"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
