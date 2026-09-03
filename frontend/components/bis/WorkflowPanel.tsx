"use client";

import { useState } from "react";
import { api, type Citation, type ComplianceResponse, type HelpResponse, type LabsResponse, type RecommendResponse } from "../../lib/api";
import CitationList from "./CitationList";

type Workflow = "standards" | "compliance" | "hallmarking" | "consumer" | "laboratories";
type PanelResponse = RecommendResponse | ComplianceResponse | HelpResponse | LabsResponse;

const copy: Record<Workflow, { title: string; description: string; label: string; placeholder: string; button: string }> = {
  standards: { title: "Find applicable standards", description: "Get evidence-backed BIS standard recommendations for a product.", label: "Product description", placeholder: "e.g. electric pressure cooker", button: "Find standards" },
  compliance: { title: "Check compliance evidence", description: "Review only the requirements supported by the available BIS sources.", label: "Product description", placeholder: "e.g. household electrical appliance", button: "Check compliance" },
  hallmarking: { title: "Hallmarking help", description: "Ask a question about hallmarking evidence and consumer-facing guidance.", label: "Hallmarking question", placeholder: "e.g. What markings are required on hallmarked jewellery?", button: "Ask about hallmarking" },
  consumer: { title: "Consumer help", description: "Ask about quality complaints or BIS-certified product concerns.", label: "Your question", placeholder: "e.g. How can I complain about a BIS certified product?", button: "Get consumer help" },
  laboratories: { title: "Find laboratories", description: "Search the currently available laboratory records. Results may be empty.", label: "Product description", placeholder: "e.g. household electrical appliance", button: "Find laboratories" },
};

function Evidence({ evidence }: { evidence: { section?: string | null; page?: number | null; excerpt: string }[] }) {
  if (!evidence.length) return null;
  return <details className="mt-3 rounded-lg border border-[var(--bis-border)] p-3"><summary className="cursor-pointer text-xs font-medium text-[var(--bis-navy)]">View retrieved evidence</summary><div className="mt-3 space-y-3">{evidence.map((item, index) => <div key={`${item.section}-${index}`} className="text-xs text-[var(--bis-ink-soft)]"><p className="font-medium text-[var(--bis-ink)]">{item.section || "Retrieved excerpt"}{item.page ? ` · page ${item.page}` : ""}</p><p className="mt-1 whitespace-pre-wrap">{item.excerpt}</p></div>)}</div></details>;
}

function Limitations({ items }: { items: string[] }) { return items.length ? <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{items.map((item) => <p key={item}>{item}</p>)}</div> : null; }

