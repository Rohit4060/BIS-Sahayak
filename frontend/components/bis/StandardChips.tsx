import { standardCodes } from "../../lib/mockData";

export default function StandardChips() {
  return (
    <div className="pointer-events-none absolute inset-0 hidden overflow-hidden lg:block" aria-hidden="true">
      {standardCodes.map((code, i) => (
        <span
          key={code}
          className="absolute rounded-full border border-[var(--bis-border)] bg-white px-2.5 py-1 font-mono text-[10px] text-[var(--bis-ink-soft)] shadow-sm"
          style={{ top: `${(i * 37) % 90}%`, left: `${(i * 53) % 92}%`, opacity: 0.5 }}
        >
          {code}
        </span>
      ))}
    </div>
  );
}