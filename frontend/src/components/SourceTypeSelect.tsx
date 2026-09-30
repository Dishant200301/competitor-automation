import { SourceType } from '../types/research';

interface Props {
  value: SourceType;
  onChange: (val: SourceType) => void;
  disabled?: boolean;
}

const OPTIONS: { value: SourceType; label: string }[] = [
  { value: 'website', label: 'Website URL' },
  { value: 'company', label: 'Company Name' },
  { value: 'social', label: 'Social Profile' },
  { value: 'product', label: 'Product Name' },
  { value: 'service', label: 'Service / Offering' }
];

export const SourceTypeSelect: React.FC<Props> = ({ value, onChange, disabled }) => {
  return (
    <div className="flex flex-wrap gap-2">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          disabled={disabled}
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
            value === opt.value
              ? 'bg-zinc-900 text-white dark:bg-white dark:text-zinc-900 shadow-sm'
              : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
};
