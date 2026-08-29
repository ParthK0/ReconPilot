"use client";

import React, { useState, useRef } from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  Play,
  Layers,
  ArrowRight,
  Shield,
} from "lucide-react";

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
      const response = await fetch(`http://localhost:8000/api/v1/batches?merchant_type=${merchantType}`, {
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
      setUploadError(err.message || "Failed to upload and reconcile batch.");
    } finally {
      setIsUploading(false);
    }
  };

  const renderFileCard = (
    title: string,
    description: string,
    file: File | null,
    setFile: (f: File | null) => void,
    inputRef: React.RefObject<HTMLInputElement>,
    accept: string = ".csv",
    required: boolean = true
  ) => {
    return (
      <div
        onClick={() => inputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-5 cursor-pointer transition-all ${
          file
            ? "border-emerald-500/50 bg-emerald-950/10 hover:border-emerald-400"
            : "border-slate-800 bg-slate-900/40 hover:border-indigo-500/50 hover:bg-slate-900/70"
        }`}
      >
        <input
          type="file"
          ref={inputRef}
          accept={accept}
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              setFile(e.target.files[0]);
              setUploadError(null);
            }
          }}
        />
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-lg ${
                file ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-800 text-slate-400"
              }`}
            >
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-200 text-sm">{title}</span>
                {required && (
                  <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-indigo-950/80 text-indigo-400 border border-indigo-800/40">
                    Required
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">{description}</p>
            </div>
          </div>
          {file ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          ) : (
            <UploadCloud className="w-5 h-5 text-slate-500 flex-shrink-0" />
          )}
        </div>

        {file && (
          <div className="mt-3 pt-3 border-t border-emerald-900/30 flex items-center justify-between text-xs text-slate-300">
            <span className="truncate max-w-[200px] font-mono text-emerald-300">{file.name}</span>
            <span className="text-slate-400">{(file.size / 1024).toFixed(1)} KB</span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl backdrop-blur-md">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 text-xs font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-full">
              Multi-Source Ingestion
            </span>
            <h2 className="text-lg font-bold text-slate-100">Upload 3-Way Reconciliation Batch</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            ReconPilot normalizes headers, calculates statutory rate schedules, and proves AI reasoning mathematically.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs font-medium text-slate-400 whitespace-nowrap">Merchant Profile:</label>
          <select
            value={merchantType}
            onChange={(e) => setMerchantType(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-medium focus:outline-none focus:border-indigo-500"
          >
            {merchants.map((m) => (
              <option key={m.merchant_type} value={m.merchant_type}>
                {m.display_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {uploadError && (
        <div className="mt-4 p-3.5 bg-rose-950/30 border border-rose-800/50 rounded-xl flex items-center gap-3 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
          <span>{uploadError}</span>
        </div>
      )}

      <form onSubmit={handleUploadSubmit} className="mt-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {renderFileCard(
            "1. Razorpay Settlements",
            "Gateway payouts, MDR fees, GST, TDS",
            settlementFile,
            setSettlementFile,
            settlementInputRef
          )}
          {renderFileCard(
            "2. Bank Statement",
            "Corporate bank credits, UTR deposits",
            bankFile,
            setBankFile,
            bankInputRef
          )}
          {renderFileCard(
            "3. ERP Invoices",
            "Billed customer accounts receivable",
            invoiceFile,
            setInvoiceFile,
            invoiceInputRef
          )}
        </div>

        <div className="p-4 bg-slate-950/50 border border-slate-800/60 rounded-xl flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <Shield className="w-4 h-4 text-indigo-400 flex-shrink-0" />
            <span>
              Optional Ground Truth Benchmark: upload labeled ground truth JSON to calculate live Precision, Recall, and Confusion Matrix.
            </span>
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto">
            <button
              type="button"
              onClick={() => groundTruthInputRef.current?.click()}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg transition-colors font-medium"
            >
              {groundTruthFile ? groundTruthFile.name : "Attach Ground Truth (Optional)"}
            </button>
            <input
              type="file"
              ref={groundTruthInputRef}
              accept=".json"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setGroundTruthFile(e.target.files[0]);
                }
              }}
            />

            <button
              type="submit"
              disabled={isUploading || !settlementFile || !bankFile || !invoiceFile}
              className="flex-1 md:flex-initial px-6 py-2 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-500 text-white font-semibold text-xs rounded-lg shadow-lg shadow-indigo-600/20 transition-all flex items-center justify-center gap-2"
            >
              {isUploading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Processing Pipeline...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Execute 3-Way Reconciliation</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
