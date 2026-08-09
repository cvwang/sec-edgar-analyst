import React from 'react';
import { useFetchMetrics } from '../../hooks/useQueries';

interface FinancialInlineTableProps {
  ticker: any;
  startYear: any;
  endYear: any;
}

export const FinancialInlineTable: React.FC<FinancialInlineTableProps> = ({
  ticker,
  startYear,
  endYear,
}) => {
  const safeTicker = typeof ticker === 'string' ? ticker.trim().toUpperCase() : (Array.isArray(ticker) && ticker.length > 0 ? String(ticker[0]).trim().toUpperCase() : (ticker ? String(ticker).trim().toUpperCase() : ''));
  const safeStartYear = startYear ? String(startYear).trim() : '2022';
  const safeEndYear = endYear ? String(endYear).trim() : '2023';

  if (!safeTicker) {
    return (
      <div className="my-3 p-3 text-xs rounded-xl bg-amber-50 border border-amber-200 text-amber-800">
        Company ticker not specified for financial metrics table.
      </div>
    );
  }

  const { data, isLoading, error } = useFetchMetrics(safeTicker, safeStartYear, safeEndYear);

  if (isLoading) {
    return (
      <div className="w-full p-4 my-3 rounded-xl bg-gray-100 border border-gray-200 text-xs text-gray-600 animate-pulse flex items-center gap-2">
        <div className="w-3 h-3 rounded-full border-2 border-[#1A73E8] border-t-transparent animate-spin" />
        <span>Fetching deterministic financial metrics for {safeTicker}...</span>
      </div>
    );
  }

  if (error || !data?.metrics?.start_period || !data?.metrics?.end_period || !data?.metrics?.variances) {
    return (
      <div className="my-3 p-3 text-xs rounded-xl bg-rose-50 border border-rose-200 text-[#EA4335]">
        Failed to load financial metrics table for {safeTicker}.
      </div>
    );
  }

  const { start_period, end_period, variances } = data.metrics;

  const revVal = variances.revenue_yoy_change_percent;
  const isRevGrowth = revVal > 0;
  const isRevDecline = revVal < 0;

  const marginVal = variances.operating_margin_yoy_change_bps;
  const isMarginGrowth = marginVal > 0;
  const isMarginDecline = marginVal < 0;

  const netVal = variances.net_income_yoy_change_percent;
  const isNetGrowth = netVal > 0;
  const isNetDecline = netVal < 0;

  return (
    <div className="my-4 border border-gray-200 rounded-xl bg-white overflow-hidden shadow-xs">
      <div className="px-4 py-2.5 bg-gray-100 border-b border-gray-200 flex items-center justify-between">
        <span className="font-heading font-semibold text-xs text-[#1A73E8]">
          📊 {safeTicker.toUpperCase()} Financial Metrics Table
        </span>
        <span className="text-[10px] font-mono text-gray-500">
          FY {safeStartYear} → FY {safeEndYear}
        </span>
      </div>
      <table className="w-full text-xs text-left border-collapse">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50 text-gray-600 font-semibold text-[11px]">
            <th className="p-3">Metric</th>
            <th className="p-3 text-right">FY {safeStartYear}</th>
            <th className="p-3 text-right">FY {safeEndYear}</th>
            <th className="p-3 text-right">YoY Variance</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 text-gray-800">
          <tr className="hover:bg-gray-50 transition-colors">
            <td className="p-3 font-medium">Revenue</td>
            <td className="p-3 text-right font-mono">${((start_period.revenue || 0) / 1e9).toFixed(2)}B</td>
            <td className="p-3 text-right font-mono">${((end_period.revenue || 0) / 1e9).toFixed(2)}B</td>
            <td className={`p-3 text-right font-bold font-mono ${
              isRevGrowth ? 'text-[#34A853]' : isRevDecline ? 'text-[#EA4335]' : 'text-gray-500'
            }`}>
              {isRevGrowth ? '+' : ''}{revVal}%
            </td>
          </tr>
          <tr className="hover:bg-gray-50 transition-colors">
            <td className="p-3 font-medium">Operating Margin</td>
            <td className="p-3 text-right font-mono">{(start_period.operating_margin || 0).toFixed(2)}%</td>
            <td className="p-3 text-right font-mono">{(end_period.operating_margin || 0).toFixed(2)}%</td>
            <td className={`p-3 text-right font-bold font-mono ${
              isMarginGrowth ? 'text-[#34A853]' : isMarginDecline ? 'text-[#EA4335]' : 'text-gray-500'
            }`}>
              {isMarginGrowth ? '+' : ''}{marginVal} bps
            </td>
          </tr>
          <tr className="hover:bg-gray-50 transition-colors">
            <td className="p-3 font-medium">Net Income</td>
            <td className="p-3 text-right font-mono">${((start_period.net_income || 0) / 1e9).toFixed(2)}B</td>
            <td className="p-3 text-right font-mono">${((end_period.net_income || 0) / 1e9).toFixed(2)}B</td>
            <td className={`p-3 text-right font-bold font-mono ${
              isNetGrowth ? 'text-[#34A853]' : isNetDecline ? 'text-[#EA4335]' : 'text-gray-500'
            }`}>
              {isNetGrowth ? '+' : ''}{netVal}%
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};
