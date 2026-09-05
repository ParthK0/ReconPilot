"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  UserCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Send,
} from "lucide-react";
import { ExceptionItem } from "./ExceptionGrid";
import { Button } from "./ui/Button";

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

  // ESC key listener for accessibility
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

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
    <div
      className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <UserCheck className="w-4 h-4" aria-hidden="true" />
            </div>
            <div>
              <h2 id="modal-title" className="text-sm sm:text-base font-bold text-slate-100">
                Human Controller Audit Review
              </h2>
              <p className="text-xs text-slate-400">
                Exception: <span className="font-mono text-slate-300">{exception.exception_id.substring(0, 14)}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close review dialog"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {/* Action Toggle */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Resolution Disposition
            </label>
            <div className="grid grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => setAction("approve")}
                className={`py-2 px-3 rounded-xl border flex items-center justify-center gap-2 font-semibold transition-all ${
                  action === "approve"
                    ? "bg-emerald-950 text-emerald-300 border-emerald-600 shadow-md shadow-emerald-950/40"
                    : "bg-slate-950/60 text-slate-400 border-slate-800 hover:bg-slate-800/60"
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                Approve & Match
              </button>
              <button
                type="button"
                onClick={() => setAction("reject")}
                className={`py-2 px-3 rounded-xl border flex items-center justify-center gap-2 font-semibold transition-all ${
                  action === "reject"
                    ? "bg-rose-950 text-rose-300 border-rose-600 shadow-md shadow-rose-950/40"
                    : "bg-slate-950/60 text-slate-400 border-slate-800 hover:bg-slate-800/60"
                }`}
              >
                <XCircle className="w-3.5 h-3.5" />
                Reject Match
              </button>
            </div>
          </div>

          {/* Justification Reason Dropdown */}
          <div>
            <label htmlFor="reason-select" className="block text-xs font-semibold text-slate-300 mb-1.5">
              Primary Accounting Justification
            </label>
            <select
              id="reason-select"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="Manual rate schedule override">Manual rate schedule override (Contractual discount)</option>
              <option value="Section 194-O TDS withholding confirmed">Section 194-O TDS withholding confirmed (1% statutory)</option>
              <option value="T+2 clearing cutoff weekend shift">T+2 clearing cutoff weekend shift (Banking delay)</option>
              <option value="Temporary risk escrow hold release">Temporary risk escrow hold release (Dispute resolved)</option>
              <option value="Forensic anomaly - requires merchant inquiry">Forensic anomaly - requires merchant inquiry</option>
            </select>
          </div>

          {/* Controller Audit Notes */}
          <div>
            <label htmlFor="review-notes" className="block text-xs font-semibold text-slate-300 mb-1.5">
              Controller Audit Notes (Logs to Feedback Memory)
            </label>
            <textarea
              id="review-notes"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Document the exact basis for approval or adjustment..."
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
              required
            />
          </div>

          {/* Actions */}
          <div className="pt-3 border-t border-slate-800/80 flex items-center justify-end gap-2.5">
            <Button type="button" variant="ghost" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              leftIcon={<Send className="w-3.5 h-3.5" />}
            >
              Save Audit Decision
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
