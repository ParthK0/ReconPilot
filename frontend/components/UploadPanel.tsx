"use client";

import React, { useState, useRef } from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  Play,
  Layers,
  Building2,
  X,
  FileText,
} from "lucide-react";
import { API_BASE_URL } from "../lib/api";
import { Button } from "./ui/Button";

interface UploadPanelProps {
  onUploadSuccess: (batchId: string) => void;
  merchants: Array<{
    merchant_type: string;
    display_name: string;
    description: string;
  }>;
}

export function UploadPanel({ onUploadSuccess, merchants }: UploadPanelProps) {
  const [settlementFile, setSettlementFile] = useState<File | null>(null);
  const [bankFile, setBankFile] = useState<File | null>(null);
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [groundTruthFile, setGroundTruthFile] = useState<File | null>(null);
  const [merchantType, setMerchantType] = useState<string>("retail");
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const settlementInputRef = useRef<HTMLInputElement>(null);
  const bankInputRef = useRef<HTMLInputElement>(null);
  const invoiceInputRef = useRef<HTMLInputElement>(null);
  const groundTruthInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settlementFile || !bankFile || !invoiceFile) {
      setUploadError("Please select all three required financial files (Settlement, Bank, and Invoice).");
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("settlement_csv", settlementFile);
    formData.append("bank_csv", bankFile);
    formData.append("invoice_csv", invoiceFile);
    if (groundTruthFile) {
      formData.append("ground_truth_json", groundTruthFile);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/batches?merchant_type=${merchantType}`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
      }

      const result = await response.json();
      onUploadSuccess(result.batch_id);
    } catch (err: any) {
      setUploadError(err.message || "An unexpected error occurred during batch ingestion.");
    } finally {
      setIsUploading(false);
    }
  };

  const uploadSlots = [
    {
      id: "settlement",
      title: "1. Gateway Settlement CSV",
      description: "Net settlement payouts, fees, GST, and TDS from Razorpay",
      file: settlementFile,
      setFile: setSettlementFile,
      ref: settlementInputRef,
      accept: ".csv",
    },
    {
      id: "bank",
      title: "2. Bank Statement CSV",
      description: "Lump-sum bank credits, UTR references, and closing balances",
      file: bankFile,
      setFile: setBankFile,
      ref: bankInputRef,
      accept: ".csv",
    },
    {
      id: "invoice",
      title: "3. ERP Invoices CSV",
      description: "Gross customer billing lines, order IDs, and line items",
      file: invoiceFile,
      setFile: setInvoiceFile,
      ref: invoiceInputRef,
      accept: ".csv",
    },
    {
      id: "ground_truth",
      title: "4. Ground Truth JSON (Optional)",
      description: "Pre-labeled benchmarks for automated precision / recall evaluation",
      file: groundTruthFile,
      setFile: setGroundTruthFile,
      ref: groundTruthInputRef,
      accept: ".json",
    },
  ];

  return (
    <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 shadow-xl backdrop-blur-md space-y-6">
      {/* Header */}
      <div className="border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <UploadCloud className="w-5 h-5" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100">Three-Way Financial Batch Ingestion</h2>
            <p className="text-xs text-slate-400">
              Upload customer ERP registers, payment aggregator settlements, and commercial bank statements
            </p>
          </div>
        </div>
      </div>

      {uploadError && (
        <div
          role="alert"
          className="bg-rose-950/50 border border-rose-800/60 p-4 rounded-xl flex items-start justify-between text-xs text-rose-200"
        >
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{uploadError}</span>
          </div>
          <button
            onClick={() => setUploadError(null)}
            aria-label="Dismiss error notification"
            className="text-rose-400 hover:text-rose-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <form onSubmit={handleUploadSubmit} className="space-y-6">
        {/* Merchant Archetype Profile Selector */}
        <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4">
          <label htmlFor="merchant-profile-select" className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-indigo-400" />
            Target Merchant Archetype (Configures Statutory MDR, GST & TDS Rate Cards)
          </label>
          <select
            id="merchant-profile-select"
            value={merchantType}
            onChange={(e) => setMerchantType(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            {merchants.map((m) => (
              <option key={m.merchant_type} value={m.merchant_type}>
                {m.display_name} — {m.description}
              </option>
            ))}
          </select>
        </div>

        {/* 4 File Dropzone Slots */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {uploadSlots.map((slot) => (
            <div
              key={slot.id}
              className={`p-4 rounded-xl border transition-all duration-150 flex flex-col justify-between gap-3 ${
                slot.file
                  ? "bg-indigo-950/30 border-indigo-500/40"
                  : "bg-slate-950/50 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200">{slot.title}</span>
                  {slot.file ? (
                    <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Selected
                    </span>
                  ) : (
                    <span className="text-[10px] text-slate-500 uppercase font-mono">Required</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                  {slot.description}
                </p>
              </div>

              <input
                ref={slot.ref}
                type="file"
                accept={slot.accept}
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    slot.setFile(e.target.files[0]);
                  }
                }}
                className="hidden"
              />

              {slot.file ? (
                <div className="flex items-center justify-between bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-xs font-mono">
                  <div className="flex items-center gap-2 truncate pr-2">
                    <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                    <span className="truncate text-slate-200">{slot.file.name}</span>
                    <span className="text-slate-500 text-[10px]">({formatFileSize(slot.file.size)})</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => slot.setFile(null)}
                    aria-label={`Remove file ${slot.file.name}`}
                    className="text-slate-400 hover:text-rose-400 p-1"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => slot.ref.current?.click()}
                  leftIcon={<FileSpreadsheet className="w-3.5 h-3.5" />}
                >
                  Choose File
                </Button>
              )}
            </div>
          ))}
        </div>

        {/* Submit Actions */}
        <div className="flex justify-end pt-2">
          <Button
            type="submit"
            variant="primary"
            size="md"
            isLoading={isUploading}
            disabled={!settlementFile || !bankFile || !invoiceFile}
            leftIcon={<Play className="w-4 h-4" />}
          >
            {isUploading ? "Ingesting & Reconciling..." : "Run Autonomous Reconciliation Pipeline"}
          </Button>
        </div>
      </form>
    </div>
  );
}
