import { useState } from "react";

export default function LanguageToggle({ compact = false }: { compact?: boolean }) {
  const [lang, setLang] = useState<"en" | "hi">("en");
  return (
    <div className={`inline-flex rounded-full border border-[var(--bis-border)] bg-white p-0.5 ${compact ? "text-[11px]" : "text-xs"}`}>
      {(["en", "hi"] as const).map((code) => (
        <button
          key={code}
          onClick={() => setLang(code)}
          className={`rounded-full px-2.5 py-1 font-medium transition-colors ${
            lang === code ? "bg-[var(--bis-navy)] text-white" : "text-[var(--bis-ink-soft)]"
          }`}
        >
          {code === "en" ? "EN" : "हिं"}
        </button>
      ))}
    </div>
  );
}