export default function WorkflowPanel({ workflow }: { workflow: Workflow }) {
  const [value, setValue] = useState("");
  const [standardNumber, setStandardNumber] = useState("");
  const [response, setResponse] = useState<PanelResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const content = copy[workflow];

  async function submit() {
    if (!value.trim()) { setError(`${content.label} is required.`); return; }
    setLoading(true); setError(""); setResponse(null);
    try {
      const result = workflow === "standards" ? await api.recommend(value.trim())
        : workflow === "compliance" ? await api.compliance(value.trim())
        : workflow === "hallmarking" ? await api.hallmarking(value.trim())
        : workflow === "consumer" ? await api.consumer(value.trim())
        : await api.labs(value.trim(), standardNumber.trim() || undefined);
      setResponse(result);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not reach the BIS Sahayak backend."); }
    finally { setLoading(false); }
  }

  return <section className="rounded-2xl border border-[var(--bis-border)] bg-white p-5 shadow-sm sm:p-6"><h1 className="font-display text-xl font-semibold text-[var(--bis-navy)]">{content.title}</h1><p className="mt-1 text-sm text-[var(--bis-ink-soft)]">{content.description}</p><label className="mt-5 block text-sm font-medium text-[var(--bis-ink)]">{content.label}<textarea value={value} onChange={(event) => setValue(event.target.value)} rows={3} placeholder={content.placeholder} className="mt-2 w-full resize-none rounded-xl border border-[var(--bis-border)] bg-[var(--bis-paper)] px-4 py-3 text-sm outline-none focus:border-[var(--bis-chakra)]" /></label>{workflow === "laboratories" && <label className="mt-3 block text-sm font-medium text-[var(--bis-ink)]">Standard number <span className="font-normal text-[var(--bis-ink-soft)]">(optional)</span><input value={standardNumber} onChange={(event) => setStandardNumber(event.target.value)} placeholder="e.g. IS 302" className="mt-2 w-full rounded-xl border border-[var(--bis-border)] bg-[var(--bis-paper)] px-4 py-3 text-sm outline-none focus:border-[var(--bis-chakra)]" /></label>}<button onClick={submit} disabled={loading} className="mt-4 rounded-xl bg-[var(--bis-navy)] px-5 py-3 text-sm font-medium text-white hover:bg-[var(--bis-navy-deep)] disabled:opacity-60">{loading ? "Searching BIS evidence..." : content.button}</button>{error && <p role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}{response && <Result workflow={workflow} response={response} />}</section>;
}

function Result({ workflow, response }: { workflow: Workflow; response: PanelResponse }) {
  if (workflow === "standards") { const data = response as RecommendResponse; return <div className="mt-6"><p className="text-sm text-[var(--bis-ink-soft)]">{data.message || `${data.recommendations.length} evidence-backed recommendation(s) found.`}</p>{data.recommendations.map((item) => <article key={item.standard_number || item.title} className="mt-4 rounded-xl border border-[var(--bis-border)] p-4"><p className="font-display font-semibold text-[var(--bis-navy)]">{item.standard_number || item.title}</p><p className="mt-1 text-sm">{item.reason}</p><p className="mt-2 text-xs font-medium text-[var(--bis-green)]">{item.requirement_status}</p><Evidence evidence={item.evidence} /><CitationList citations={item.citations} /></article>)}</div>; }
  if (workflow === "compliance") { const data = response as ComplianceResponse; return <div className="mt-6"><p className="text-sm text-[var(--bis-ink-soft)]">{data.message || "Requirements shown below are grounded in retrieved evidence."}</p>{data.standards.map((item) => <article key={item.standard_number || item.title} className="mt-4 rounded-xl border border-[var(--bis-border)] p-4"><p className="font-display font-semibold text-[var(--bis-navy)]">{item.standard_number || item.title}</p>{item.requirements.map((requirement, index) => <div key={index} className="mt-3 rounded-lg bg-[var(--bis-paper)] p-3 text-sm"><p className="font-medium">{requirement.requirement}</p><p className="mt-1 text-xs text-[var(--bis-ink-soft)]">{requirement.status} · {requirement.reason}</p>{requirement.testing_requirement && <p className="mt-1 text-xs">Testing: {requirement.testing_requirement}</p>}{requirement.next_step && <p className="mt-1 text-xs">Next step: {requirement.next_step}</p>}</div>)}<Evidence evidence={item.evidence} /><CitationList citations={item.citations} /></article>)}<Limitations items={[data.limitations]} /></div>; }
  if (workflow === "laboratories") { const data = response as LabsResponse; return <div className="mt-6"><p className="text-sm text-[var(--bis-ink-soft)]">{data.message || `${data.laboratories.length} laboratory result(s) found.`}</p>{data.laboratories.map((lab) => <article key={lab.name} className="mt-4 rounded-xl border border-[var(--bis-border)] p-4"><p className="font-display font-semibold text-[var(--bis-navy)]">{lab.name}</p><p className="mt-1 text-sm text-[var(--bis-ink-soft)]">{lab.location || "Location unavailable"}</p><p className="mt-2 text-xs">{lab.reason}</p><p className="mt-2 text-xs">{lab.testing_capabilities.join(", ") || "Capabilities unavailable"}</p><CitationList citations={lab.citations} /></article>)}<Limitations items={data.limitations} /></div>; }
  const data = response as HelpResponse; return <div className="mt-6 rounded-xl bg-[var(--bis-paper)] p-4"><p className="whitespace-pre-wrap text-sm leading-relaxed">{data.answer}</p>{data.key_points.length > 0 && <><p className="mt-4 text-xs font-semibold uppercase tracking-wide">Key points</p><ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{data.key_points.map((point) => <li key={point}>{point}</li>)}</ul></>}{data.next_steps.length > 0 && <><p className="mt-4 text-xs font-semibold uppercase tracking-wide">Next steps</p><ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{data.next_steps.map((step) => <li key={step}>{step}</li>)}</ul></>}<CitationList citations={data.citations as Citation[]} /><Limitations items={data.limitations} /></div>;
}
