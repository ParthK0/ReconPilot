"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Search,
  CheckCircle2,
  Sparkles,
  AlertTriangle,
  ArrowRight,
  Download,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  X,
  Copy,
  Check,
  ChevronDown,
  ArrowUpDown,
  FileCode,
  Building,
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

export type ExportFormat = "csv" | "tally" | "zoho" | "netsuite";

interface MatchTableProps {
  matches: MatchItem[];
  selectedMatchId: string | null;
  onSelectMatch: (matchId: string) => void;
  onExportCsv?: () => void;
  onExportFormat?: (format: ExportFormat) => void;
  isLoading?: boolean;
}

export function MatchTable({
  matches,
  selectedMatchId,
  onSelectMatch,
  onExportCsv,
  onExportFormat,
  isLoading = false,
}: MatchTableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [methodFilter, setMethodFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [sortField, setSortField] = useState<"order_id" | "amount" | "confidence">("confidence");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const searchInputRef = useRef<HTMLInputElement>(null);
  const exportDropdownRef = useRef<HTMLDivElement>(null);
  const pageSize = 12;

  // Keyboard shortcut: Ctrl+K or '/' focuses search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        searchInputRef.current?.focus();
      } else if (e.key === "/" && document.activeElement !== searchInputRef.current) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        exportDropdownRef.current &&
        !exportDropdownRef.current.contains(e.target as Node)
      ) {
        setIsExportOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleCopy = (e: React.MouseEvent, text: string) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopiedId(text);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const handleSort = (field: "order_id" | "amount" | "confidence") => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

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

  const sortedMatches = [...filteredMatches].sort((a, b) => {
    let comparison = 0;
    if (sortField === "amount") {
      const aVal = a.settlement_amount ?? a.invoice_amount ?? a.amount;
      const bVal = b.settlement_amount ?? b.invoice_amount ?? b.amount;
      comparison = aVal - bVal;
    } else if (sortField === "confidence") {
      comparison = a.confidence - b.confidence;
    } else if (sortField === "order_id") {
      comparison = (a.order_id || "").localeCompare(b.order_id || "");
    }
    return sortOrder === "asc" ? comparison : -comparison;
  });

  const totalPages = Math.ceil(sortedMatches.length / pageSize) || 1;
  const paginatedMatches = sortedMatches.slice(
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

  const triggerExport = (format: ExportFormat) => {
    setIsExportOpen(false);
    if (onExportFormat) {
      onExportFormat(format);
    } else if (onExportCsv) {
      onExportCsv();
    }
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
          {/* Search Bar with Keyboard Hint */}
          <div className="relative min-w-[220px] sm:min-w-[260px]">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search Order ID, UTR..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              aria-label="Search transactions by Order ID or UTR"
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-8 pr-14 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
            {searchTerm ? (
              <button
                onClick={() => setSearchTerm("")}
                aria-label="Clear search"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
              >
                <X className="w-3 h-3" />
              </button>
            ) : (
              <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-slate-500 font-mono px-1 py-0.5 rounded bg-slate-900 border border-slate-800 pointer-events-none">
                /
              </span>
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
            className="bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500 cursor-pointer"
          >
            <option value="all">All Methods</option>
            <option value="rule">Rule Matches</option>
            <option value="ai">AI Verified</option>
            <option value="manual">Controller Approved</option>
          </select>

          {/* 1-Click Multi-Format ERP Export Dropdown */}
          <div className="relative" ref={exportDropdownRef}>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsExportOpen(!isExportOpen)}
              leftIcon={<Download className="w-3.5 h-3.5" />}
              rightIcon={<ChevronDown className={`w-3 h-3 transition-transform ${isExportOpen ? "rotate-180" : ""}`} />}
            >
              1-Click ERP Export
            </Button>

            {isExportOpen && (
              <div className="absolute right-0 mt-2 w-60 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-50 p-1.5 space-y-1 text-xs animate-fade-in">
                <div className="px-2 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                  Accounting Formats
                </div>
                <button
                  onClick={() => triggerExport("tally")}
                  className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-indigo-950/60 hover:text-indigo-200 flex items-center gap-2 text-slate-200 transition-colors"
                >
                  <Building className="w-3.5 h-3.5 text-indigo-400" />
                  <div>
                    <div className="font-semibold">Tally Prime XML</div>
                    <div className="text-[10px] text-slate-400">&lt;ENVELOPE&gt; Double-entry vouchers</div>
                  </div>
                </button>
                <button
                  onClick={() => triggerExport("zoho")}
                  className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-emerald-950/60 hover:text-emerald-200 flex items-center gap-2 text-slate-200 transition-colors"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                  <div>
                    <div className="font-semibold">Zoho Books CSV</div>
                    <div className="text-[10px] text-slate-400">Multi-column journal ledger</div>
                  </div>
                </button>
                <button
                  onClick={() => triggerExport("netsuite")}
                  className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-purple-950/60 hover:text-purple-200 flex items-center gap-2 text-slate-200 transition-colors"
                >
                  <FileCode className="w-3.5 h-3.5 text-purple-400" />
                  <div>
                    <div className="font-semibold">NetSuite SuiteTalk JSON</div>
                    <div className="text-[10px] text-slate-400">Oracle NetSuite REST schema</div>
                  </div>
                </button>
                <div className="border-t border-slate-800 my-1" />
                <button
                  onClick={() => triggerExport("csv")}
                  className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-slate-800 text-slate-300 flex items-center gap-2 transition-colors"
                >
                  <Download className="w-3.5 h-3.5 text-slate-400" />
                  <div>
                    <div className="font-semibold">Standard CSV Ledger</div>
                    <div className="text-[10px] text-slate-400">Audit-ready spreadsheet export</div>
                  </div>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300 border-collapse" aria-label="Reconciliation transactions">
          <thead className="bg-slate-950/70 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider sticky top-0 backdrop-blur z-10">
            <tr>
              <th scope="col" className="py-3 px-4">
                <button
                  onClick={() => handleSort("order_id")}
                  className="inline-flex items-center gap-1 hover:text-slate-200 font-semibold uppercase tracking-wider"
                >
                  Order ID & Date
                  <ArrowUpDown className="w-3 h-3 text-slate-500" />
                </button>
              </th>
              <th scope="col" className="py-3 px-4">Method & Rule</th>
              <th scope="col" className="py-3 px-4 text-right">
                <button
                  onClick={() => handleSort("amount")}
                  className="inline-flex items-center gap-1 hover:text-slate-200 font-semibold uppercase tracking-wider ml-auto"
                >
                  Invoice Billed
                  <ArrowUpDown className="w-3 h-3 text-slate-500" />
                </button>
              </th>
              <th scope="col" className="py-3 px-4 text-right">Settlement Net</th>
              <th scope="col" className="py-3 px-4 text-right">Bank Credit</th>
              <th scope="col" className="py-3 px-4 text-center">
                <button
                  onClick={() => handleSort("confidence")}
                  className="inline-flex items-center gap-1 hover:text-slate-200 font-semibold uppercase tracking-wider mx-auto"
                >
                  Confidence
                  <ArrowUpDown className="w-3 h-3 text-slate-500" />
                </button>
              </th>
              <th scope="col" className="py-3 px-4 text-right">Audit Trace</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => <TableRowSkeleton key={i} cols={7} />)
            ) : paginatedMatches.length > 0 ? (
              paginatedMatches.map((match) => {
                const isSelected = selectedMatchId === match.match_id;
                const orderText = match.order_id || "Unlinked Order";
                const isCopied = copiedId === orderText;

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
                      <div className="flex items-center gap-1.5 group">
                        <span className="font-mono font-semibold text-slate-200">
                          {orderText}
                        </span>
                        {match.order_id && (
                          <button
                            onClick={(e) => handleCopy(e, match.order_id!)}
                            aria-label={`Copy order ID ${match.order_id}`}
                            className="text-slate-500 hover:text-slate-200 opacity-0 group-hover:opacity-100 transition-opacity p-0.5"
                          >
                            {isCopied ? (
                              <Check className="w-3 h-3 text-emerald-400" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        )}
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
              {Math.min(currentPage * pageSize, sortedMatches.length)}
            </span>{" "}
            of <span className="font-semibold text-slate-200">{sortedMatches.length}</span> entries
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
