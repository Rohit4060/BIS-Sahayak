import { MenuIcon } from "./icons";
import LanguageToggle from "./LanguageToggle";
import type { LanguageCode } from "../../lib/api";

type MobileHeaderProps = { onOpenMenu: () => void; language: LanguageCode; onLanguageChange: (language: LanguageCode) => void };

export default function MobileHeader({ onOpenMenu, language, onLanguageChange }: MobileHeaderProps) {
  return (
    <div className="sticky top-0 z-30 flex items-center justify-between border-b border-[var(--bis-border)] bg-[var(--bis-paper)]/90 px-4 py-3 backdrop-blur lg:hidden">
      <button
        onClick={onOpenMenu}
        aria-label="Open navigation"
        className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--bis-border)] bg-white shadow-sm"
      >
        <MenuIcon className="h-5 w-5 text-[var(--bis-navy)]" />
      </button>
      <div className="text-center">
        <p className="brand-gradient font-display text-sm font-semibold tracking-[-0.02em]">BIS Sahayak AI</p>
      </div>
      <LanguageToggle compact value={language} onChange={onLanguageChange} />
    </div>
  );
}
