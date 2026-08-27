type QuickActionCardProps = {
  title: string;
  description: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  onClick: () => void;
};

export default function QuickActionCard({ title, description, icon: Icon, onClick }: QuickActionCardProps) {
  return (
    <button
      onClick={onClick}
      className="group flex h-full flex-col items-start rounded-xl border border-[var(--bis-border)] bg-white p-4 text-left transition-all hover:-translate-y-0.5 hover:border-[var(--bis-chakra)] hover:shadow-md"
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--bis-navy)]/5 text-[var(--bis-navy)] group-hover:bg-[var(--bis-chakra)]/10 group-hover:text-[var(--bis-chakra)]">
        <Icon className="h-5 w-5" />
      </span>
      <p className="mt-3 font-display text-sm font-semibold text-[var(--bis-ink)]">{title}</p>
      <p className="mt-1 text-xs leading-relaxed text-[var(--bis-ink-soft)]">{description}</p>
    </button>
  );
}