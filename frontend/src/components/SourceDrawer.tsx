import React, { useState, useEffect, useRef } from 'react';
import { Database, FileText, ExternalLink, BookmarkCheck, CheckCircle2, ChevronDown, ChevronUp, PanelRightClose, Target } from 'lucide-react';
import { marked } from 'marked';
import { AnalysisResponse, ActiveSourceQuery } from '../types';

interface SourceDrawerProps {
  lastResponse: AnalysisResponse | null;
  activeSourceQuery?: ActiveSourceQuery | null;
  onToggleCollapse?: () => void;
}

marked.use({
  gfm: true,
  breaks: true,
});

function normalizeMarkdownTables(text: string): string {
  if (!text) return '';

  // 1. Universal SEC Metadata & Page Banner Stripper (ZERO hardcoded company names)
  // Strips both "| <COMPANY> | <FORM> | <PAGE/SECTION>" AND "<COMPANY> | <FORM> | <PAGE/SECTION>"
  let preprocessed = text
    .replace(/^(?:\||\s*)[^|\n]+\s*\|\s*(?:\d{4}\s*)?Form\s*10-[KQAB][^\n]*\n?/gim, '')
    .replace(/(?:\||\s*)[^|\n]+\s*\|\s*(?:\d{4}\s*)?Form\s*10-[KQAB][^\n]*\n?/gim, '');

  // 2. Separate narrative text & <mark> tags that run onto the end of a table line
  preprocessed = preprocessed.replace(
    /(\|\s*(?:\$?\d[\d,.]*%?|\([^)]+\))\s*\|?<\/mark>|\|\s*(?:\$?\d[\d,.]*%?|\([^)]+\))\s*\|)\s*(\|?\s*<mark[^>]*>[A-Z][a-z]{2,}|\|?\s*[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})/g,
    '$1\n\n$2'
  );

  const rawLines = preprocessed.split('\n');
  const sanitizedLines: string[] = [];

  for (let i = 0; i < rawLines.length; i++) {
    let line = rawLines[i].trim();
    if (!line) continue;

    // Check for orphan label lines like "| Services" followed by "| - | 96,169 | ..."
    if (/^\|\s*[A-Za-z0-9\s,&\-\/]+\s*$/.test(line) && i + 1 < rawLines.length) {
      const nextLine = rawLines[i + 1].trim();
      if (nextLine.startsWith('| - |') || nextLine.startsWith('| |')) {
        const label = line.replace(/\|/g, '').trim();
        rawLines[i + 1] = '| ' + label + ' ' + nextLine.substring(nextLine.indexOf('|', 2));
        continue;
      }
    }

    sanitizedLines.push(line);
  }

  const blocks: Array<{ type: 'text' | 'table'; lines: string[] }> = [];
  let currentBlock: { type: 'text' | 'table'; lines: string[] } | null = null;

  for (let i = 0; i < sanitizedLines.length; i++) {
    let line = sanitizedLines[i].trim();
    if (!line) {
      if (currentBlock) {
        blocks.push(currentBlock);
        currentBlock = null;
      }
      continue;
    }

    if (/^\|[\s|]*$/.test(line)) {
      continue;
    }

    // A line is a table line IF it contains pipe delimiters and table metrics (NOT long narrative text > 90 chars without pipes)
    const pipeCount = (line.match(/\|/g) || []).length;
    const isLongNarrative = line.replace(/<mark[^>]*>|<\/mark>/g, '').length > 90 && pipeCount <= 1;
    const isTableLine =
      !isLongNarrative &&
      (pipeCount >= 2 ||
        (pipeCount >= 1 && (line.includes('$') || line.includes('%') || line.includes('---'))));

    if (!isTableLine && line.startsWith('|')) {
      line = line.replace(/^\|\s*/, '');
    }

    if (isTableLine) {
      if (!currentBlock || currentBlock.type !== 'table') {
        if (currentBlock) blocks.push(currentBlock);
        currentBlock = { type: 'table', lines: [] };
      }
      currentBlock.lines.push(line);
    } else {
      if (!currentBlock || currentBlock.type !== 'text') {
        if (currentBlock) blocks.push(currentBlock);
        currentBlock = { type: 'text', lines: [] };
      }
      currentBlock.lines.push(line);
    }
  }

  if (currentBlock) {
    blocks.push(currentBlock);
  }

  const outputBlocks: string[] = [];

  for (const block of blocks) {
    if (block.type === 'text') {
      outputBlocks.push(block.lines.join('\n'));
      continue;
    }

    const rawTableLines = block.lines;
    const parsedRows: Array<{ citeId: string; cells: string[] }> = [];
    let maxCols = 0;

    for (let r = 0; r < rawTableLines.length; r++) {
      let rowStr = rawTableLines[r];

      let citeId = '';
      const citeMatch = rowStr.match(/id=["']?(c\d+)["']?/i) || rowStr.match(/data-cite-id=["']?(c\d+)["']?/i);
      if (citeMatch) citeId = citeMatch[1].toLowerCase();

      if (rowStr.startsWith('<mark') && rowStr.endsWith('</mark>')) {
        const markOpenEnd = rowStr.indexOf('>');
        rowStr = rowStr.substring(markOpenEnd + 1, rowStr.length - 7).trim();
      }

      if (!rowStr.startsWith('|')) rowStr = '| ' + rowStr;
      if (!rowStr.endsWith('|')) rowStr = rowStr + ' |';

      if (/^\|\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|$/.test(rowStr)) {
        continue;
      }

      const rawCells = rowStr.split('|').slice(1, -1);
      const cleanedCells = rawCells.map((c) => c.trim());

      if (cleanedCells.length > maxCols) {
        maxCols = cleanedCells.length;
      }

      parsedRows.push({ citeId, cells: cleanedCells });
    }

    if (maxCols === 0 || parsedRows.length === 0) {
      outputBlocks.push(block.lines.join('\n'));
      continue;
    }

    const headerRow = parsedRows[0];
    const dataRows = parsedRows.slice(1);
    const firstHeaderCell = headerRow.cells[0] ? headerRow.cells[0].trim() : '';

    const firstHeaderIsYearOrMetric = /^(?:20\d\d|change|\$|%)/i.test(firstHeaderCell);
    const dataRowsStartWithText = dataRows.some((r) => r.cells[0] && !/^(?:\$|%|\d+(?:\.\d+)?$)/.test(r.cells[0].trim()));

    if (firstHeaderIsYearOrMetric && dataRowsStartWithText) {
      headerRow.cells.unshift('Category');
      if (headerRow.cells.length > maxCols) {
        maxCols = headerRow.cells.length;
      }
    }

    const normalizedTableLines: string[] = [];

    const headerCells = [...headerRow.cells];
    while (headerCells.length < maxCols) {
      headerCells.push('');
    }
    normalizedTableLines.push('| ' + headerCells.map((c) => c || ' ').join(' | ') + ' |');

    normalizedTableLines.push('| ' + Array(maxCols).fill('---').join(' | ') + ' |');

    for (let d = 1; d < parsedRows.length; d++) {
      const rowObj = parsedRows[d];
      const cells = [...rowObj.cells];
      while (cells.length < maxCols) {
        cells.push('');
      }

      const formattedCells = cells.map((cellStr) => {
        if (!cellStr) return '';

        if (rowObj.citeId && !cellStr.includes('<mark')) {
          return `<mark id="${rowObj.citeId}" data-cite-id="${rowObj.citeId}">${cellStr}</mark>`;
        }
        return cellStr;
      });

      normalizedTableLines.push('| ' + formattedCells.map((c) => c || ' ').join(' | ') + ' |');
    }

    outputBlocks.push(normalizedTableLines.join('\n'));
  }

  return outputBlocks.join('\n\n');
}

function formatSECParagraphsAndHeadings(text: string): string {
  if (!text) return '';

  let cleaned = text;

  // 1. Universal Deduplication of Repeated Line-Start Words/Phrases (ZERO hardcoded words)
  // Replaces "Title Title sentence..." with "*Title*\n\nTitle sentence..."
  cleaned = cleaned.replace(
    /(?:^|\n)\s*(<mark[^>]*>)?\s*\b([A-Z][a-zA-Z0-9&, -]{1,40})\s+\2\b/gm,
    (_match, openMark, category) => {
      const markStr = openMark || '';
      return `\n\n*${category}*\n\n${markStr}${category}`;
    }
  );

  // 2. Universal Standalone Line Heading Formatting (ZERO hardcoded words)
  // Short standalone lines (< 65 chars, no ending punctuation like .!? or :, no table pipes) become italicized section headings
  const lines = cleaned.split('\n');
  const processedLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : '';

    const isHeadingLabel =
      line.length > 1 &&
      line.length <= 65 &&
      !/[.!?:]$/.test(line) &&
      !line.includes('|') &&
      !line.includes('<mark') &&
      !line.startsWith('*') &&
      !line.startsWith('#') &&
      !/^\d+$/.test(line) &&
      nextLine.length > 0;

    if (isHeadingLabel) {
      processedLines.push(`*${line}*`);
      processedLines.push(''); // blank line after heading
    } else {
      processedLines.push(lines[i]);
    }
  }

  cleaned = processedLines.join('\n');

  // 3. Ensure double line breaks between consecutive paragraphs or <mark> tags
  cleaned = cleaned.replace(/<\/mark>\s*<mark/g, '</mark>\n\n<mark');

  return cleaned;
}

