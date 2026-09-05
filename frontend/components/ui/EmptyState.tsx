"use client";

import React from "react";
import { FolderSearch } from "lucide-react";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon = <FolderSearch className="w-8 h-8 text-slate-500" />,
  title,
  description,
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center p-8 sm:p-12 rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 backdrop-blur-sm ${className}`}
      role="status"
    >
      <div className="p-3.5 rounded-2xl bg-slate-800/60 border border-slate-700/50 mb-3.5 text-slate-400">
        {icon}
      </div>
      <h3 className="text-sm sm:text-base font-bold text-slate-200">{title}</h3>
      <p className="text-xs sm:text-sm text-slate-400 max-w-sm mt-1 mb-4 leading-relaxed">
        {description}
      </p>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
