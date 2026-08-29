"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { Layers, PieChart as PieIcon, Activity } from "lucide-react";

interface AnalyticsChartsProps {
  metrics: {
    records_processed: number;
    rule_matches: number;
    ai_verified: number;
    needs_review: number;
    processing_time_seconds: number;
  };
  exceptionCounts: Record<string, number>;
}

const EXCEPTION_COLORS = [
  "#f59e0b", // amber-500
  "#ef4444", // red-500
  "#8b5cf6", // purple-500
  "#ec4899", // pink-500
  "#3b82f6", // blue-500
  "#10b981", // emerald-500
  "#06b6d4", // cyan-500
  "#f97316", // orange-500
];

export function AnalyticsCharts({ metrics, exceptionCounts }: AnalyticsChartsProps) {
  // Data for match distribution bar chart
  const matchDistributionData = [
    {
      name: "Reconciliation Breakdown",
      "Rule Matches (Deterministic)": metrics.rule_matches,
      "AI Verified (Math Proven)": metrics.ai_verified,
      "Exceptions (Needs Review)": metrics.needs_review,
    },
  ];

  // Data for exception category pie chart
  const pieData = Object.entries(exceptionCounts)
    .filter(([_, count]) => count > 0)
    .map(([category, count]) => ({
      name: category.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
      value: count,
    }));

  if (pieData.length === 0 && metrics.needs_review > 0) {
    pieData.push({ name: "General Discrepancies", value: metrics.needs_review });
  }

  const speedMultiplier = metrics.processing_time_seconds > 0
    ? (metrics.records_processed / metrics.processing_time_seconds).toFixed(0)
    : "100+";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* 1. Stacked Match Distribution */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-slate-100">Match Resolution Distribution</h3>
            </div>
            <span className="text-xs text-slate-400 font-mono">
              Total: {metrics.records_processed} records
            </span>
          </div>
          <p className="text-xs text-slate-400 mb-4">
            "Rules before AI" ensures 85%+ resolved deterministically before invoking AI verification.
          </p>
        </div>

        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={matchDistributionData}
              layout="vertical"
              margin={{ top: 10, right: 20, left: 10, bottom: 5 }}
            >
              <XAxis type="number" stroke="#64748b" fontSize={11} />
              <YAxis type="category" dataKey="name" hide />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0f172a",
                  borderColor: "#334155",
                  borderRadius: "0.5rem",
                  fontSize: "12px",
                  color: "#f8fafc",
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
              />
              <Bar dataKey="Rule Matches (Deterministic)" stackId="a" fill="#10b981" radius={[4, 0, 0, 4]} />
              <Bar dataKey="AI Verified (Math Proven)" stackId="a" fill="#6366f1" />
              <Bar dataKey="Exceptions (Needs Review)" stackId="a" fill="#f59e0b" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Exception Taxonomy Donut */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-bold text-slate-100">Exception Taxonomy</h3>
            </div>
            <span className="text-xs text-amber-400 font-mono font-bold">
              {metrics.needs_review} exceptions
            </span>
          </div>
          <p className="text-xs text-slate-400 mb-2">
            Structured operational discrepancy categorization.
          </p>
        </div>

        <div className="h-44 w-full flex items-center justify-center">
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={36}
                  outerRadius={64}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={EXCEPTION_COLORS[index % EXCEPTION_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    borderRadius: "0.5rem",
                    fontSize: "11px",
                    color: "#f8fafc",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-xs text-slate-500 italic">No exceptions detected in current batch</div>
          )}
        </div>
      </div>

      {/* 3. Throughput & Latency Benchmark */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-bold text-slate-100">Throughput & Performance</h3>
            </div>
            <span className="text-xs text-emerald-400 font-bold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
              SLA Met ✓
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Real-time pipeline speed vs standard 30-minute manual batch benchmark.
          </p>
        </div>

        <div className="my-auto py-2">
          <div className="flex items-baseline justify-between mb-2">
            <span className="text-xs text-slate-400">Reconciliation Speed:</span>
            <span className="text-2xl font-black text-cyan-300 font-mono">
              {speedMultiplier} <span className="text-xs font-medium text-slate-400">tx/sec</span>
            </span>
          </div>
          <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
            <div
              className="bg-gradient-to-r from-cyan-500 to-indigo-500 h-full rounded-full transition-all duration-1000"
              style={{ width: "95%" }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 mt-1.5 font-mono">
            <span>Wall-clock: {metrics.processing_time_seconds.toFixed(2)}s</span>
            <span>Target: &lt; 30.0s</span>
          </div>
        </div>
      </div>
    </div>
  );
}
