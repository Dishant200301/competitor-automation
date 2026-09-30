import { useState, useEffect, useRef } from 'react';
import { SourceType, ResearchSummary } from '../types/research';
import { executeResearchSingleCall } from '../services/api';
import { ResearchInput } from '../components/ResearchInput';
import { RunResearchButton } from '../components/RunResearchButton';
import { ResearchProgress } from '../components/ResearchProgress';
import { ResearchComplete } from '../components/ResearchComplete';
import { ErrorMessage } from '../components/ErrorMessage';

export const ResearchPage: React.FC = () => {
  const [sourceType] = useState<SourceType>('website');
  const [sourceInput, setSourceInput] = useState('');
  const [context, setContext] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('Initializing research pipeline...');
  const [summary, setSummary] = useState<ResearchSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const animTimerRef = useRef<number | null>(null);

  const startResearch = async () => {
    if (!sourceInput.trim() || loading) return;

    setError(null);
    setSummary(null);
    setLoading(true);
    setProgress(0);
    setCurrentStep('Connecting to target website...');

    // Smoothly calculate and animate progress while the single API request executes
    const startTime = Date.now();
    if (animTimerRef.current) clearInterval(animTimerRef.current);

    animTimerRef.current = window.setInterval(() => {
      const elapsedSec = (Date.now() - startTime) / 1000;
      setProgress(prev => {
        let target = 0;
        let stepText = '';

        if (elapsedSec < 4) {
          target = (elapsedSec / 4) * 20; // 0% -> 20%
          stepText = 'Crawling target website & mapping public pages...';
        } else if (elapsedSec < 12) {
          target = 20 + ((elapsedSec - 4) / 8) * 25; // 20% -> 45%
          stepText = 'Extracting product catalog, services & offerings...';
        } else if (elapsedSec < 24) {
          target = 45 + ((elapsedSec - 12) / 12) * 25; // 45% -> 70%
          stepText = 'Analyzing business model & discovering search hypotheses...';
        } else if (elapsedSec < 45) {
          target = 70 + ((elapsedSec - 24) / 21) * 18; // 70% -> 88%
          stepText = 'Independently crawling & verifying competitor offerings...';
        } else {
          // Asymptotic ease towards 96%
          target = 88 + Math.min(8, (elapsedSec - 45) * 0.15);
          stepText = 'Finalizing evidence registry & compiling intelligence report...';
        }

        setCurrentStep(stepText);
        return Math.min(96, Math.max(prev, Math.round(target)));
      });
    }, 250);

    try {
      // Handled within ONE SINGLE API CALL!
      const result = await executeResearchSingleCall(sourceType, sourceInput, context);

      if (animTimerRef.current) clearInterval(animTimerRef.current);
      setProgress(100);
      setCurrentStep('Research complete! Rendering results...');

      setTimeout(() => {
        setSummary(result);
        setLoading(false);
      }, 400);
    } catch (err: any) {
      if (animTimerRef.current) clearInterval(animTimerRef.current);
      setError(err.message || 'Failed to complete competitor research');
      setLoading(false);
    }
  };

  useEffect(() => {
    return () => {
      if (animTimerRef.current) clearInterval(animTimerRef.current);
    };
  }, []);

  const handleReset = () => {
    if (animTimerRef.current) clearInterval(animTimerRef.current);
    setSummary(null);
    setError(null);
    setLoading(false);
    setProgress(0);
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
             Enter Website URL or social media link or product/service link
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
          <details className="text-xs text-zinc-500">
            <summary className="cursor-pointer">Optional company, product and social context</summary>
            <div className="grid gap-3 pt-3 sm:grid-cols-2">
              {Object.entries({company_name: 'Company name', product_url: 'Product URL', service_url: 'Service URL', social_url: 'Social profile URL'}).map(([key, label]) => (
                <label key={key} className="space-y-1">{label}
                  <input type={key.endsWith('_url') ? 'url' : 'text'} disabled={loading} value={context[key] || ''}
                    onChange={e => setContext({...context, [key]: e.target.value})}
                    className="block w-full rounded border border-zinc-300 bg-transparent p-2 dark:border-zinc-700" />
                </label>
              ))}
            </div>
          </details>
        </div>

        {/* Execution State */}
        {loading && (
          <ResearchProgress
            progressPercentage={progress}
            statusText={progress >= 100 ? 'Completed' : 'Analyzing'}
            currentStep={currentStep}
          />
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
