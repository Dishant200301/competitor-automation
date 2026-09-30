import { useState } from 'react';
import { ResearchSummary } from '../types/research';
import { getPdfDownloadUrl, generateGoogleDoc } from '../services/api';

interface Props {
  summary: ResearchSummary;
  onReset: () => void;
}

export const ResearchComplete: React.FC<Props> = ({ summary, onReset }) => {
  const [docLoading, setDocLoading] = useState(false);
  const [gdocUrl, setGdocUrl] = useState<string | null>(summary.run.google_doc_url || null);
  const [gdocError, setGdocError] = useState<string | null>(null);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const handleOpenGoogleDoc = async () => {
    if (gdocUrl) {
      window.open(gdocUrl, '_blank');
      return;
    }

    setDocLoading(true);
    setGdocError(null);
    try {
      const res = await generateGoogleDoc(summary.run.id);
      setGdocUrl(res.url);
      window.open(res.url, '_blank');
    } catch (err: any) {
      setGdocError(err.message || 'Google Docs credentials not configured in backend.');
    } finally {
      setDocLoading(false);
    }
  };

  const pdfUrl = getPdfDownloadUrl(summary.run.id);

  return (
    <div className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 sm:p-8 shadow-sm space-y-6">
      {/* Target Overview */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-zinc-200 dark:border-zinc-800 gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-block px-2.5 py-0.5 text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400 rounded-full">
              Intelligence Verified
            </span>
            <span className="text-xs text-zinc-400 font-mono">
              {summary.run.source_type.toUpperCase()}
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            {summary.company?.company_name || summary.run.source_input}
          </h2>
          <p className="text-xs text-zinc-500 mt-1">
            {summary.pages_count} pages crawled • {summary.competitors.length} Google-verified competitors • {summary.keywords_count} high-ranking keywords
          </p>
          {summary.company?.description && (
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-2 max-w-2xl">
              {summary.company.description}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-100 shadow-sm transition-all"
          >
            Download PDF Report
          </a>

          <button
            type="button"
            onClick={handleOpenGoogleDoc}
            disabled={docLoading}
            className="px-4 py-2 text-xs font-semibold rounded-lg border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-200 transition-all cursor-pointer disabled:opacity-50"
          >
            {docLoading ? 'Generating Doc...' : 'Open Google Doc'}
          </button>

          <button
            type="button"
            onClick={onReset}
            className="px-3 py-2 text-xs font-medium text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200 cursor-pointer"
          >
            New Research
          </button>
        </div>
      </div>

      {gdocError && (
        <div className="p-3 text-xs rounded-lg bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-300">
          {gdocError}
        </div>
      )}

      {/* Top Google Competitors with A-to-Z Deep Details */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider">
            Google Top Competitors (Ranked & Deeply Crawled)
          </h3>
          <span className="text-[11px] text-zinc-400">
            Click any card to view A-to-Z breakdown
          </span>
        </div>

        <div className="space-y-3">
          {summary.competitors.map((comp, idx) => {
            const isExpanded = expandedIndex === idx;
            return (
              <div
                key={idx}
                className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-950/40 p-4 transition-all hover:border-zinc-300 dark:hover:border-zinc-700"
              >
                {/* Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950/70 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900">
                      Google #{comp.google_rank || idx + 1}
                    </span>
                    <a
                      href={comp.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-bold text-sm text-zinc-900 dark:text-zinc-100 hover:underline"
                    >
                      {comp.competitor_name}
                    </a>
                    <span className="text-[10px] text-zinc-400 font-mono">
                      ({comp.domain})
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 font-semibold">
                      {comp.competitor_type}
                    </span>
                    <button
                      type="button"
                      onClick={() => setExpandedIndex(isExpanded ? null : idx)}
                      className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline cursor-pointer ml-2"
                    >
                      {isExpanded ? 'Hide A-to-Z Info ▲' : 'View A-to-Z Info ▼'}
                    </button>
                  </div>
                </div>

                {/* Primary Overview / Reason */}
                <p className="text-xs text-zinc-600 dark:text-zinc-300 mt-2">
                  {comp.description || comp.reason}
                </p>

                {/* Pricing & Key Tags Preview */}
                <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
                  {comp.pricing_model && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-900 font-medium text-[11px]">
                      💰 Pricing: {comp.pricing_model}
                    </span>
                  )}

                  {comp.products && comp.products.length > 0 && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-[11px]">
                      🏷️ {comp.products[0]}
                    </span>
                  )}
                </div>

                {/* Expanded A-to-Z Clean Details */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-800 space-y-3 text-xs">
                    {/* Products / Offerings */}
                    {comp.products && comp.products.length > 0 && (
                      <div>
                        <span className="font-semibold text-zinc-800 dark:text-zinc-200 block mb-1">
                          Discovered Products & Offerings:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {comp.products.map((p, pIdx) => (
                            <span
                              key={pIdx}
                              className="px-2 py-0.5 rounded bg-zinc-200/70 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-[11px]"
                            >
                              • {p}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Key Capabilities / Features */}
                    {comp.key_features && comp.key_features.length > 0 && (
                      <div>
                        <span className="font-semibold text-zinc-800 dark:text-zinc-200 block mb-1">
                          Key Capabilities:
                        </span>
                        <ul className="list-disc list-inside text-zinc-600 dark:text-zinc-400 space-y-0.5 text-[11px]">
                          {comp.key_features.map((feat, fIdx) => (
                            <li key={fIdx}>{feat}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Competitive Overlap */}
                    {comp.competitive_overlap && (
                      <div className="p-2.5 rounded bg-blue-50/60 dark:bg-blue-950/30 border border-blue-100 dark:border-blue-900/60">
                        <span className="font-semibold text-blue-900 dark:text-blue-300 block mb-0.5">
                          Competitive Overlap Analysis:
                        </span>
                        <p className="text-zinc-600 dark:text-zinc-400 text-[11px]">
                          {comp.competitive_overlap}
                        </p>
                      </div>
                    )}

                    {/* Sources */}
                    {comp.evidence_urls && comp.evidence_urls.length > 0 && (
                      <div className="text-[11px] text-zinc-400">
                        <span className="font-medium text-zinc-500">Verified Web Sources: </span>
                        {comp.evidence_urls.slice(0, 2).map((eu, euIdx) => (
                          <a
                            key={euIdx}
                            href={eu}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 dark:text-blue-400 hover:underline mr-2"
                          >
                            [{euIdx + 1}] {eu}
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
