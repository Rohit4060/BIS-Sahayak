import type { Citation } from "../../lib/api";

export default function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return <section className="mt-5 border-t border-[var(--bis-border)] pt-4"><p className="text-xs font-semibold uppercase tracking-wide text-[var(--bis-ink-soft)]">Sources from retrieved BIS evidence</p><div className="mt-2 space-y-2">{citations.map((citation, index) => <div key={`${citation.source_url}-${citation.page}-${index}`} className="rounded-lg bg-[var(--bis-paper)] p-3 text-xs text-[var(--bis-ink-soft)]"><p className="font-medium text-[var(--bis-ink)]">{citation.standard_number || citation.source_reference || "BIS source"}{citation.clause ? ` · ${citation.clause}` : ""}{citation.page ? ` · page ${citation.page}` : ""}</p>{citation.source_url ? <a className="mt-1 inline-block break-all text-[var(--bis-chakra)] underline" href={citation.source_url} target="_blank" rel="noreferrer">{citation.source_url}</a> : <p className="mt-1">Official source URL unavailable</p>}</div>)}</div></section>;
}
