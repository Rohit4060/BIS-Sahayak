import { stats } from "../../lib/mockData";

export default function StatsStrip() {
  return (
    <div className="grid grid-cols-1 gap-3 rounded-xl border border-[var(--bis-border)] bg-white/60 p-4 sm:grid-cols-3">
      {stats.map((s) => (
        <div key={s.label} className="flex items-baseline gap-2 sm:flex-col sm:items-start sm:gap-0.5">
          <p className="font-display text-xl font-semibold text-[var(--bis-navy)]">{s.value}</p>
          <p className="text-xs text-[var(--bis-ink-soft)]">{s.label}</p>
        </div>
      ))}
    </div>
  );
}