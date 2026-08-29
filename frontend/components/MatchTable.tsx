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
  ShieldCheck,
} from "lucide-react";

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
}

export function MatchTable({
  matches,
  selectedMatchId,
  onSelectMatch,
  onExportCsv,
}: MatchTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [methodFilter, setMethodFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 15;

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
    if (val === null || val === undefined) return "-";
    return `₹${val.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getMethodBadge = (method: string, ruleName: string | null) => {
    if (method === "rule") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800/40">
          <CheckCircle2 className="w-3 h-3" />
          <span>{ruleName ? ruleName.replace(/_/g, " ") : "Rule Match"}</span>
        </span>
      );
    }
    if (method === "ai_verified") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-950 text-indigo-300 border border-indigo-500/40 shadow-sm shadow-indigo-500/20">
          <Sparkles className="w-3 h-3 text-indigo-400" />
          <span>AI Verified (Math Proven)</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-950 text-blue-300 border border-blue-800/40">
        <ShieldCheck className="w-3 h-3" />
        <span>Manual Approved</span>
      </span>
    );
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl backdrop-blur-md">
      {/* Header controls */}
      <div className="p-4 border-b border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-950/40">
        <div className="flex items-center gap-2">
          <div className="relative flex-1 md:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search Order ID, UTR, Match ID..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <select
            value={methodFilter}
            onChange={(e) => {
              setMethodFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Methods</option>
            <option value="rule">Rule Matches</option>
            <option value="ai">AI Verified</option>
            <option value="manual">Manual Approved</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">
            Showing {filteredMatches.length} of {matches.length} matches
          </span>

          <button
            onClick={onExportCsv}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/80 text-slate-400 font-mono uppercase text-[10px] tracking-wider border-b border-slate-800/80">
            <tr>
              <th className="py-3 px-4">Order ID / UTR</th>
              <th className="py-3 px-4">Invoice</th>
              <th className="py-3 px-4">Settlement</th>
              <th className="py-3 px-4">Bank Credit</th>
              <th className="py-3 px-4">Resolution Method</th>
              <th className="py-3 px-4">Confidence</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {paginatedMatches.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500 italic">
                  No matching records found.
                </td>
              </tr>
            ) : (
              paginatedMatches.map((m) => {
                const isSelected = selectedMatchId === m.match_id;
                const isAI = m.match_method === "ai_verified";

                return (
                  <tr
                    key={m.match_id}
                    onClick={() => onSelectMatch(m.match_id)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? "bg-indigo-950/40 hover:bg-indigo-950/50"
                        : isAI
                        ? "bg-indigo-950/10 hover:bg-slate-800/50"
                        : "hover:bg-slate-800/30"
                    }`}
                  >
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-200">
                        {m.order_id || m.match_id.substring(0, 12)}
                      </div>
                      {m.reference_number && (
                        <div className="text-[10px] text-slate-400 truncate max-w-[150px]">
                          UTR: {m.reference_number}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      {formatCurrency(m.invoice_amount || m.amount)}
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      {formatCurrency(m.settlement_amount || m.amount)}
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      {formatCurrency(m.bank_amount || m.amount)}
                    </td>
                    <td className="py-3 px-4">
                      {getMethodBadge(m.match_method, m.rule_name)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              m.confidence >= 0.95
                                ? "bg-emerald-400"
                                : m.confidence >= 0.85
                                ? "bg-indigo-400"
                                : "bg-amber-400"
                            }`}
                            style={{ width: `${m.confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-[11px] font-bold text-slate-300">
                          {(m.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectMatch(m.match_id);
                        }}
                        className="px-2.5 py-1 text-[11px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-sans font-medium transition-colors"
                      >
                        Inspect Trace
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="p-3 border-t border-slate-800/80 flex items-center justify-between bg-slate-950/40 text-xs text-slate-400">
          <div>
            Page {currentPage} of {totalPages}
          </div>
          <div className="flex items-center gap-1">
            <button
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-slate-800"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-slate-800"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
