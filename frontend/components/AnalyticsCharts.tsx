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
import { BarChart3, PieChart as PieIcon, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "./ui/Card";
import { Skeleton } from "./ui/Skeleton";

interface AnalyticsChartsProps {
  metrics: {
    records_processed: number;
    rule_matches: number;
    ai_verified: number;
    needs_review: number;
    processing_time_seconds: number;
  };
  exceptionCounts: Record<string, number>;
  isLoading?: boolean;
}

const CATEGORY_COLORS = [
  "#6366f1", // indigo-500
  "#f59e0b", // amber-500
  "#ef4444", // red-500
  "#8b5cf6", // purple-500
  "#ec4899", // pink-500
  "#06b6d4", // cyan-500
  "#10b981", // emerald-500
  "#f97316", // orange-500
];

export function AnalyticsCharts({
  metrics,
  exceptionCounts,
  isLoading = false,
}: AnalyticsChartsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-3 w-56" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-64 w-full rounded-xl" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-3 w-56" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-64 w-full rounded-xl" />
          </CardContent>
        </Card>
      </div>
    );
  }

  // Data for reconciliation breakdown bar chart
  const barData = [
    {
      name: "Deterministic Rules",
      count: metrics.rule_matches,
      fill: "#10b981",
    },
    {
      name: "AI Verified Math",
      count: metrics.ai_verified,
      fill: "#818cf8",
    },
    {
      name: "Audit Exceptions",
      count: metrics.needs_review,
      fill: "#f59e0b",
    },
  ];

  // Data for exception category donut chart
  const pieData = Object.entries(exceptionCounts)
    .filter(([_, count]) => count > 0)
    .map(([category, count]) => ({
      name: category.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
      value: count,
    }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      return (
        <div className="bg-slate-900 border border-slate-700/80 p-3 rounded-xl shadow-2xl backdrop-blur-md text-xs space-y-1">
          <p className="font-bold text-slate-200">{label || data.name}</p>
          <p className="text-slate-400 font-mono">
            Count: <span className="font-bold text-slate-100">{data.value}</span>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <section aria-label="Visual Analytics and Operational Breakdown">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Chart 1: Match Waterfall Distribution */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <BarChart3 className="w-4 h-4" aria-hidden="true" />
              </div>
              <CardTitle>Reconciliation Execution Waterfall</CardTitle>
            </div>
            <CardDescription>
              Volume resolved deterministically vs AI forensic verification
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} margin={{ top: 15, right: 15, left: -15, bottom: 20 }}>
                  <XAxis
                    dataKey="name"
                    stroke="#94a3b8"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: "#334155" }}
                  />
                  <YAxis
                    stroke="#94a3b8"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: "#334155" }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {barData.map((entry, index) => (
                      <Cell key={`bar-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Chart 2: Exception Categories Donut */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <PieIcon className="w-4 h-4" aria-hidden="true" />
              </div>
              <CardTitle>Operational Exception Breakdown</CardTitle>
            </div>
            <CardDescription>
              Discrepancies triaged across statutory tax, timing, and fee categories
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 w-full flex items-center justify-center">
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {pieData.map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]}
                          stroke="#0f172a"
                          strokeWidth={2}
                        />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      formatter={(value) => (
                        <span className="text-[11px] font-medium text-slate-300">{value}</span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex flex-col items-center justify-center text-center p-6 text-slate-400">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mb-2" />
                  <p className="text-sm font-semibold text-slate-200">Zero Unresolved Exceptions</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    All processed records successfully matched with 100% precision.
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
