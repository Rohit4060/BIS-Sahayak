import { navItems } from "../../lib/mockData";
import { BadgeIcon, BookIcon, ChatIcon, FlaskIcon, MenuIcon, ShieldCheckIcon } from "./icons";

const iconMap: Record<string, React.ComponentType<React.SVGProps<SVGSVGElement>>> = {
  "ask-bis": ChatIcon,
  standards: BookIcon,
  compliance: ShieldCheckIcon,
  hallmarking: BadgeIcon,
  consumer: ChatIcon,
  laboratories: FlaskIcon,
};

type SidebarProps = {
  activeId: string;
  onSelect: (id: string) => void;
  variant?: "desktop" | "drawer";
  collapsed?: boolean;
  onToggle?: () => void;
};

export default function Sidebar({ activeId, onSelect, variant = "desktop", collapsed = false, onToggle }: SidebarProps) {
  return (
    <div className="flex h-full flex-col bg-[linear-gradient(160deg,var(--bis-navy-deep),var(--bis-navy))] text-white">
      <div className={`flex items-center border-b border-white/10 py-6 ${collapsed ? "justify-center px-3" : "gap-3 px-5"}`}>
        <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/10 font-display text-xs font-semibold shadow-inner shadow-white/10">
          BIS
          <span className="absolute inset-0 rounded-xl border border-white/15" />
        </div>
        {!collapsed && <div className="min-w-0"><p className="font-display text-sm font-semibold tracking-wide">BIS Sahayak AI</p><p className="mt-0.5 text-[11px] text-white/50">Indian Standards assistant</p></div>}
        {variant === "desktop" && !collapsed && <button onClick={onToggle} aria-label="Collapse navigation" className="ml-auto flex h-8 w-8 items-center justify-center rounded-lg text-white/60 transition-colors hover:bg-white/10 hover:text-white"><MenuIcon className="h-4 w-4" /></button>}
      </div>

      {variant === "desktop" && collapsed && <button onClick={onToggle} aria-label="Expand navigation" className="mx-auto mt-4 flex h-9 w-9 items-center justify-center rounded-lg text-white/60 transition-colors hover:bg-white/10 hover:text-white"><MenuIcon className="h-4 w-4" /></button>}
      <nav aria-label="Primary navigation" className={`flex-1 space-y-1 py-6 ${collapsed ? "px-2" : "px-3"}`}>
        {navItems.map((item) => {
          const Icon = iconMap[item.id];
          const active = item.id === activeId;
          return <button key={item.id} onClick={() => onSelect(item.id)} aria-current={active ? "page" : undefined} aria-label={collapsed ? item.label : undefined} title={collapsed ? item.label : undefined} className={`flex w-full items-center rounded-xl py-2.5 text-sm transition-all duration-150 ${collapsed ? "justify-center px-2" : "gap-3 px-3"} ${active ? "border-l-2 border-[var(--bis-accent)] bg-white/8 font-medium text-white" : "border-l-2 border-transparent text-white/60 hover:bg-white/5 hover:text-white"}`}>
            <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${active ? "bg-blue-200/15 text-blue-200" : "bg-white/5"}`}><Icon className="h-4 w-4" /></span>
            {!collapsed && item.label}
            {active && !collapsed && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[var(--bis-accent)]" />}
          </button>;
        })}
      </nav>

      {!collapsed && <div className="border-t border-white/10 px-5 py-5 text-[11px] leading-5 text-white/40"><p>Not an official BIS service.</p><p className="mt-1">v0.1 · Demo build</p></div>}
    </div>
  );
}
