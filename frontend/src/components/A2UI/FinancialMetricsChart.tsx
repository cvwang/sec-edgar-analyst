import React from 'react';
import { useFetchMetrics, useFetchPeerMetrics } from '../../hooks/useQueries';

interface FinancialMetricsChartProps {
  ticker: any;
  startYear: any;
  endYear: any;
  metricType?: 'all' | 'revenue' | 'net_income' | 'operating_margin';
}

interface MiniBarChartProps {
  label: string;
  startVal: number;
  endVal: number;
  startLabel: string;
  endLabel: string;
  formattedStart: string;
  formattedEnd: string;
  changeLabel: string;
  trend: 'up' | 'down' | 'neutral';
}

const MiniBarChart: React.FC<MiniBarChartProps> = ({
  label,
  startVal,
  endVal,
  startLabel,
  endLabel,
  formattedStart,
  formattedEnd,
  changeLabel,
  trend,
}) => {
  const allPositive = startVal >= 0 && endVal >= 0;
  const baselineY = allPositive ? 75 : 50;
  const chartHeight = allPositive ? 55 : 35;
  const barWidth = 22;

  const maxAbs = Math.max(Math.abs(startVal), Math.abs(endVal), 1);
  const h1 = (Math.abs(startVal) / maxAbs) * chartHeight;
  const h2 = (Math.abs(endVal) / maxAbs) * chartHeight;

  let y1 = baselineY;
  const height1 = h1;
  if (startVal >= 0) {
    y1 = baselineY - h1;
  }

  let y2 = baselineY;
  const height2 = h2;
  if (endVal >= 0) {
    y2 = baselineY - h2;
  }

  const isUp = trend === 'up';
  const isDown = trend === 'down';

  const barColor1 = 'fill-gray-300 hover:fill-gray-400 transition-colors duration-200';
  const barColor2 = isUp
    ? 'fill-[#34A853] hover:fill-emerald-600 transition-colors duration-200'
    : isDown
    ? 'fill-[#EA4335] hover:fill-rose-600 transition-colors duration-200'
    : 'fill-[#1A73E8] hover:fill-[#1557B0] transition-colors duration-200';

  const labelY1 = startVal >= 0 ? y1 - 6 : y1 + height1 + 12;
  const labelY2 = endVal >= 0 ? y2 - 6 : y2 + height2 + 12;

  return (
    <div className="flex flex-col items-center p-4 border border-gray-200 rounded-xl bg-white hover:border-blue-300 transition-all duration-200 flex-1 min-w-[150px] shadow-xs">
      <span className="text-[10px] uppercase font-bold tracking-wider text-gray-500 mb-2">
        {label}
      </span>
      <svg width="130" height="110" className="overflow-visible mt-1">
        {/* Baseline Grid Line */}
        <line x1="0" y1={baselineY} x2="130" y2={baselineY} className="stroke-gray-300 stroke-1" />

        {!allPositive && (
          <line
            x1="0"
            y1={baselineY}
            x2="130"
            y2={baselineY}
            className="stroke-gray-400 stroke-1 stroke-dasharray-2"
          />
        )}

        {/* Bar 1 (Start Year) */}
        <rect
          x="22"
          y={y1}
          width={barWidth}
          height={Math.max(height1, 2)}
          rx="4"
          className={barColor1}
        />
        <text
          x={22 + barWidth / 2}
          y={labelY1}
          textAnchor="middle"
          className="text-[10px] font-semibold fill-gray-700 font-mono"
        >
          {formattedStart}
        </text>
        <text
          x={22 + barWidth / 2}
          y="95"
          textAnchor="middle"
          className="text-[9px] fill-gray-500 font-medium"
        >
          {startLabel}
        </text>

        {/* Bar 2 (End Year) */}
        <rect
          x="80"
          y={y2}
          width={barWidth}
          height={Math.max(height2, 2)}
          rx="4"
          className={barColor2}
        />
        <text
          x={80 + barWidth / 2}
          y={labelY2}
          textAnchor="middle"
          className="text-[10px] font-bold fill-gray-900 font-mono"
        >
          {formattedEnd}
        </text>
        <text
          x={80 + barWidth / 2}
          y="95"
          textAnchor="middle"
          className="text-[9px] fill-gray-500 font-medium"
        >
          {endLabel}
        </text>
      </svg>
      <span
        className={`text-[10px] font-bold mt-4 px-2 py-0.5 rounded-full inline-flex items-center gap-0.5 ${
          isUp
            ? 'text-[#34A853] bg-emerald-50 border border-emerald-200'
            : isDown
            ? 'text-[#EA4335] bg-rose-50 border border-rose-200'
            : 'text-gray-700 bg-gray-100 border border-gray-300'
        }`}
      >
        {changeLabel}
      </span>
    </div>
  );
};

