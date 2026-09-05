"use client";

import React from "react";
import {
  Wallet,
  TrendingUp,
  ArrowUpRight,
  ShieldCheck,
  AlertCircle,
  HelpCircle,
} from "lucide-react";
import { Badge } from "./ui/Badge";
import { Skeleton } from "./ui/Skeleton";

interface CashPositionData {
  batch_id: string;
  merchant_type: string;
  currency: string;
  current_bank_balance: number;
  gross_volume_processed: number;
  settled_volume_credited: number;
  pending_settlement_inflows: number;
  pending_refund_reserves: number;
  expected_cash_tomorrow: number;
  expected_mdr_tax_deductions: number;
  reconciled_cash_ratio: number;
  liquidity_health_index: number;
  disputed_volume_at_risk: number;
  summary_narrative: string;
}

interface CashPositionBannerProps {
  cashPosition: CashPositionData | null;
  isLoading?: boolean;
}

export function CashPositionBanner({
  cashPosition,
  isLoading = false,
}: CashPositionBannerProps) {
  if (isLoading) {
    return (
      <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 space-y-4">
        <div className="flex justify-between items-center">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-6 w-24 rounded-full" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!cashPosition) return null;

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: cashPosition.currency || "INR",
      maximumFractionDigits: 0,
    }).format(val);
  };

  const healthVariant =
    cashPosition.liquidity_health_index >= 80
      ? "success"
      : cashPosition.liquidity_health_index >= 60
      ? "warning"
      : "danger";

  return (
    <section
      aria-label="Live Cash Position & Liquidity Controller"
      className="bg-gradient-to-r from-slate-900 via-indigo-950/25 to-slate-900 border border-slate-800/80 rounded-2xl p-5 shadow-xl backdrop-blur-md"
    >
      {/* Header Row */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div className="flex items-start sm:items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shrink-0">
            <Wallet className="w-5 h-5" aria-hidden="true" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm sm:text-base font-bold text-slate-100 tracking-tight">
                Treasury Cash Position & Liquidity Controller
              </h2>
              <Badge variant={healthVariant} size="sm" dot>
                Health: {cashPosition.liquidity_health_index}/100
              </Badge>
            </div>
            <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
              {cashPosition.summary_narrative}
            </p>
          </div>
        </div>

        {/* Status Pills */}
        <div className="flex items-center gap-2.5 text-xs font-mono shrink-0">
          <div className="px-3 py-1.5 bg-slate-950/80 border border-slate-800 rounded-xl flex items-center gap-2">
            <span className="text-slate-400">Reconciled Ratio:</span>
            <span className="text-emerald-300 font-bold">
              {(cashPosition.reconciled_cash_ratio * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Financial Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 pt-4">
        {/* 1. Confirmed Bank Cash */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1.5">
            <span className="font-medium">Confirmed Bank Cash</span>
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-lg sm:text-xl font-bold font-mono text-slate-100">
            {formatCurrency(cashPosition.current_bank_balance)}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-medium">
            Settled bank account credit
          </div>
        </div>

        {/* 2. In-Flight Settlement Inflows */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1.5">
            <span className="font-medium">In-Flight Pipeline (+)</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="text-lg sm:text-xl font-bold font-mono text-indigo-300">
            {formatCurrency(cashPosition.pending_settlement_inflows)}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-medium">
            T+2 transit from Razorpay
          </div>
        </div>

        {/* 3. Pending Refund Reserves */}
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1.5">
            <span className="font-medium">Refund Reserves (-)</span>
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-lg sm:text-xl font-bold font-mono text-amber-300">
            {formatCurrency(cashPosition.pending_refund_reserves)}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-medium">
            Held for customer chargebacks
          </div>
        </div>

        {/* 4. Expected Net Cash Tomorrow */}
        <div className="bg-gradient-to-br from-indigo-950/50 to-slate-950/80 border border-indigo-500/30 rounded-xl p-3.5 shadow-sm shadow-indigo-500/10">
          <div className="flex items-center justify-between text-indigo-200 text-xs mb-1.5">
            <span className="font-semibold">Expected Cash Tomorrow (=)</span>
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-lg sm:text-xl font-bold font-mono text-emerald-300">
            {formatCurrency(cashPosition.expected_cash_tomorrow)}
          </div>
          <div className="text-[11px] text-slate-300 mt-1 font-medium">
            Net anticipated working capital
          </div>
        </div>
      </div>
    </section>
  );
}
