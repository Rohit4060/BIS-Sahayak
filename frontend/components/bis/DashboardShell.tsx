"use client";

import { useState } from "react";
import Sidebar from "./Sidebar";
import MobileHeader from "./MobileHeader";
import LanguageToggle from "./LanguageToggle";
import QueryInput from "./QueryInput";
import QuickActions from "./QuickActions";
import StatsStrip from "./StatsStrip";
import StandardChips from "./StandardChips";
import { CloseIcon } from "./icons";

export default function DashboardShell() {
  const [activeNav, setActiveNav] = useState("ask-bis");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [reply, setReply] = useState("");

  const handleQuickSelect = (prompt: string) => {
    setQuery(prompt);
    setSubmitted(false);
    setReply("");
  };

  const handleSubmit = async () => {
    if (!query.trim()) return;
    setSubmitted(true);
    setLoading(true);
    setReply("");
    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: query }),
      });
      const data = await res.json();
      setReply(data.reply);
    } catch (err) {
      setReply("Error: could not reach Sahayak backend. Is it running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bis-paper)] lg:flex">
      {/* Desktop sidebar */}
      <aside className="hidden lg:block lg:w-72 lg:shrink-0">
        <div className="fixed h-screen w-72">
          <Sidebar activeId={activeNav} onSelect={setActiveNav} />
        </div>
      </aside>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setDrawerOpen(false)} />
          <div className="relative h-full w-72">
            <Sidebar
              activeId={activeNav}
              onSelect={(id) => {
                setActiveNav(id);
                setDrawerOpen(false);
              }}
              variant="drawer"
            />
            <button
              onClick={() => setDrawerOpen(false)}
              aria-label="Close navigation"
              className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-md bg-white/10 text-white"
            >
              <CloseIcon className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      <div className="flex-1">
        <MobileHeader onOpenMenu={() => setDrawerOpen(true)} />

        <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
          <div className="hidden items-start justify-between lg:flex">
            <div>
              <p className="font-display text-2xl font-semibold text-[var(--bis-navy)] xl:text-3xl">BIS Sahayak AI</p>
              <p className="mt-1 text-sm text-[var(--bis-ink-soft)]">Indian Standards &amp; Compliance Copilot</p>
            </div>
            <LanguageToggle />
          </div>

          <div className="relative mt-6 lg:mt-8">
            <StandardChips />
            <div className="relative z-10">
                <QueryInput
                value={query}
                onChange={setQuery}
                onSubmit={handleSubmit}
                submitted={submitted}
                loading={loading}
                reply={reply}
              />
            </div>
          </div>

          <div className="mt-8">
            <QuickActions onSelect={handleQuickSelect} />
          </div>

          <div className="mt-8">
            <StatsStrip />
          </div>
        </main>
      </div>
    </div>
  );
}