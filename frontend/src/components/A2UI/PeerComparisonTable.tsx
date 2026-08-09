import React from 'react';
import { useFetchPeerMetrics } from '../../hooks/useQueries';

interface PeerComparisonTableProps {
  ticker: any;
  peerTicker: any;
  year: any;
}

export const PeerComparisonTable: React.FC<PeerComparisonTableProps> = ({
  ticker,
  peerTicker,
  year,
}) => {
  let rawTicker = typeof ticker === 'string' ? ticker.trim().toUpperCase() : (Array.isArray(ticker) && ticker.length > 0 ? String(ticker[0]).trim().toUpperCase() : (ticker ? String(ticker).trim().toUpperCase() : ''));
  let rawPeer = typeof peerTicker === 'string' ? peerTicker.trim().toUpperCase() : (Array.isArray(peerTicker) && peerTicker.length > 0 ? String(peerTicker[0]).trim().toUpperCase() : (peerTicker ? String(peerTicker).trim().toUpperCase() : ''));

  let safeTicker = rawTicker;
  let safePeerTicker = rawPeer;

  if (rawTicker.includes(',')) {
    const parts = rawTicker.split(',').map((s) => s.trim().toUpperCase());
    safeTicker = parts[0];
    if (parts[1]) safePeerTicker = parts[1];
  }

  const safeYear = year ? String(year).trim() : '2023';

  if (!safeTicker || !safePeerTicker || safeTicker === safePeerTicker) {
    return (
      <div className="my-3 p-3 text-xs rounded-xl bg-amber-50 border border-amber-200 text-amber-800">
        Peer comparison table requires two distinct company tickers (e.g. ticker: "{safeTicker || 'PRIMARY'}", peer_ticker: "PEER").
      </div>
    );
  }

  const { data, isLoading, error } = useFetchPeerMetrics(safeTicker, safePeerTicker, safeYear);

  if (isLoading) {
    return (
      <div className="w-full p-4 my-3 rounded-xl bg-gray-100 border border-gray-200 text-xs text-gray-600 animate-pulse flex items-center gap-2">
        <div className="w-3 h-3 rounded-full border-2 border-[#1A73E8] border-t-transparent animate-spin" />
        <span>Fetching peer comparison metrics for {safeTicker} vs {safePeerTicker} ({safeYear})...</span>
      </div>
    );
  }

  if (error || !data?.primary || !data?.peer) {
    return (
      <div className="my-3 p-3 text-xs rounded-xl bg-rose-50 border border-rose-200 text-[#EA4335]">
        Failed to load peer comparison table for {safeTicker} vs {safePeerTicker}.
      </div>
    );
  }

  const { primary, peer } = data;

  const revDiff = primary.revenue - peer.revenue;
  const isPrimaryRevLarger = revDiff > 0;
  const revRatio = peer.revenue > 0 ? (primary.revenue / peer.revenue).toFixed(1) : 'N/A';
  const revRatioPeer = primary.revenue > 0 ? (peer.revenue / primary.revenue).toFixed(1) : 'N/A';

  const marginDiffBps = Math.round((primary.operating_margin - peer.operating_margin) * 100);
  const isPrimaryMarginHigher = marginDiffBps > 0;

  const netDiff = primary.net_income - peer.net_income;
  const isPrimaryNetLarger = netDiff > 0;
  const netRatio = peer.net_income > 0 ? (primary.net_income / peer.net_income).toFixed(1) : 'N/A';
  const netRatioPeer = primary.net_income > 0 ? (peer.net_income / primary.net_income).toFixed(1) : 'N/A';

  return (
    <div className="my-4 border border-gray-200 rounded-xl bg-white overflow-hidden shadow-xs">
      <div className="px-4 py-2.5 bg-gray-100 border-b border-gray-200 flex items-center justify-between">
        <span className="font-heading font-semibold text-xs text-[#1A73E8]">
          ⚔️ {primary.ticker} vs. {peer.ticker} Side-by-Side Financial Comparison
        </span>
        <span className="text-[10px] font-mono text-gray-500">
          FY {safeYear}
        </span>
      </div>
      <table className="w-full text-xs text-left border-collapse">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50 text-gray-600 font-semibold text-[11px]">
            <th className="p-3">Metric</th>
            <th className="p-3 text-right">{primary.ticker}</th>
            <th className="p-3 text-right">{peer.ticker}</th>
            <th className="p-3 text-right">Comparison Variance</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 text-gray-800">
          <tr className="hover:bg-gray-50 transition-colors">
            <td className="p-3 font-medium">Revenue</td>
            <td className="p-3 text-right font-mono font-semibold">${((primary.revenue || 0) / 1e9).toFixed(2)}B</td>
            <td className="p-3 text-right font-mono font-semibold">${((peer.revenue || 0) / 1e9).toFixed(2)}B</td>
            <td className="p-3 text-right font-mono text-gray-700">
              {isPrimaryRevLarger ? `${primary.ticker} +$${(revDiff / 1e9).toFixed(2)}B (${revRatio}x)` : `${peer.ticker} +$${(Math.abs(revDiff) / 1e9).toFixed(2)}B (${revRatioPeer}x)`}
            </td>
          </tr>
          <tr className="hover:bg-gray-50 transition-colors">
            <td className="p-3 font-medium">Operating Income</td>
            <td className="p-3 text-right font-mono">${((primary.operating_income || 0) / 1e9).toFixed(2)}B</td>
            <td className="p-3 text-right font-mono">${((peer.operating_income || 0) / 1e9).toFixed(2)}B</td>
            <td className="p-3 text-right font-mono text-gray-700">
              {primary.operating_income > peer.operating_income ? `${primary.ticker} +$${((primary.operating_income - peer.operating_income) / 1e9).toFixed(2)}B` : `${peer.ticker} +$${((peer.operating_income - primary.operating_income) / 1e9).toFixed(2)}B`}
            </td>
          </tr>
          <tr className="hover:bg-gray-50 transition-colors">
            <td className="p-3 font-medium">Operating Margin</td>
            <td className="p-3 text-right font-mono">{(primary.operating_margin || 0).toFixed(2)}%</td>
            <td className="p-3 text-right font-mono">{(peer.operating_margin || 0).toFixed(2)}%</td>
            <td className={`p-3 text-right font-bold font-mono ${isPrimaryMarginHigher ? 'text-[#34A853]' : 'text-[#EA4335]'}`}>
              {isPrimaryMarginHigher ? `${primary.ticker} +${marginDiffBps} bps` : `${peer.ticker} +${Math.abs(marginDiffBps)} bps`}
            </td>
          </tr>
          <tr className="hover:bg-gray-50 transition-colors">
            <td className="p-3 font-medium">Net Income</td>
            <td className="p-3 text-right font-mono font-semibold">${((primary.net_income || 0) / 1e9).toFixed(2)}B</td>
            <td className="p-3 text-right font-mono font-semibold">${((peer.net_income || 0) / 1e9).toFixed(2)}B</td>
            <td className="p-3 text-right font-mono text-gray-700">
              {isPrimaryNetLarger ? `${primary.ticker} +$${(netDiff / 1e9).toFixed(2)}B (${netRatio}x)` : `${peer.ticker} +$${(Math.abs(netDiff) / 1e9).toFixed(2)}B (${netRatioPeer}x)`}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};
