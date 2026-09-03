import { navItems } from "../../lib/mockData";
import { ChatIcon, ShieldCheckIcon, BookIcon, FlaskIcon, BadgeIcon } from "./icons";

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
};

export default function Sidebar({ activeId, onSelect }: SidebarProps) {
  return (
    <div className="flex h-full flex-col bg-[var(--bis-navy-deep)] text-white">
      <div className="flex items-center gap-3 border-b border-white/10 px-6 py-6">
        <div className="relative flex h-10 w-10 items-center justify-center rounded-full bg-[var(--bis-navy)] font-display text-xs font-semibold">
          BIS
          <span className="absolute inset-0 rounded-full border border-white/15" />
        </div>
        <div>
          <p className="font-display text-sm font-semibold tracking-wide">BIS Sahayak AI</p>
          <p className="text-[11px] text-white/50">Hackathon Prototype</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-5">
        {navItems.map((item) => {
          const Icon = iconMap[item.id];
          const active = item.id === activeId;
          return (
            <button
              key={item.id}
              onClick={() => onSelect(item.id)}
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                active ? "bg-white/10 font-medium text-white" : "text-white/60 hover:bg-white/5 hover:text-white"
              }`}
            >
              <span
                className={`flex h-7 w-7 items-center justify-center rounded-md ${
                  active ? "bg-[var(--bis-saffron)]/90" : "bg-white/5"
                }`}
              >
                <Icon className="h-4 w-4" />
              </span>
              {item.label}
              {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[var(--bis-chakra)]" />}
            </button>
          );
        })}
      </nav>

      <div className="border-t border-white/10 px-4 py-4 text-[11px] text-white/40">
        <p>Not an official BIS service.</p>
        <p className="mt-1">v0.1 · Demo build</p>
      </div>
    </div>
  );
}