function renderHighlightedMarkdown(text: string): { __html: string } {
  if (!text) return { __html: '' };

  try {
    // 1. Normalize and fix broken Markdown table pipe structures
    const normalized = normalizeMarkdownTables(text);

    // 2. Format SEC paragraph line breaks and subsection headings
    const formatted = formatSECParagraphsAndHeadings(normalized);

    // 3. Parse Markdown into HTML structure (including <table>, <thead>, <tbody>, <th>, <td>)
    const rawHtml = marked.parse(formatted) as string;

    // 4. Ensure <mark> tags inside rendered HTML preserve id and data-cite-id attributes cleanly
    const processedHtml = rawHtml.replace(
      /<mark(?:\s+id=["']?(c\d+)["']?)?(?:\s+data-cite-id=["']?(c\d+)["']?)?\s*>(.*?)<\/mark>/gs,
      (_match, id1, id2, content) => {
        const citeId = (id1 || id2 || '').toLowerCase();
        if (citeId) {
          return `<mark id="${citeId}" data-cite-id="${citeId}" class="bg-amber-100 text-amber-900 px-1.5 py-0.5 rounded border border-amber-300 font-semibold inline-block my-0.5 transition-all duration-300">${content}</mark>`;
        }
        return `<mark class="bg-amber-100 text-amber-900 px-1.5 py-0.5 rounded border border-amber-300 font-semibold inline-block my-0.5 transition-all duration-300">${content}</mark>`;
      }
    );

    return { __html: processedHtml };
  } catch {
    return { __html: text };
  }
}

function computeMarkScore(markText: string, rawQuery: string): number {

  if (!markText || !rawQuery) return 0;

  const mLower = markText.toLowerCase().trim();
  const qLower = rawQuery.toLowerCase().trim();

  // 1. Direct inclusion check
  if (qLower.includes(mLower) || mLower.includes(qLower)) {
    return 100;
  }

  const stopWords = new Set([
    'the', 'and', 'for', 'that', 'this', 'with', 'from', 'were', 'was', 'have',
    'has', 'had', 'been', 'than', 'more', 'less', 'over', 'into', 'also', 'source',
    'item', 'mda', 'md&a', 'filing', '10-k', '10k', 'form', 'page', 'part'
  ]);

  const extractTokens = (text: string) =>
    text
      .replace(/[^\w\s%]/g, ' ')
      .split(/\s+/)
      .map((t) => t.toLowerCase().trim())
      .filter((t) => t.length >= 2 && !stopWords.has(t));

  const markTokens = extractTokens(mLower);
  const queryTokens = extractTokens(qLower);

  if (markTokens.length === 0 || queryTokens.length === 0) return 0;

  const queryTokenSet = new Set(queryTokens);
  let score = 0;

  for (const token of markTokens) {
    if (queryTokenSet.has(token)) {
      if (
        /\d+/.test(token) ||
        /%/.test(token) ||
        ['services', 'iphone', 'mac', 'ipad', 'wearables', 'revenue', 'sales', 'operating', 'income', 'net', 'decreased', 'increased', 'growth'].includes(token)
      ) {
        score += 5;
      } else {
        score += 2;
      }
    }
  }

  return score;
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
    const rawQuery = activeSourceQuery?.query;
    if (!rawQuery || consolidatedChunks.length === 0) return;

    const queryLower = rawQuery.toLowerCase().trim();
    const queryParts = rawQuery.split('|||').map((p) => p.toLowerCase().trim());

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

      const targetIdx = matchIdx;
      const scrollAndPulseMark = () => {
        const el = cardRefs.current[targetIdx];
        if (!el) return;

        // 1. Scroll container to source card
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // 2. Locate target <mark> element by explicit citeId if present, or fallback to computeMarkScore
        const markEls = el.querySelectorAll('mark');
        if (markEls && markEls.length > 0) {
          let bestMark: HTMLElement | null = null;

          const targetCiteId = activeSourceQuery?.citeId;
          if (targetCiteId) {
            const directMatch =
              el.querySelector(`[data-cite-id="${targetCiteId}"]`) ||
              el.querySelector(`#${targetCiteId}`);
            if (directMatch) {
              bestMark = directMatch as HTMLElement;
            }
          }

          if (!bestMark) {
            let highestScore = -1;
            markEls.forEach((markNode) => {
              const mText = markNode.textContent || '';
              const score = computeMarkScore(mText, rawQuery);
              if (score > highestScore) {
                highestScore = score;
                bestMark = markNode as HTMLElement;
              }
            });
          }

          if (!bestMark) {
            bestMark = markEls[0] as HTMLElement;
          }

          bestMark.scrollIntoView({ behavior: 'smooth', block: 'center' });

          markEls.forEach((m) => m.classList.remove('citation-mark-pulse'));
          // Force DOM reflow to restart CSS keyframe animation on consecutive clicks
          void bestMark.offsetWidth;
          bestMark.classList.add('citation-mark-pulse');
        }
      };

      requestAnimationFrame(scrollAndPulseMark);
      const timerId = setTimeout(scrollAndPulseMark, 120);

      const clearTimer = setTimeout(() => {
        setHighlightedIdx(null);
      }, 5000);

      return () => {
        clearTimeout(timerId);
        clearTimeout(clearTimer);
      };
    }
  }, [activeSourceQuery?.timestamp, activeSourceQuery, consolidatedChunks]);

  const toggleExpand = (idx: number) => {
    setExpandedChunks((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const renderHighlightedText = (text: string, isHighlighted: boolean) => {
    if (!text) return null;

    // Safely parse LLM-annotated <mark ...>...</mark> sentence blocks preserving id and data-cite-id
    const parts = text.split(/(<mark[^>]*>.*?<\/mark>)/gs);

    return (
      <span>
        {parts.map((part, i) => {
          if (part.startsWith('<mark') && part.endsWith('</mark>')) {
            const openTagEnd = part.indexOf('>');
            const openTag = part.substring(0, openTagEnd + 1);
            const innerText = part.substring(openTagEnd + 1, part.length - 7);

            const idMatch = openTag.match(/id=["']?(c\d+)["']?/i) || openTag.match(/data-cite-id=["']?(c\d+)["']?/i);
            const citeId = idMatch ? idMatch[1].toLowerCase() : '';

            return (
              <mark
                key={i}
                id={citeId || undefined}
                data-cite-id={citeId || undefined}
                className="bg-amber-100 text-amber-900 px-1.5 py-0.5 rounded border border-amber-300 font-semibold inline-block my-0.5 transition-all duration-300"
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

  const handleDrawerMarkClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement;
    const markNode = target.closest('[data-cite-id]') || target.closest('mark');
    if (!markNode) return;

    const rawCiteId = markNode.getAttribute('data-cite-id') || markNode.getAttribute('id');
    if (!rawCiteId) return;

    const citeId = rawCiteId.toLowerCase().trim();
    if (!citeId) return;

    const matchingBadges = Array.from(
      document.querySelectorAll<HTMLButtonElement>(`button[data-cite-id="${citeId}"]`)
    );

    if (matchingBadges.length === 0) return;

    matchingBadges.forEach((badge) => {
      badge.scrollIntoView({ behavior: 'smooth', block: 'center' });
      badge.classList.remove('citation-flash-pulse');
      void badge.offsetWidth;
      badge.classList.add('citation-flash-pulse');

      setTimeout(() => {
        badge.classList.remove('citation-flash-pulse');
      }, 1800);
    });
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

      <div className="flex-1 overflow-y-auto p-4 space-y-3" onClick={handleDrawerMarkClick}>
        {consolidatedChunks.length > 0 ? (
          consolidatedChunks.map((chunk, idx) => {
            const isExpanded = !!expandedChunks[idx];
            const isHighlighted = highlightedIdx === idx;
            const textToDisplay = isExpanded ? chunk.content : (chunk.highlight_excerpt || chunk.content);
            const isBQ = chunk.source_type === 'bigquery' || (chunk.gcs_uri && chunk.gcs_uri.startsWith('bq://'));

            return (
              <div
                key={idx}
                ref={(el) => (cardRefs.current[idx] = el)}
                className={`p-3.5 rounded-xl transition-all duration-300 ${
                  isHighlighted
                    ? 'source-card-highlight'
                    : isBQ
                    ? 'bg-white border border-cyan-300 shadow-sm'
                    : idx === 0
                    ? 'bg-white border border-blue-300 shadow-sm'
                    : 'bg-white border border-gray-200 shadow-xs hover:border-blue-200'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-xs text-gray-900 flex items-center gap-1.5">
                    {isBQ ? (
                      <Database className="w-3.5 h-3.5 text-cyan-600" />
                    ) : (
                      <FileText className="w-3.5 h-3.5 text-[#1A73E8]" />
                    )}
                    {chunk.company_name} FY{chunk.fiscal_year} {isBQ ? 'Audited Metrics' : '10-K'}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {isHighlighted && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#1A73E8] text-white shadow-xs flex items-center gap-1 animate-pulse">
                        <Target className="w-2.5 h-2.5 text-white" /> Target
                      </span>
                    )}
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                      <CheckCircle2 className="w-2.5 h-2.5 text-[#34A853]" /> Cited
                    </span>
                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${isBQ ? 'bg-cyan-50 text-cyan-800 border border-cyan-200' : 'bg-purple-50 text-purple-700 border border-purple-200'}`}>
                      {chunk.section}
                    </span>
                  </div>
                </div>

                <div className="text-xs text-gray-800 leading-relaxed bg-gray-50 p-3 rounded-lg border border-gray-200 mb-2">
                  <div className="text-[10px] font-semibold text-amber-800 uppercase tracking-wider mb-1 flex items-center justify-between">
                    <span>{isBQ ? 'GCP BigQuery Metric Data Table' : (isExpanded ? 'Full Document Context' : 'Relevant Grounded Excerpt')}</span>
                    {!isBQ && (
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
                    )}
                  </div>
                  <div className="markdown-drawer-content max-w-none text-xs text-gray-800 leading-relaxed overflow-x-auto">
                    <div dangerouslySetInnerHTML={renderHighlightedMarkdown(textToDisplay)} />
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
          <div className="p-4 rounded-xl bg-white border border-gray-200 shadow-xs space-y-2 text-center py-8">
            <BookmarkCheck className="w-6 h-6 text-gray-400 mx-auto mb-1" />
            <h3 className="font-semibold text-xs text-gray-800">No Grounded Context Available</h3>
            <p className="text-xs text-gray-500 leading-relaxed max-w-xs mx-auto">
              Execute a financial inquiry or click an inline citation badge to view grounded SEC filings or BigQuery metrics.
            </p>
          </div>
        )}
      </div>
    </aside>
  );
};

