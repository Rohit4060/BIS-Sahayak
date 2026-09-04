import { SendIcon } from "./icons";
import { sampleQueries } from "../../lib/mockData";
import type { Citation } from "../../lib/api";
import CitationList from "./CitationList";

type QueryInputProps = {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  submitted: boolean;
  loading: boolean;
  reply: string;
  citations: Citation[];
  error: string;
};

export default function QueryInput({ value, onChange, onSubmit, submitted, loading, reply, citations, error }: QueryInputProps) {
  return (
    <div className="rounded-2xl border border-[var(--bis-border)] bg-white p-5 shadow-sm sm:p-6">
      <p className="font-display text-lg font-semibold text-[var(--bis-navy)] sm:text-xl">Ask BIS Sahayak AI</p>
      <p className="mt-1 text-sm text-[var(--bis-ink-soft)]">
        Describe your product or paste a standard number — Sahayak finds what applies.
      </p>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          placeholder="e.g. What Indian Standard applies to household pressure cookers?"
          className="w-full flex-1 resize-none rounded-xl border border-[var(--bis-border)] bg-[var(--bis-paper)] px-4 py-3 text-sm text-[var(--bis-ink)] outline-none focus:border-[var(--bis-chakra)] focus:ring-2 focus:ring-[var(--bis-chakra)]/20"
        />
        <button
          onClick={onSubmit}
          disabled={loading}
          className="flex items-center justify-center gap-2 rounded-xl bg-[var(--bis-navy)] px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-[var(--bis-navy-deep)] disabled:opacity-60 sm:w-auto"
        >
          <span>{loading ? "Asking..." : "Ask Sahayak"}</span>
          <SendIcon aria-hidden="true" className="h-4 w-4 shrink-0" />
        </button>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {sampleQueries.map((q) => (
          <button
            key={q}
            onClick={() => onChange(q)}
            className="rounded-full border border-[var(--bis-border)] px-3 py-1 font-mono text-[11px] text-[var(--bis-ink-soft)] hover:border-[var(--bis-chakra)] hover:text-[var(--bis-chakra)]"
          >
            {q}
          </button>
        ))}
      </div>
      {submitted && <div className="mt-4 rounded-lg bg-[var(--bis-paper)] px-4 py-3 text-sm text-[var(--bis-ink-soft)]">{loading ? "Sahayak is reviewing retrieved BIS evidence..." : error ? <p role="alert" className="text-red-700">{error}</p> : <><p className="whitespace-pre-wrap leading-relaxed text-[var(--bis-ink)]">{reply}</p><CitationList citations={citations} /></>}</div>}
    </div>
  );
}
