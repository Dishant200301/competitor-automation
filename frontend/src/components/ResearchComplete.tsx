import React from 'react';
import { ResearchSummary } from '../types/research';
import { getPdfDownloadUrl, getDocxReportUrl } from '../services/api';

interface Props {
  summary: ResearchSummary;
  onReset: () => void;
}

export const ResearchComplete: React.FC<Props> = ({ summary, onReset }) => {
  const pdfUrl = getPdfDownloadUrl(summary.run.id);
  const docxUrl = getDocxReportUrl(summary.run.id);

  return (
    <div className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 sm:p-8 shadow-sm space-y-6">
      {/* Target Overview */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-zinc-200 dark:border-zinc-800 gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-block px-2.5 py-0.5 text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400 rounded-full">
              Research complete
            </span>
            <span className="text-xs text-zinc-400 font-mono">
              {summary.run.source_type.toUpperCase()}
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            {summary.company?.company_name || summary.run.source_input}
          </h2>
          <div className="flex flex-wrap items-center gap-3 mt-1">
            {summary.company?.website && (
              <a
                href={summary.company.website}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1 font-mono font-medium"
              >
                🌐 {summary.company.website} ↗
              </a>
            )}
            <span className="text-xs text-zinc-500">
              {summary.pages_count} pages crawled • {summary.competitors.length} verified competitors • {summary.keywords_count} search hypotheses
            </span>
          </div>

          {summary.company?.description && (
            <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-2 max-w-2xl">
              {summary.company.description}
            </p>
          )}

          {/* Official Social Media Channels Directly from Website */}
          {summary.social_profiles && summary.social_profiles.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 mt-3 pt-2.5 border-t border-zinc-100 dark:border-zinc-800">
              <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
                Official Socials:
              </span>
              {summary.social_profiles.map((sp, spIdx) => (
                <a
                  key={spIdx}
                  href={sp.profile_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-blue-50 dark:hover:bg-blue-950 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                >
                  <span>{sp.platform}</span>
                  {sp.username && <span className="text-[10px] text-zinc-400 font-mono">@{sp.username}</span>}
                  <span className="text-[10px]">↗</span>
                </a>
              ))}
            </div>
          )}
        </div>

        {/* Exactly Two Action Buttons: Docs (.docx) and PDF */}
        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3">
          {/* Docs (.docx) Button */}
          <a
            href={docxUrl}
            target="_blank"
            rel="noopener noreferrer"
            download
            className="px-4 py-2.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition-all inline-flex items-center gap-2 cursor-pointer"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
            </svg>
            <span>Docs</span>
            <span className="text-[10px] opacity-80">↗</span>
          </a>

          {/* PDF Button */}
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2.5 text-xs font-semibold rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 shadow-sm transition-all inline-flex items-center gap-2 cursor-pointer"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            <span>PDF</span>
            <span className="text-[10px] opacity-80">↗</span>
          </a>

          <button
            type="button"
            onClick={onReset}
            className="px-3 py-2 text-xs font-medium text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200 cursor-pointer ml-auto"
          >
            New Research
          </button>
        </div>
      </div>

      {/* Product Keywords Section */}
      {summary.keywords && summary.keywords.length > 0 && (
        <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/60 dark:bg-zinc-950/40 p-4 space-y-2.5">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider">
              Product-Derived Keywords ({summary.keywords.length})
            </h3>
            <span className="text-[10px] text-zinc-400">Grounded in website catalog & offerings</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {summary.keywords.map((kw, kwIdx) => (
              <span
                key={kwIdx}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-700 dark:text-zinc-300"
              >
                <span className="font-medium">{kw.keyword}</span>
                <span className="text-[9px] uppercase px-1 py-0.2 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 font-mono">
                  {kw.intent}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
