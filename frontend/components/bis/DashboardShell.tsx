"use client";

import { useState } from "react";
import Sidebar from "./Sidebar";
import MobileHeader from "./MobileHeader";
import LanguageToggle from "./LanguageToggle";
import QueryInput from "./QueryInput";
import QuickActions from "./QuickActions";
import StatsStrip from "./StatsStrip";
import StandardChips from "./StandardChips";
import WorkflowPanel from "./WorkflowPanel";
import { CloseIcon } from "./icons";
import { api, type Citation, type LanguageCode } from "../../lib/api";

type NavId = "ask-bis" | "standards" | "compliance" | "hallmarking" | "consumer" | "laboratories";

export default function DashboardShell() {
  const [activeNav, setActiveNav] = useState<NavId>("ask-bis");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const [language, setLanguage] = useState<LanguageCode>("en");
  const [query, setQuery] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [reply, setReply] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [error, setError] = useState("");

  const handleQuickSelect = (id: string, prompt: string) => {
    const workflowByAction: Record<string, NavId> = { "find-standard": "standards", "certification-guidance": "compliance", "testing-requirements": "compliance", "laboratory-finder": "laboratories" };
    const destination = workflowByAction[id] ?? "ask-bis";
    setActiveNav(destination); setQuery(destination === "ask-bis" ? prompt : ""); setSubmittedQuestion(""); setSubmitted(false); setReply(""); setCitations([]); setError("");
  };
  const handleSubmit = async () => {
    if (!query.trim()) return;
    const question = query.trim();
    setSubmittedQuestion(question); setSubmitted(true); setLoading(true); setReply(""); setCitations([]); setError("");
    try { const data = await api.chat(question, language); setReply(data.reply); setCitations(data.citations); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Could not reach the Sahayak backend."); }
    finally { setLoading(false); }
  };

  return <div className="app-background min-h-screen lg:flex">
    <aside className={`hidden shrink-0 transition-[width] duration-200 lg:block ${sidebarExpanded ? "lg:w-72" : "lg:w-20"}`}><div className={`fixed h-screen transition-[width] duration-200 ${sidebarExpanded ? "w-72" : "w-20"}`}><Sidebar activeId={activeNav} onSelect={(id) => setActiveNav(id as NavId)} collapsed={!sidebarExpanded} onToggle={() => setSidebarExpanded((expanded) => !expanded)} /></div></aside>
    {drawerOpen && <div className="fixed inset-0 z-40 lg:hidden"><div className="absolute inset-0 bg-black/40" onClick={() => setDrawerOpen(false)} /><div className="relative h-full w-72"><Sidebar activeId={activeNav} onSelect={(id) => { setActiveNav(id as NavId); setDrawerOpen(false); }} variant="drawer" /><button onClick={() => setDrawerOpen(false)} aria-label="Close navigation" className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-md bg-white/10 text-white"><CloseIcon className="h-4 w-4" /></button></div></div>}
    <div className="min-w-0 flex-1"><MobileHeader onOpenMenu={() => setDrawerOpen(true)} language={language} onLanguageChange={setLanguage} />
      <main className="mx-auto max-w-6xl px-4 py-7 sm:px-6 sm:py-9 lg:px-10 lg:py-12"><div className="hidden items-start justify-between lg:flex"><div><p className="brand-gradient font-display text-3xl font-semibold tracking-[-0.035em] xl:text-[2rem]">BIS Sahayak AI</p><p className="mt-2 text-sm text-[var(--bis-ink-soft)]">Indian Standards &amp; Compliance Copilot</p></div><LanguageToggle value={language} onChange={setLanguage} /></div>
        {activeNav === "ask-bis" ? <><div className="relative mt-7 lg:mt-10"><StandardChips /><div className="relative z-10"><QueryInput value={query} question={submittedQuestion} onChange={setQuery} onSubmit={handleSubmit} submitted={submitted} loading={loading} reply={reply} citations={citations} error={error} /></div></div><div className="mt-9"><QuickActions onSelect={handleQuickSelect} /></div></> : <div className="mt-7 lg:mt-10"><WorkflowPanel workflow={activeNav} /></div>}<div className="mt-9"><StatsStrip /></div></main>
    </div>
  </div>;
}
