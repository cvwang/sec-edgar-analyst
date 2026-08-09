import React, { useState, useEffect, useRef } from 'react';
import { Database, FileText, ExternalLink, BookmarkCheck, CheckCircle2, ChevronDown, ChevronUp, PanelRightClose } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface SourceDrawerProps {
  lastResponse: AnalysisResponse | null;
  activeSourceQuery?: string | null;
  onToggleCollapse?: () => void;
}

export const SourceDrawer: React.FC<SourceDrawerProps> = ({ lastResponse, activeSourceQuery, onToggleCollapse }) => {
  const [expandedChunks, setExpandedChunks] = useState<Record<number, boolean>>({});
  const [highlightedIdx, setHighlightedIdx] = useState<number | null>(null);
  const cardRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const citations = lastResponse?.citations || [];
  const textChunks = lastResponse?.hybrid_search_result?.text_chunks || [];
  const derivedTicker = lastResponse?.ticker || (lastResponse?.tickers && lastResponse.tickers.length > 0 ? lastResponse.tickers[0] : 'SEC');

  // Group and merge chunks from the same document section into a single unified context block per source file
  const consolidatedChunks = React.useMemo(() => {
    if (!textChunks || textChunks.length === 0) return [];

    const map = new Map<string, typeof textChunks[0]>();
    for (const chunk of textChunks) {
      const key = chunk.gcs_uri || `${chunk.company_name}_${chunk.fiscal_year}_${chunk.section}`;
      if (map.has(key)) {
        const existing = { ...map.get(key)! };
        if (chunk.content && !existing.content.includes(chunk.content)) {
          existing.content = `${existing.content}\n\n${chunk.content}`;
        }
        if (
          chunk.highlight_excerpt &&
          existing.highlight_excerpt &&
          !existing.highlight_excerpt.includes(chunk.highlight_excerpt)
        ) {
          existing.highlight_excerpt = `${existing.highlight_excerpt}\n\n${chunk.highlight_excerpt}`;
        }
        map.set(key, existing);
      } else {
        map.set(key, { ...chunk });
      }
    }
    return Array.from(map.values());
  }, [textChunks]);

  // Auto-scroll and highlight when a source citation badge is clicked in chat stream
  useEffect(() => {
    if (!activeSourceQuery || consolidatedChunks.length === 0) return;

    const queryLower = activeSourceQuery.toLowerCase().trim();
    const queryParts = activeSourceQuery.split('|||').map((p) => p.toLowerCase().trim());

    // 1. Stage 1: Match by GCS URI or exact filename
    let matchIdx = consolidatedChunks.findIndex((chunk) => {
      const gcs = (chunk.gcs_uri || '').toLowerCase();
      const filename = gcs.split('/').pop() || '';
      return queryParts.some((p) => p && (gcs.includes(p) || (filename && p.includes(filename))));
    });

    // 2. Stage 2: Match by Ticker + Fiscal Year + SEC Section
    if (matchIdx === -1) {
      matchIdx = consolidatedChunks.findIndex((chunk) => {
        const comp = (chunk.company_name || chunk.ticker || '').toLowerCase();
        const yr = String(chunk.fiscal_year || '');
        const sec = (chunk.section || '').toLowerCase();

        const matchesComp = comp && queryParts.some((p) => p && comp.includes(p.replace(/\s+corp$/i, '')));
        const matchesYr = yr && queryParts.some((p) => p && p.includes(yr));

        if (matchesComp && matchesYr) {
          const isRiskInQuery = queryParts.some((p) => p.includes('risk') || p.includes('1a'));
          const isMdaInQuery = queryParts.some((p) => p.includes('md&a') || p.includes('mda') || p.includes('7'));
          const isRiskInSec = sec.includes('risk') || sec.includes('1a');
          const isMdaInSec = sec.includes('md&a') || sec.includes('7');

          if ((isRiskInQuery && isRiskInSec) || (isMdaInQuery && isMdaInSec)) return true;
          if (!isRiskInQuery && !isMdaInQuery) return true;
        }
        return false;
      });
    }

    // 3. Stage 3: Direct metadata match (citation or company/year)
    if (matchIdx === -1) {
      matchIdx = consolidatedChunks.findIndex((chunk) => {
        if (chunk.citation && queryLower.includes(chunk.citation.toLowerCase())) return true;
        if (
          chunk.company_name &&
          queryLower.includes(chunk.company_name.toLowerCase()) &&
          chunk.fiscal_year &&
          queryLower.includes(String(chunk.fiscal_year))
        )
          return true;
        return false;
      });
    }

    // 4. Stage 4: Direct text content inclusion match
    if (matchIdx === -1) {
      matchIdx = consolidatedChunks.findIndex(
        (chunk) =>
          chunk.content &&
          (chunk.content.toLowerCase().includes(queryLower) || queryLower.includes(chunk.content.toLowerCase()))
      );
    }

    // 5. Stage 5: Fallback company name match
    if (matchIdx === -1) {
      matchIdx = consolidatedChunks.findIndex(
        (chunk) => chunk.company_name && queryLower.includes(chunk.company_name.toLowerCase())
      );
    }

    if (matchIdx !== -1) {
      setExpandedChunks((prev) => ({ ...prev, [matchIdx]: true }));
      setHighlightedIdx(matchIdx);

      const el = cardRefs.current[matchIdx];
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Scroll inside card container to the highlighted <mark> element if rendered
        setTimeout(() => {
          const markEl = el.querySelector('mark');
          if (markEl) {
            markEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }
        }, 150);
      }

      const timer = setTimeout(() => {
        setHighlightedIdx(null);
      }, 3500);
      return () => clearTimeout(timer);
    }
  }, [activeSourceQuery, consolidatedChunks]);

  const toggleExpand = (idx: number) => {
    setExpandedChunks((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const renderHighlightedText = (text: string) => {
    if (!text) return null;

    // Safely parse LLM-annotated <mark>...</mark> sentence blocks
    const parts = text.split(/(<mark>.*?<\/mark>)/gs);

    return (
      <span>
        {parts.map((part, i) => {
          if (part.startsWith('<mark>') && part.endsWith('</mark>')) {
            const innerText = part.substring(6, part.length - 7);
            return (
              <mark
                key={i}
                className="bg-amber-100 text-amber-900 px-1 py-0.5 rounded border border-amber-300 font-semibold inline-block my-0.5"
              >
                {innerText}
              </mark>
            );
          }
          return part;
        })}
      </span>
    );
  };

  return (
    <aside className="w-full h-full bg-white border-l border-gray-200 flex flex-col shrink-0 overflow-hidden shadow-xs">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-[#1A73E8]" />
          <h2 className="font-heading font-semibold text-sm text-gray-800">Grounded Context Drawer</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-[#1A73E8] border border-blue-200">
            {consolidatedChunks.length} {consolidatedChunks.length === 1 ? 'Source Cited' : 'Sources Cited'}
          </span>
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              title="Collapse Grounded Context Drawer"
              className="p-1.5 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer flex items-center justify-center"
            >
              <PanelRightClose className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {consolidatedChunks.length > 0 ? (
          consolidatedChunks.map((chunk, idx) => {
            const isExpanded = !!expandedChunks[idx];
            const isHighlighted = highlightedIdx === idx;
            const textToDisplay = isExpanded ? chunk.content : (chunk.highlight_excerpt || chunk.content);

            return (
              <div
                key={idx}
                ref={(el) => (cardRefs.current[idx] = el)}
                className={`p-3.5 rounded-xl transition-all duration-300 ${
                  isHighlighted
                    ? 'source-card-highlight'
                    : idx === 0
                    ? 'bg-white border border-blue-300 shadow-sm'
                    : 'bg-white border border-gray-200 shadow-xs hover:border-blue-200'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-xs text-gray-900 flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-[#1A73E8]" />
                    {chunk.company_name} FY{chunk.fiscal_year} 10-K
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                      <CheckCircle2 className="w-2.5 h-2.5 text-[#34A853]" /> Cited
                    </span>
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
                      {chunk.section}
                    </span>
                  </div>
                </div>

                <div className="text-xs text-gray-800 leading-relaxed bg-gray-50 p-3 rounded-lg border border-gray-200 mb-2">
                  <div className="text-[10px] font-semibold text-amber-800 uppercase tracking-wider mb-1 flex items-center justify-between">
                    <span>{isExpanded ? 'Full Document Context' : 'Relevant Grounded Excerpt'}</span>
                    <button
                      onClick={() => toggleExpand(idx)}
                      className="text-[#1A73E8] hover:text-[#1557B0] flex items-center gap-0.5 text-[10px] normal-case cursor-pointer"
                    >
                      {isExpanded ? (
                        <>Show Excerpt <ChevronUp className="w-3 h-3" /></>
                      ) : (
                        <>Show Full Text <ChevronDown className="w-3 h-3" /></>
                      )}
                    </button>
                  </div>
                  <div className="italic whitespace-pre-line leading-relaxed text-gray-700">
                    "{renderHighlightedText(textToDisplay)}"
                  </div>
                </div>

                <div className="text-[10px] font-mono text-gray-500 flex items-center justify-between">
                  <span className="truncate pr-2">Citation: {chunk.citation}</span>
                  <ExternalLink className="w-3 h-3 text-gray-400 shrink-0" />
                </div>
              </div>
            );
          })
        ) : (
          <div className="p-4 rounded-xl bg-white border border-gray-200 shadow-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-xs text-gray-900 flex items-center gap-1.5">
                <BookmarkCheck className="w-3.5 h-3.5 text-[#1A73E8]" />
                {derivedTicker} Grounded Context
              </span>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
                Item 7 - MD&A
              </span>
            </div>
            <p className="text-xs text-gray-700 leading-relaxed italic bg-gray-50 p-2.5 rounded-lg border border-gray-200">
              "Official SEC EDGAR Filing Grounded Context: Audited financial disclosures and period metrics."
            </p>
            <div className="text-[10px] font-mono text-gray-500">
              Citation: {derivedTicker} 10-K Filing Grounded Context
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