interface FinancialMetricsChartProps {
  ticker: any;
  peerTicker?: any;
  startYear: any;
  endYear: any;
  metricType?: 'all' | 'revenue' | 'net_income' | 'operating_margin';
}

export const FinancialMetricsChart: React.FC<FinancialMetricsChartProps> = ({
  ticker,
  peerTicker,
  startYear,
  endYear,
  metricType = 'all',
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

  const isPeerMode = Boolean(safePeerTicker && safePeerTicker !== safeTicker);
  const safeStartYear = startYear ? String(startYear).trim() : '2022';
  const safeEndYear = endYear ? String(endYear).trim() : '2023';

  const singleMetrics = useFetchMetrics(safeTicker, safeStartYear, safeEndYear);
  const peerMetrics = useFetchPeerMetrics(safeTicker, safePeerTicker, safeEndYear);

  if (isPeerMode) {
    const { data: pData, isLoading: pLoading, error: pError } = peerMetrics;
    if (pLoading) {
      return (
        <div className="w-full flex items-center justify-center p-6 border border-dashed border-gray-300 rounded-xl bg-gray-50">
          <div className="flex flex-col items-center gap-2">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#1A73E8] border-t-transparent" />
            <span className="text-xs text-gray-500 animate-pulse">Generating peer comparison bar charts...</span>
          </div>
        </div>
      );
    }

    if (pError || !pData?.primary || !pData?.peer) {
      return (
        <div className="text-xs text-[#EA4335] p-3 border rounded-xl border-rose-200 bg-rose-50">
          Failed to fetch peer chart metrics for {safeTicker} vs {safePeerTicker}.
        </div>
      );
    }

    const { primary, peer } = pData;
    const yrShort = safeEndYear.slice(-2);
    const showRevenue = metricType === 'all' || metricType === 'revenue';
    const showNetIncome = metricType === 'all' || metricType === 'net_income';
    const showMargin = metricType === 'all' || metricType === 'operating_margin';

    const revDiff = primary.revenue - peer.revenue;
    const revRatio = peer.revenue > 0 ? (primary.revenue / peer.revenue).toFixed(1) : 'N/A';
    const revRatioPeer = primary.revenue > 0 ? (peer.revenue / primary.revenue).toFixed(1) : 'N/A';

    const marginDiffBps = Math.round((primary.operating_margin - peer.operating_margin) * 100);

    const netDiff = primary.net_income - peer.net_income;
    const netRatio = peer.net_income > 0 ? (primary.net_income / peer.net_income).toFixed(1) : 'N/A';
    const netRatioPeer = primary.net_income > 0 ? (peer.net_income / primary.net_income).toFixed(1) : 'N/A';

    return (
      <div className="my-3 flex flex-col gap-3">
        <div className="flex flex-row gap-3 flex-wrap w-full">
          {showRevenue && (
            <MiniBarChart
              label="Revenue"
              startVal={primary.revenue || 0}
              endVal={peer.revenue || 0}
              startLabel={`'${yrShort} ${primary.ticker}`}
              endLabel={`'${yrShort} ${peer.ticker}`}
              formattedStart={`$${((primary.revenue || 0) / 1e9).toFixed(1)}B`}
              formattedEnd={`$${((peer.revenue || 0) / 1e9).toFixed(1)}B`}
              changeLabel={revDiff >= 0 ? `${primary.ticker} +${revRatio}x` : `${peer.ticker} +${revRatioPeer}x`}
              trend={revDiff >= 0 ? 'up' : 'down'}
            />
          )}
          {showMargin && (
            <MiniBarChart
              label="Operating Margin"
              startVal={primary.operating_margin || 0}
              endVal={peer.operating_margin || 0}
              startLabel={`'${yrShort} ${primary.ticker}`}
              endLabel={`'${yrShort} ${peer.ticker}`}
              formattedStart={`${(primary.operating_margin || 0).toFixed(1)}%`}
              formattedEnd={`${(peer.operating_margin || 0).toFixed(1)}%`}
              changeLabel={marginDiffBps >= 0 ? `${primary.ticker} +${marginDiffBps} bps` : `${peer.ticker} +${Math.abs(marginDiffBps)} bps`}
              trend={marginDiffBps >= 0 ? 'up' : 'down'}
            />
          )}
          {showNetIncome && (
            <MiniBarChart
              label="Net Income"
              startVal={primary.net_income || 0}
              endVal={peer.net_income || 0}
              startLabel={`'${yrShort} ${primary.ticker}`}
              endLabel={`'${yrShort} ${peer.ticker}`}
              formattedStart={`$${((primary.net_income || 0) / 1e9).toFixed(1)}B`}
              formattedEnd={`$${((peer.net_income || 0) / 1e9).toFixed(1)}B`}
              changeLabel={netDiff >= 0 ? `${primary.ticker} +${netRatio}x` : `${peer.ticker} +${netRatioPeer}x`}
              trend={netDiff >= 0 ? 'up' : 'down'}
            />
          )}
        </div>
      </div>
    );
  }

  const { data, isLoading, error } = singleMetrics;

  if (isLoading) {
    return (
      <div className="w-full flex items-center justify-center p-6 border border-dashed border-gray-300 rounded-xl bg-gray-50">
        <div className="flex flex-col items-center gap-2">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#1A73E8] border-t-transparent" />
          <span className="text-xs text-gray-500 animate-pulse">Generating SVG chart visuals...</span>
        </div>
      </div>
    );
  }

  if (error || !data?.metrics?.start_period || !data?.metrics?.end_period || !data?.metrics?.variances) {
    return (
      <div className="text-xs text-[#EA4335] p-3 border rounded-xl border-rose-200 bg-rose-50">
        Failed to fetch chart metrics for {safeTicker}.
      </div>
    );
  }

  const { start_period, end_period, variances } = data.metrics;

  const showRevenue = metricType === 'all' || metricType === 'revenue';
  const showNetIncome = metricType === 'all' || metricType === 'net_income';
  const showMargin = metricType === 'all' || metricType === 'operating_margin';

  const startYrShort = safeStartYear.slice(-2);
  const endYrShort = safeEndYear.slice(-2);

  return (
    <div className="my-3 flex flex-col gap-3">
      <div className="flex flex-row gap-3 flex-wrap w-full">
        {showRevenue && (
          <MiniBarChart
            label="Revenue"
            startVal={start_period.revenue || 0}
            endVal={end_period.revenue || 0}
            startLabel={`'${startYrShort}`}
            endLabel={`'${endYrShort}`}
            formattedStart={`$${((start_period.revenue || 0) / 1e9).toFixed(1)}B`}
            formattedEnd={`$${((end_period.revenue || 0) / 1e9).toFixed(1)}B`}
            changeLabel={`${variances.revenue_yoy_change_percent > 0 ? '+' : ''}${variances.revenue_yoy_change_percent}%`}
            trend={variances.revenue_yoy_change_percent > 0 ? 'up' : variances.revenue_yoy_change_percent < 0 ? 'down' : 'neutral'}
          />
        )}
        {showMargin && (
          <MiniBarChart
            label="Operating Margin"
            startVal={start_period.operating_margin || 0}
            endVal={end_period.operating_margin || 0}
            startLabel={`'${startYrShort}`}
            endLabel={`'${endYrShort}`}
            formattedStart={`${(start_period.operating_margin || 0).toFixed(1)}%`}
            formattedEnd={`${(end_period.operating_margin || 0).toFixed(1)}%`}
            changeLabel={`${variances.operating_margin_yoy_change_bps > 0 ? '+' : ''}${variances.operating_margin_yoy_change_bps} bps`}
            trend={variances.operating_margin_yoy_change_bps > 0 ? 'up' : variances.operating_margin_yoy_change_bps < 0 ? 'down' : 'neutral'}
          />
        )}
        {showNetIncome && (
          <MiniBarChart
            label="Net Income"
            startVal={start_period.net_income || 0}
            endVal={end_period.net_income || 0}
            startLabel={`'${startYrShort}`}
            endLabel={`'${endYrShort}`}
            formattedStart={`$${((start_period.net_income || 0) / 1e9).toFixed(1)}B`}
            formattedEnd={`$${((end_period.net_income || 0) / 1e9).toFixed(1)}B`}
            changeLabel={`${variances.net_income_yoy_change_percent > 0 ? '+' : ''}${variances.net_income_yoy_change_percent}%`}
            trend={variances.net_income_yoy_change_percent > 0 ? 'up' : variances.net_income_yoy_change_percent < 0 ? 'down' : 'neutral'}
          />
        )}
      </div>
    </div>
  );
};
