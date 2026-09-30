import React from 'react';
import { ResearchRun } from '../types/research';

interface Props {
  run?: ResearchRun | null;
  progressPercentage?: number;
  statusText?: string;
  currentStep?: string;
}

export const ResearchProgress: React.FC<Props> = ({ run, progressPercentage, statusText, currentStep }) => {
  const percent = progressPercentage !== undefined ? progressPercentage : (run?.progress_percentage ?? 0);
  const status = statusText || run?.status?.replace(/_/g, ' ') || 'running';
  const step = currentStep || run?.current_step || 'Initializing intelligence pipeline...';

  return (
    <div className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 shadow-sm space-y-5">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500"></span>
          </span>
          <span className="font-mono uppercase font-semibold text-zinc-700 dark:text-zinc-300">
            Status: {status}
          </span>
        </div>
        <span className="font-mono text-sm font-bold text-zinc-900 dark:text-zinc-100">
          {Math.round(percent)}%
        </span>
      </div>

      {/* Progress Bar with smooth animated transition */}
      <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-2.5 rounded-full overflow-hidden p-0.5">
        <div
          className="bg-gradient-to-r from-blue-600 via-indigo-600 to-emerald-500 h-full rounded-full transition-all duration-300 ease-out shadow-sm"
          style={{ width: `${Math.max(3, Math.min(100, percent))}%` }}
        />
      </div>



      <div className="flex items-center justify-between gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800/80">
        <p className="text-xs text-zinc-600 dark:text-zinc-400 font-mono flex-1">
          {step}
        </p>
        <span className="text-[10px] text-zinc-400 font-mono">Single API Call</span>
      </div>
    </div>
  );
};
