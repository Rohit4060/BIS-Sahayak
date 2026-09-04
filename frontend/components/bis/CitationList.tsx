import type { Citation } from "../../lib/api";

export default function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;

  return (
    <section className="mt-6 border-t border-[var(--bis-border)] pt-5">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--bis-ink-soft)]">
        Sources from retrieved BIS evidence
      </p>
      <div className="mt-3 space-y-2">
        {citations.map((citation, index) => (
          <div key={`${citation.source_url}-${citation.page}-${index}`} className="rounded-lg border border-[var(--bis-border)] bg-white p-3 text-xs leading-5 text-[var(--bis-ink-soft)]">
            <p className="font-medium text-[var(--bis-ink)]">
              {citation.standard_number || citation.source_reference || "BIS source"}
              {citation.clause ? ` · ${citation.clause}` : ""}
              {citation.page ? ` · page ${citation.page}` : ""}
            </p>
            {citation.source_url ? (
              <a className="mt-1 inline-block break-all font-medium text-[var(--bis-chakra)] underline decoration-blue-300 underline-offset-2 hover:text-[var(--bis-navy)]" href={citation.source_url} target="_blank" rel="noreferrer">
                {citation.source_url}
              </a>
            ) : <p className="mt-1">Official source URL unavailable</p>}
          </div>
        ))}
      </div>
    </section>
  );
}
