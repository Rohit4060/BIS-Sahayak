import { quickActions } from "../../lib/mockData";
import QuickActionCard from "./QuickActionCard";
import { SearchIcon, BadgeIcon, FlaskIcon, MapPinIcon } from "./icons";

const iconMap = {
  "find-standard": SearchIcon,
  "certification-guidance": BadgeIcon,
  "testing-requirements": FlaskIcon,
  "laboratory-finder": MapPinIcon,
};

type QuickActionsProps = { onSelect: (id: string, prompt: string) => void };

export default function QuickActions({ onSelect }: QuickActionsProps) {
  return (
    <div>
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--bis-ink-soft)]">Quick actions</p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {quickActions.map((action) => (
          <QuickActionCard
            key={action.id}
            title={action.title}
            description={action.description}
            icon={iconMap[action.id as keyof typeof iconMap]}
            onClick={() => onSelect(action.id, action.prompt)}
          />
        ))}
      </div>
    </div>
  );
}
