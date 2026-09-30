import { useState, useEffect, useRef } from 'react';
import { SourceType, ResearchRun, ResearchSummary } from '../types/research';
import { createResearchRun, getResearchStatus, getResearchSummary } from '../services/api';
import { SourceTypeSelect } from '../components/SourceTypeSelect';
import { ResearchInput } from '../components/ResearchInput';
import { RunResearchButton } from '../components/RunResearchButton';
import { ResearchProgress } from '../components/ResearchProgress';
import { ResearchComplete } from '../components/ResearchComplete';
import { ErrorMessage } from '../components/ErrorMessage';

export const ResearchPage: React.FC = () => {
  const [sourceType, setSourceType] = useState<SourceType>('website');
  const [sourceInput, setSourceInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentRun, setCurrentRun] = useState<ResearchRun | null>(null);
  const [summary, setSummary] = useState<ResearchSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollTimerRef = useRef<number | null>(null);

  const startResearch = async () => {
    if (!sourceInput.trim()) return;

    setError(null);
    setSummary(null);
    setLoading(true);

    try {
      const { research_run_id } = await createResearchRun(sourceType, sourceInput);
      pollRun(research_run_id);
    } catch (err: any) {
      setError(err.message || 'Failed to start research');
      setLoading(false);
    }
  };

  const pollRun = (runId: string) => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);

    pollTimerRef.current = window.setInterval(async () => {
      try {
        const run = await getResearchStatus(runId);
        setCurrentRun(run);

        if (run.status === 'completed') {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          const summ = await getResearchSummary(runId);
          setSummary(summ);
          setLoading(false);
        } else if (run.status === 'failed') {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          setError(run.error_message || 'Research execution encountered an error.');
          setLoading(false);
        }
      } catch (err: any) {
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        setError(err.message || 'Error communicating with backend server.');
        setLoading(false);
      }
    }, 1500);
  };

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  const handleReset = () => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    setCurrentRun(null);
    setSummary(null);
    setError(null);
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col justify-between p-6 sm:p-12">
      <div className="max-w-3xl w-full mx-auto space-y-10">
        {/* Minimal Header */}
        <header className="space-y-2">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Competitor Intelligence
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Autonomous discovery, deterministic website & SEO crawling, and structured intelligence reports.
          </p>
        </header>

        {/* Input Controls */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 shadow-sm space-y-5">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 uppercase tracking-wider">
              1. Select Source Type
            </label>
            <SourceTypeSelect
              value={sourceType}
              onChange={setSourceType}
              disabled={loading}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 uppercase tracking-wider">
              2. Enter Target Entity
            </label>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex-1">
                <ResearchInput
                  sourceType={sourceType}
                  value={sourceInput}
                  onChange={setSourceInput}
                  onSubmit={startResearch}
                  disabled={loading}
                />
              </div>
              <RunResearchButton
                onClick={startResearch}
                disabled={!sourceInput.trim()}
                loading={loading}
              />
            </div>
          </div>
        </div>

        {/* Execution State */}
        {loading && currentRun && (
          <ResearchProgress run={currentRun} />
        )}

        {summary && (
          <ResearchComplete summary={summary} onReset={handleReset} />
        )}

        {error && (
          <ErrorMessage message={error} onRetry={handleReset} />
        )}
      </div>

      <footer className="text-center text-xs text-zinc-400 dark:text-zinc-600 py-6">
        Verified Intelligence • Strict Source Traceability • No AI-hallucinated metrics
      </footer>
    </div>
  );
};
