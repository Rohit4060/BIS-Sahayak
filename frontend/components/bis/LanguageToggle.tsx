import { languageOptions, type LanguageCode } from "../../lib/api";

type LanguageToggleProps = {
  compact?: boolean;
  value: LanguageCode;
  onChange: (language: LanguageCode) => void;
};

export default function LanguageToggle({ compact = false, value, onChange }: LanguageToggleProps) {
  return (
    <label className={`inline-flex items-center gap-2 rounded-full border border-[var(--bis-border)] bg-white px-2 py-1.5 shadow-sm ${compact ? "text-[11px]" : "text-xs"}`}>
      <span className="sr-only">Response language</span>
      <select value={value} onChange={(event) => onChange(event.target.value as LanguageCode)} className="max-w-28 bg-transparent font-medium text-[var(--bis-navy)] outline-none">
        {languageOptions.map((language) => <option key={language.code} value={language.code}>{language.label}</option>)}
      </select>
    </label>
  );
}
