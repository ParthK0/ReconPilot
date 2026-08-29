"use client";

import React from "react";
import {
  Wallet,
  TrendingUp,
  Coins,
  ArrowUpRight,
  Shield,
  AlertTriangle,
} from "lucide-react";

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
}

export function CashPositionBanner({ cashPosition }: CashPositionBannerProps) {
  if (!cashPosition) return null;

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: cashPosition.currency || "INR",
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="bg-gradient-to-r from-slate-900 via-indigo-950/20 to-slate-900 border border-slate-800/80 rounded-2xl p-5 shadow-lg backdrop-blur-md">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800/60">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Wallet className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-100">Live Cash Position & Liquidity Controller</h3>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/40">
                Health Index: {cashPosition.liquidity_health_index}/100
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{cashPosition.summary_narrative}</p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="px-3 py-1.5 bg-slate-950/70 border border-slate-800 rounded-lg">
            <span className="text-slate-500">Reconciled Ratio: </span>
            <span className="text-emerald-400 font-bold">
              {(cashPosition.reconciled_cash_ratio * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
        {/* 1. Bank Balance */}
        <div className="p-3 bg-slate-950/40 border border-slate-800/40 rounded-xl">
          <div className="text-[11px] text-slate-400 font-medium">Bank Balance</div>
          <div className="text-base font-bold text-slate-100 font-mono mt-1">
            {formatCurrency(cashPosition.current_bank_balance)}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Verified in bank credits</div>
        </div>

        {/* 2. Expected Inflows */}
        <div className="p-3 bg-slate-950/40 border border-slate-800/40 rounded-xl">
          <div className="text-[11px] text-emerald-400 font-medium flex items-center gap-1">
            <span>Pending Settlements</span>
            <ArrowUpRight className="w-3 h-3" />
          </div>
          <div className="text-base font-bold text-emerald-400 font-mono mt-1">
            +{formatCurrency(cashPosition.pending_settlement_inflows)}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Clearing in T+1 window</div>
        </div>

        {/* 3. Expected Cash Tomorrow */}
        <div className="p-3 bg-indigo-950/20 border border-indigo-500/20 rounded-xl">
          <div className="text-[11px] text-indigo-300 font-medium flex items-center gap-1">
            <span>Expected Cash Tomorrow</span>
            <Coins className="w-3 h-3 text-indigo-400" />
          </div>
          <div className="text-base font-bold text-indigo-200 font-mono mt-1">
            {formatCurrency(cashPosition.expected_cash_tomorrow)}
          </div>
          <div className="text-[10px] text-indigo-400/70 mt-0.5">Net of MDR & taxes</div>
        </div>

        {/* 4. Volume at Risk */}
        <div className="p-3 bg-slate-950/40 border border-slate-800/40 rounded-xl">
          <div className="text-[11px] text-amber-400 font-medium flex items-center gap-1">
            <span>Volume At Risk</span>
            <AlertTriangle className="w-3 h-3 text-amber-400" />
          </div>
          <div className="text-base font-bold text-amber-300 font-mono mt-1">
            {formatCurrency(cashPosition.disputed_volume_at_risk)}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Unsettled / Disputed</div>
        </div>
      </div>
    </div>
  );
}
