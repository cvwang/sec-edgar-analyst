import React, { useState, useEffect } from 'react';
import { ArrowUpRight, ArrowDownRight, Minus, AlertTriangle } from 'lucide-react';
import { FinancialInlineTable } from './FinancialInlineTable';
import { FinancialMetricsChart } from './FinancialMetricsChart';
import { PeerComparisonTable } from './PeerComparisonTable';

interface A2UIComponent {
  id: string;
  component: string;
  children?: string[];
  text?: string;
  label?: string;
  value?: string;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  ticker?: any;
  peer_ticker?: any;
  start_year?: any;
  end_year?: any;
  year?: any;
  variant?: 'title' | 'subtitle' | 'body' | 'caption';
  metric_type?: 'all' | 'revenue' | 'net_income' | 'operating_margin';
}

interface A2UIMessage {
  version: string;
  createSurface?: {
    surfaceId: string;
    catalogId: string;
  };
  updateComponents?: {
    surfaceId: string;
    components: A2UIComponent[];
  };
}

interface A2UISurfaceProps {
  payload: string;
  isMessageRunning?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class A2UIErrorBoundary extends React.Component<{ children: React.ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('A2UI Component Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="my-3 p-3 border border-rose-200 bg-rose-50 rounded-xl text-xs flex flex-col gap-1 text-[#EA4335]">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle className="h-4 w-4" />
            <span>A2UI Component Render Error</span>
          </div>
          <p className="text-gray-600 text-[11px]">{this.state.error?.message || 'Unable to render visual component.'}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

const A2UISurfaceContent: React.FC<A2UISurfaceProps> = ({
  payload,
  isMessageRunning = false,
}) => {
  const [error, setError] = useState<string | null>(null);
  const [componentsMap, setComponentsMap] = useState<Record<string, A2UIComponent>>({});

  useEffect(() => {
    try {
      setError(null);
      const parsed = JSON.parse(payload);

      if (!Array.isArray(parsed)) {
        throw new Error('A2UI payload must be a JSON array of messages.');
      }

      const updateMsg = parsed.find((msg: A2UIMessage) => msg.updateComponents);
      if (!updateMsg || !updateMsg.updateComponents) {
        throw new Error("A2UI payload is missing an 'updateComponents' message.");
      }

      const comps = updateMsg.updateComponents.components;
      if (!Array.isArray(comps)) {
        throw new Error("A2UI 'components' must be an array.");
      }

      const map: Record<string, A2UIComponent> = {};
      for (const comp of comps) {
        if (!comp.id) {
          throw new Error("Each component in A2UI components list must have a unique 'id'.");
        }
        map[comp.id] = comp;
      }

      if (!map['root']) {
        throw new Error("A2UI components list must contain a component with id 'root'.");
      }

      setComponentsMap(map);
    } catch (err: any) {
      setError(err.message || 'Failed to parse A2UI payload.');
    }
  }, [payload]);

  if (error) {
    if (isMessageRunning) {
      return (
        <div className="w-full my-3 p-4 rounded-xl bg-gray-100 border border-gray-200 animate-pulse flex flex-col gap-2">
          <div className="h-6 w-1/3 bg-gray-200 rounded" />
          <div className="h-20 w-full bg-gray-200/60 rounded-xl" />
        </div>
      );
    }
    return (
      <div className="my-3 p-4 border border-rose-200 bg-rose-50 rounded-xl text-xs flex flex-col gap-2">
        <div className="flex items-center gap-2 text-[#EA4335] font-semibold">
          <AlertTriangle className="h-4 w-4" />
          <span>A2UI Render Error</span>
        </div>
        <p className="text-gray-600 text-xs">{error}</p>
        <pre className="mt-1 p-2 bg-gray-100 rounded text-[10px] overflow-auto max-h-32 font-mono text-gray-800 whitespace-pre">
          {payload}
        </pre>
      </div>
    );
  }

  const renderComponent = (id: string): React.ReactNode => {
    const comp = componentsMap[id];
    if (!comp) {
      return (
        <span key={id} className="text-xs text-[#EA4335] bg-rose-50 p-1 rounded font-mono border border-rose-200">
          [Missing Component: {id}]
        </span>
      );
    }

    const {
      component,
      children,
      text,
      label,
      value,
      change,
      trend,
      ticker,
      start_year,
      end_year,
      variant,
      metric_type,
    } = comp;

    switch (component) {
      case 'Card':
        return (
          <div key={id} className="border border-gray-200 rounded-2xl p-5 shadow-xs bg-white text-gray-900 flex flex-col gap-4">
            {children?.map((childId) => renderComponent(childId))}
          </div>
        );

      case 'Column':
        return (
          <div key={id} className="flex flex-col gap-3 w-full">
            {children?.map((childId) => renderComponent(childId))}
          </div>
        );

      case 'Row':
        return (
          <div key={id} className="flex flex-row gap-3 flex-wrap w-full items-stretch">
            {children?.map((childId) => renderComponent(childId))}
          </div>
        );

      case 'Text': {
        const textClass =
          variant === 'title'
            ? 'text-base font-bold font-heading text-[#1A73E8] tracking-tight'
            : variant === 'subtitle'
            ? 'text-xs font-semibold text-gray-500 uppercase tracking-wider'
            : variant === 'caption'
            ? 'text-xs text-gray-400'
            : 'text-sm text-gray-800 leading-relaxed';
        return (
          <p key={id} className={`${textClass} whitespace-pre-wrap`}>
            {text}
          </p>
        );
      }

      case 'MetricCard': {
        let IndicatorIcon = Minus;
        let trendColor = 'text-gray-600 bg-gray-100 border-gray-200';
        if (trend === 'up') {
          IndicatorIcon = ArrowUpRight;
          trendColor = 'text-[#34A853] bg-emerald-50 border-emerald-200';
        } else if (trend === 'down') {
          IndicatorIcon = ArrowDownRight;
          trendColor = 'text-[#EA4335] bg-rose-50 border-rose-200';
        }

        return (
          <div
            key={id}
            className="flex-1 min-w-[150px] border border-gray-200 rounded-xl p-4 bg-gray-50 shadow-xs flex flex-col gap-1.5 text-sm hover:border-blue-300 transition-colors"
          >
            <span className="text-gray-500 text-xs font-semibold uppercase tracking-wider">
              {label}
            </span>
            <div className="flex items-baseline justify-between gap-2 mt-1">
              <span className="text-2xl font-bold tracking-tight text-gray-900 font-mono">{value}</span>
              {change && (
                <span className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-bold border ${trendColor}`}>
                  <IndicatorIcon className="h-3.5 w-3.5 shrink-0" />
                  <span>{change}</span>
                </span>
              )}
            </div>
          </div>
        );
      }

      case 'PeerComparisonTable':
        return (
          <div key={id} className="w-full">
            <PeerComparisonTable
              ticker={ticker}
              peerTicker={comp.peer_ticker}
              year={comp.year || start_year || end_year}
            />
          </div>
        );

      case 'FinancialTable': {
        const hasPeer = comp.peer_ticker || (typeof ticker === 'string' && ticker.includes(','));
        if (hasPeer) {
          return (
            <div key={id} className="w-full">
              <PeerComparisonTable
                ticker={ticker}
                peerTicker={comp.peer_ticker}
                year={comp.year || start_year || end_year}
              />
            </div>
          );
        }
        return (
          <div key={id} className="w-full">
            <FinancialInlineTable ticker={ticker} startYear={start_year} endYear={end_year} />
          </div>
        );
      }

      case 'MetricsChart':
        return (
          <div key={id} className="w-full">
            <FinancialMetricsChart
              ticker={ticker}
              peerTicker={comp.peer_ticker}
              startYear={start_year}
              endYear={end_year}
              metricType={metric_type || 'all'}
            />
          </div>
        );

      default:
        return (
          <div key={id} className="text-xs text-[#EA4335] p-2 bg-rose-50 border border-rose-200 rounded font-mono">
            [Unsupported A2UI Component: {component}]
          </div>
        );
    }
  };

  if (!componentsMap['root']) {
    return null;
  }

  return <div className="w-full my-4 flex flex-col gap-4">{renderComponent('root')}</div>;
};

export const A2UISurface: React.FC<A2UISurfaceProps> = (props) => (
  <A2UIErrorBoundary>
    <A2UISurfaceContent {...props} />
  </A2UIErrorBoundary>
);
