interface Props {
  message: string;
  onRetry: () => void;
}

export const ErrorMessage: React.FC<Props> = ({ message, onRetry }) => {
  return (
    <div className="w-full bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-xl p-6 text-center space-y-4">
      <div className="text-red-700 dark:text-red-400 text-sm font-medium">
        {message}
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="px-4 py-2 text-xs font-semibold bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors cursor-pointer"
      >
        Try Again
      </button>
    </div>
  );
};
