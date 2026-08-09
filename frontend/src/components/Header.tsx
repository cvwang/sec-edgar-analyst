import React from 'react';
import { TrendingUp, Download } from 'lucide-react';

interface HeaderProps {
  onOpenExportModal: () => void;
  canExport: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onOpenExportModal, canExport }) => {
  return (
    <header className="h-16 px-6 bg-white flex items-center justify-between border-b border-gray-200 shadow-xs shrink-0 z-10">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#1A73E8] flex items-center justify-center shadow-md shadow-blue-500/20">
          <TrendingUp className="w-6 h-6 text-white" />
        </div>
        <h1 className="font-heading font-bold text-base text-gray-900 tracking-wide">SEC EDGAR Financial Analyst</h1>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={onOpenExportModal}
          disabled={!canExport}
          className={`px-3.5 py-2 rounded-lg font-medium text-xs flex items-center gap-1.5 transition-all duration-200 ${
            canExport
              ? 'bg-[#1A73E8] hover:bg-[#1557B0] text-white shadow-sm cursor-pointer'
              : 'bg-gray-100 text-gray-400 border border-gray-200 cursor-not-allowed'
          }`}
        >
          <Download className="w-4 h-4" />
          <span>Export GCS Report (HITL)</span>
        </button>
      </div>
    </header>
  );
};
