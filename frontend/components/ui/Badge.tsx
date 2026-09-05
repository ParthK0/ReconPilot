"use client";

import React from "react";

export type BadgeVariant =
  | "default"
  | "secondary"
  | "success"
  | "warning"
  | "danger"
  | "ai"
  | "outline"
  | "neutral";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: "sm" | "md";
  dot?: boolean;
}

export function Badge({
  children,
  variant = "default",
  size = "md",
  dot = false,
  className = "",
  ...props
}: BadgeProps) {
  const variantStyles: Record<BadgeVariant, string> = {
    default: "bg-indigo-950/80 text-indigo-300 border-indigo-800/50",
    secondary: "bg-slate-800/90 text-slate-300 border-slate-700/60",
    success: "bg-emerald-950/80 text-emerald-300 border-emerald-800/50",
    warning: "bg-amber-950/80 text-amber-300 border-amber-800/50",
    danger: "bg-rose-950/80 text-rose-300 border-rose-800/50",
    ai: "bg-gradient-to-r from-indigo-950/90 to-purple-950/90 text-purple-300 border-purple-800/50",
    outline: "bg-transparent text-slate-300 border-slate-700",
    neutral: "bg-slate-900 text-slate-400 border-slate-800",
  };

  const dotStyles: Record<BadgeVariant, string> = {
    default: "bg-indigo-400",
    secondary: "bg-slate-400",
    success: "bg-emerald-400",
    warning: "bg-amber-400",
    danger: "bg-rose-400",
    ai: "bg-purple-400",
    outline: "bg-slate-400",
    neutral: "bg-slate-500",
  };

  const sizeStyles = {
    sm: "text-[10px] px-2 py-0.5 tracking-wider",
    md: "text-xs px-2.5 py-1 tracking-normal",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold rounded-full border shadow-sm transition-colors ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      {...props}
    >
      {dot && (
        <span
          className={`w-1.5 h-1.5 rounded-full animate-pulse ${dotStyles[variant]}`}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}
