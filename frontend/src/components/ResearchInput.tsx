import { SourceType } from '../types/research';

interface Props {
  sourceType: SourceType;
  value: string;
  onChange: (val: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}

const PLACEHOLDERS: Record<SourceType, string> = {
  website: 'https://example.com or example.com',
  company: 'e.g. Linear, Stripe, Figma',
  social: 'e.g. linkedin.com/company/stripe or @linear',
  product: 'e.g. Slack Connect, Notion AI',
  service: 'e.g. Managed Cloud Migration, Penetration Testing'
};

export const ResearchInput: React.FC<Props> = ({ sourceType, value, onChange, onSubmit, disabled }) => {
  return (
    <div className="w-full">
      <input
        type="text"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && value.trim() && !disabled) {
            onSubmit();
          }
        }}
        placeholder={PLACEHOLDERS[sourceType]}
        className="w-full px-4 py-3 text-sm rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100 transition-all shadow-sm disabled:opacity-50"
      />
    </div>
  );
};
