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
      className="group flex h-full flex-col items-start rounded-xl border border-[var(--bis-border)] bg-white p-5 text-left shadow-[0_1px_2px_rgb(15_36_61_/_3%)] transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--bis-chakra)] hover:shadow-[0_12px_24px_rgb(15_36_61_/_9%)]"
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--bis-navy)]/5 text-[var(--bis-navy)] group-hover:bg-[var(--bis-chakra)]/10 group-hover:text-[var(--bis-chakra)]">
        <Icon className="h-5 w-5" />
      </span>
      <p className="mt-4 font-display text-sm font-semibold text-[var(--bis-ink)]">{title}</p>
      <p className="mt-1.5 text-xs leading-5 text-[var(--bis-ink-soft)]">{description}</p>
    </button>
  );
}
