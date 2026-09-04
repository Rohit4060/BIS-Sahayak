import { stats } from "../../lib/mockData";

export default function StatsStrip() {
  return (
    <section aria-label="Knowledge base summary" className="grid grid-cols-1 divide-y divide-[var(--bis-border)] rounded-xl border border-[var(--bis-border)] bg-white/70 p-2 shadow-[0_1px_2px_rgb(15_36_61_/_3%)] sm:grid-cols-3 sm:divide-x sm:divide-y-0">
      {stats.map((s) => (
        <div key={s.label} className="flex items-baseline gap-2 px-3 py-3 sm:flex-col sm:items-start sm:gap-1 sm:px-4">
          <p className="font-display text-xl font-semibold tracking-[-0.03em] text-[var(--bis-navy)]">{s.value}</p>
          <p className="text-xs text-[var(--bis-ink-soft)]">{s.label}</p>
        </div>
      ))}
    </section>
  );
}
