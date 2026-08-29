"use client";

import React, { useState } from "react";
import {
  X,
  UserCheck,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Send,
} from "lucide-react";
import { ExceptionItem } from "./ExceptionGrid";

interface ReviewModalProps {
  exception: ExceptionItem | null;
  onClose: () => void;
  onSubmitReview: (
    exceptionId: string,
    action: "approve" | "reject",
    reason: string,
    notes: string
  ) => Promise<void>;
}

export function ReviewModal({ exception, onClose, onSubmitReview }: ReviewModalProps) {
  const [action, setAction] = useState<"approve" | "reject">("approve");
  const [reason, setReason] = useState<string>("Manual rate schedule override");
  const [notes, setNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  if (!exception) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmitReview(exception.exception_id, action, reason, notes);
      onClose();
    } catch (err) {
      console.error("Failed to submit review", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <UserCheck className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Human Controller Review</h3>
              <p className="text-xs text-slate-400">
                Exception ID: <span className="font-mono">{exception.exception_id.substring(0, 12)}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1.5 font-mono text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Category:</span>
              <span className="text-amber-400 font-bold uppercase">{exception.category}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Order / Record ID:</span>
              <span className="text-slate-200">{exception.order_id || exception.source_record_id}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Amount:</span>
              <span className="text-slate-200">
                ₹{exception.amount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </span>
            </div>
            {exception.discrepancy_amount && (
              <div className="flex justify-between text-rose-400">
                <span>Variance:</span>
                <span>₹{exception.discrepancy_amount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
              </div>
            )}
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-2">Review Decision</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setAction("approve")}
                className={`py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-2 transition-all ${
                  action === "approve"
                    ? "bg-emerald-950/60 border-emerald-500 text-emerald-300 shadow-md shadow-emerald-900/20"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Approve Match</span>
              </button>

              <button
                type="button"
                onClick={() => setAction("reject")}
                className={`py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-2 transition-all ${
                  action === "reject"
                    ? "bg-rose-950/60 border-rose-500 text-rose-300 shadow-md shadow-rose-900/20"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                <XCircle className="w-4 h-4 text-rose-400" />
                <span>Reject & Dispute</span>
              </button>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">Resolution Reason</label>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="Manual rate schedule override">Manual rate schedule override</option>
              <option value="One-off commercial discount accepted">One-off commercial discount accepted</option>
              <option value="Known banking clearing delay">Known banking clearing delay</option>
              <option value="Clawback or chargeback accepted">Clawback or chargeback accepted</option>
              <option value="Invalid transaction / fraud dispute">Invalid transaction / fraud dispute</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Controller Notes (Recorded into Feedback Memory)
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Provide exact rationale to train episodic memory for future similar discrepancies..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition-all flex items-center gap-2 shadow-lg shadow-indigo-600/20"
            >
              {isSubmitting ? (
                <span>Submitting...</span>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Submit & Save to Memory</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
