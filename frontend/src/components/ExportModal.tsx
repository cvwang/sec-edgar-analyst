import React, { useState } from 'react';
import { ShieldAlert, CheckCircle, X, UploadCloud } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  lastResponse: AnalysisResponse | null;
}

export const ExportModal: React.FC<ExportModalProps> = ({ isOpen, onClose, lastResponse }) => {
  const [isExporting, setIsExporting] = useState(false);

  if (!isOpen) return null;

  const derivedTicker = lastResponse?.ticker || (lastResponse?.tickers && lastResponse.tickers.length > 0 ? lastResponse.tickers[0] : 'SEC');
  const ticker = derivedTicker.toUpperCase();
  const year = lastResponse?.requested_years && lastResponse.requested_years.length > 0 ? lastResponse.requested_years[0] : 2023;
  const gcsUri = `gs://fde-sec-edgar-reports/${ticker.toLowerCase()}_${year}_report.md`;

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const res = await fetch('/api/v1/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker,
          current_year: year,
          destination_gcs_uri: gcsUri,
          report_content: lastResponse?.narrative || 'Financial report content.',
          human_approved: true,
        }),
      });

      const data = await res.json();
      alert(`✅ ${data.message}`);
      onClose();
    } catch (err: any) {
      alert(`❌ Export Error: ${err.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-gray-900/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-white rounded-2xl border border-gray-200 p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between border-b border-gray-200 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-700">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-heading font-bold text-base text-gray-900">Human-In-The-Loop Export Stop</h3>
              <p className="text-xs text-gray-500">Explicit human approval required for GCS persistence</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3 bg-gray-50 p-4 rounded-xl border border-gray-200 text-xs">
          <div className="flex justify-between items-center text-gray-700">
            <span className="font-medium text-gray-500">Target Ticker:</span>
            <span className="font-bold text-[#1A73E8] px-2 py-0.5 rounded bg-blue-50 border border-blue-200">{ticker}</span>
          </div>
          <div className="flex justify-between items-center text-gray-700">
            <span className="font-medium text-gray-500">Destination GCS Bucket:</span>
            <span className="font-mono text-[11px] text-[#34A853] bg-white px-2 py-1 rounded border border-gray-200">{gcsUri}</span>
          </div>
          <div className="flex justify-between items-center text-gray-700">
            <span className="font-medium text-gray-500">PII Guardrail:</span>
            <span className="text-[#34A853] flex items-center gap-1 font-medium">
              <CheckCircle className="w-3.5 h-3.5" /> Sanitized & Scrubbed
            </span>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium text-xs border border-gray-300 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="px-5 py-2 rounded-xl bg-[#34A853] hover:bg-emerald-600 text-white font-semibold text-xs flex items-center gap-2 shadow-md transition-all duration-200 cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" />
            <span>{isExporting ? 'Exporting...' : 'Grant Approval & Export'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
