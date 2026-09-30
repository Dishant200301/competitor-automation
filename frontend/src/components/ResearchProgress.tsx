import { ResearchRun } from '../types/research';

interface Props {
  run: ResearchRun;
}

export const ResearchProgress: React.FC<Props> = ({ run }) => {
  return (
    <div className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 shadow-sm space-y-4">
      <div className="flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
        <span className="font-mono uppercase font-semibold text-zinc-700 dark:text-zinc-300">
          Status: {run.status.replace(/_/g, ' ')}
        </span>
        <span className="font-mono font-medium">{run.progress_percentage}%</span>
      </div>

      <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-2 rounded-full overflow-hidden">
        <div
          className="bg-zinc-900 dark:bg-zinc-100 h-full rounded-full transition-all duration-500 ease-out"
          style={{ width: `${Math.max(5, run.progress_percentage)}%` }}
        />
      </div>

      <p className="text-sm text-zinc-600 dark:text-zinc-400 font-mono">
        {run.current_step || 'Initializing research pipeline...'}
      </p>
    </div>
  );
};
