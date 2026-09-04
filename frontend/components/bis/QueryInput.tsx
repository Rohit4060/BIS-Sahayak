import { SendIcon } from "./icons";
import { sampleQueries } from "../../lib/mockData";
import type { Citation } from "../../lib/api";
import CitationList from "./CitationList";

type QueryInputProps = {
  value: string;
  question: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  submitted: boolean;
  loading: boolean;
  reply: string;
  citations: Citation[];
  error: string;
};

export default function QueryInput({ value, question, onChange, onSubmit, submitted, loading, reply, citations, error }: QueryInputProps) {
  return (
    <section aria-labelledby="ask-title" className="surface-card overflow-hidden rounded-[1.35rem]">
      <div className="border-b border-[var(--bis-border)] bg-[linear-gradient(115deg,#fff,#f4f8fd)] px-5 py-6 sm:px-7 sm:py-8">
        <p className="text-xs font-semibold tracking-[0.12em] text-[var(--bis-chakra)]">EVIDENCE-GROUNDED ASSISTANCE</p>
        <h1 id="ask-title" className="mt-2 font-display text-2xl font-semibold tracking-[-0.04em] text-[var(--bis-navy)] sm:text-[1.75rem]">Ask BIS Sahayak <span className="bg-[linear-gradient(110deg,#102f52,#496fae)] bg-clip-text text-transparent">AI</span></h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--bis-ink-soft)]">Describe your product or paste a standard number — Sahayak finds what applies.</p>
      </div>

      {submitted && <div aria-live="polite" className="space-y-5 bg-[#f8fafc] px-5 py-6 sm:px-7">
        <div className="ml-auto max-w-[88%] rounded-2xl rounded-tr-md border border-[#d8e3f0] bg-[#edf4fb] px-4 py-3 text-sm leading-6 text-[var(--bis-ink)] shadow-sm">{question}</div>
        <div className="max-w-[94%] rounded-2xl rounded-tl-md border border-[var(--bis-border)] bg-white p-4 shadow-[0_3px_12px_rgb(15_36_61_/_5%)] sm:p-5">
          <div className="flex items-center gap-2"><span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--bis-navy)] text-[10px] font-semibold text-white">BIS</span><p className="text-xs font-semibold text-[var(--bis-navy)]">Answer based on BIS documents</p></div>
          {loading ? <div className="mt-4 flex items-center gap-3 text-sm text-[var(--bis-ink-soft)]"><span className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--bis-chakra)] border-t-transparent" />Searching BIS documents and preparing your answer...</div> : error ? <p role="alert" className="mt-4 text-sm leading-6 text-red-700">{error}</p> : <><p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-[var(--bis-ink)]">{reply}</p><CitationList citations={citations} /></>}
        </div>
      </div>}

      <div className="border-t border-[var(--bis-border)] bg-white px-5 py-5 sm:px-7 sm:py-6">
        <div className="rounded-2xl border border-[var(--bis-border)] bg-[#fbfcfe] p-2 shadow-[0_5px_16px_rgb(15_36_61_/_5%)] transition-shadow focus-within:border-[var(--bis-chakra)] focus-within:shadow-[0_0_0_4px_var(--bis-ring)]">
          <textarea value={value} onChange={(event) => onChange(event.target.value)} disabled={loading} rows={3} placeholder="e.g. What Indian Standard applies to household pressure cookers?" aria-label="Ask a question about BIS standards or compliance" className="w-full resize-none bg-transparent px-3 py-2 text-sm leading-6 text-[var(--bis-ink)] outline-none placeholder:text-[var(--bis-ink-soft)] disabled:cursor-not-allowed disabled:opacity-60" />
          <div className="flex items-center justify-end border-t border-[var(--bis-border)] px-1 pt-2"><button onClick={onSubmit} disabled={loading} className="primary-button flex min-h-10 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"><span>{loading ? "Asking..." : "Ask Sahayak"}</span><SendIcon aria-hidden="true" className="h-4 w-4 shrink-0" /></button></div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2" aria-label="Suggested questions">{sampleQueries.map((question) => <button key={question} onClick={() => onChange(question)} disabled={loading} className="rounded-full border border-[#d8e1eb] bg-white px-3 py-1.5 text-left text-[11px] font-medium text-[var(--bis-navy)] transition-colors hover:border-[var(--bis-chakra)] hover:bg-[#f1f6fc] disabled:cursor-not-allowed disabled:opacity-60">{question}</button>)}</div>
      </div>
    </section>
  );
}
