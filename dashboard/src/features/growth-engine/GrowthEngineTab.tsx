import React, { useState } from "react";
import { Profile } from "@/lib/api";
import {
  Crosshair, Sparkles, TrendingUp, Vote, Layers, BadgeCheck
} from "lucide-react";
import { usePersona } from "./hooks/usePersona";
import { F4FTab } from "./components/F4FTab";
import { SniperTab } from "./components/SniperTab";
import { HooksTab } from "./components/HooksTab";
import { ThreadsTab } from "./components/ThreadsTab";
import { PollsTab } from "./components/PollsTab";
import { TrendsTab } from "./components/TrendsTab";
import { SubTabType } from "./types";

export function GrowthEngineTab({ 
  profileId, 
  selectedProfile: _selectedProfile,
  activeSubTab,
  onSubTabChange,
}: { 
  profileId: string; 
  selectedProfile: Profile; 
  activeSubTab?: SubTabType;
  onSubTabChange?: (subTab: SubTabType) => void;
}) {
  const [internalSubTab, setInternalSubTab] = useState<SubTabType>("f4f");
  const subTab = activeSubTab || internalSubTab;

  const handleSelectSubTab = (t: SubTabType) => {
    setInternalSubTab(t);
    onSubTabChange?.(t);
  };

  const { targetKols } = usePersona(profileId);

  const tabs: { id: SubTabType; label: string; icon: any; color: string; badge?: string }[] = [
    { id: "f4f", label: "Blue Tick Radar", icon: BadgeCheck, color: "text-blue-500", badge: "500 Goal" },
    { id: "sniper", label: "KOL Sniper", icon: Crosshair, color: "text-rose-500", badge: `${targetKols.length} KOLs` },
    { id: "hooks", label: "Viral Hooks", icon: Sparkles, color: "text-indigo-500", badge: "Scoring" },
    { id: "threads", label: "Thread Gen", icon: Layers, color: "text-purple-500", badge: "3-Tier" },
    { id: "polls", label: "Polls", icon: Vote, color: "text-emerald-500", badge: "Native" },
    { id: "trends", label: "Trend Radar", icon: TrendingUp, color: "text-sky-500", badge: "Live RSS" },
  ];

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:h-[calc(100vh-120px)] items-start">
      {/* Left Nav Pane / Mobile Horizontal Scroller */}
      <div className="w-full lg:w-64 flex-shrink-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-1.5 sm:p-2 flex lg:flex-col gap-1.5 overflow-x-auto no-scrollbar scroll-smooth">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = subTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => handleSelectSubTab(tab.id)}
              className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3.5 py-2.5 sm:py-2.5 min-h-[44px] rounded-xl text-xs font-semibold transition text-left border active:scale-[0.98] ${
                isActive
                  ? "bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800/80 shadow-xs font-bold"
                  : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <Icon className={`w-4 h-4 flex-shrink-0 ${tab.color}`} />
                <span className="truncate">{tab.label}</span>
              </div>
              {tab.badge && (
                <span className="hidden sm:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Content Pane */}
      <div className="flex-1 w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 sm:p-5 lg:p-6 overflow-y-auto h-full">
        {subTab === "f4f" && <F4FTab profileId={profileId} />}
        {subTab === "sniper" && <SniperTab profileId={profileId} />}
        {subTab === "hooks" && <HooksTab profileId={profileId} />}
        {subTab === "threads" && <ThreadsTab profileId={profileId} />}
        {subTab === "polls" && <PollsTab profileId={profileId} />}
        {subTab === "trends" && <TrendsTab profileId={profileId} />}
      </div>
    </div>
  );
}
