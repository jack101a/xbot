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
  selectedProfile 
}: { 
  profileId: string; 
  selectedProfile: Profile; 
}) {
  const [subTab, setSubTab] = useState<SubTabType>("f4f");
  const { targetKols } = usePersona(profileId);

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:h-[calc(100vh-120px)] items-start">
      {/* Left Nav Pane */}

      <div className="w-full lg:w-64 flex-shrink-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-2 flex lg:flex-col gap-1 overflow-x-auto lg:overflow-visible">
        <button
          onClick={() => setSubTab("f4f")}
          className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition text-left border ${
            subTab === "f4f"
              ? "bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800/80 shadow-sm font-bold"
              : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <BadgeCheck className="w-4 h-4 text-blue-500 flex-shrink-0" />
            <span className="truncate">Blue Tick F4F Radar</span>
          </div>
          <span className="hidden sm:inline-block lg:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-blue-100/50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400">
            500 Goal
          </span>
        </button>

        <button
          onClick={() => setSubTab("sniper")}
          className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition text-left border ${
            subTab === "sniper"
              ? "bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-800/80 shadow-sm font-bold"
              : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Crosshair className="w-4 h-4 text-rose-500 flex-shrink-0" />
            <span className="truncate">KOL Sniper Engine</span>
          </div>
          <span className="hidden sm:inline-block lg:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-rose-100/50 dark:bg-rose-900/40 text-rose-600 dark:text-rose-400">
            {targetKols.length} KOLs
          </span>
        </button>

        <button
          onClick={() => setSubTab("hooks")}
          className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition text-left border ${
            subTab === "hooks"
              ? "bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 border-indigo-200 dark:border-indigo-800/80 shadow-sm font-bold"
              : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Sparkles className="w-4 h-4 text-indigo-500 flex-shrink-0" />
            <span className="truncate">Viral Hook Optimizer</span>
          </div>
          <span className="hidden sm:inline-block lg:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-100/50 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400">
            Scoring
          </span>
        </button>

        <button
          onClick={() => setSubTab("threads")}
          className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition text-left border ${
            subTab === "threads"
              ? "bg-purple-50 dark:bg-purple-950/50 text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-800/80 shadow-sm font-bold"
              : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Layers className="w-4 h-4 text-purple-500 flex-shrink-0" />
            <span className="truncate">Thread Generator</span>
          </div>
          <span className="hidden sm:inline-block lg:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-100/50 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400">
            3-Tier
          </span>
        </button>

        <button
          onClick={() => setSubTab("polls")}
          className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition text-left border ${
            subTab === "polls"
              ? "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800/80 shadow-sm font-bold"
              : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Vote className="w-4 h-4 text-emerald-500 flex-shrink-0" />
            <span className="truncate">Interactive Polls</span>
          </div>
          <span className="hidden sm:inline-block lg:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-100/50 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400">
            Native
          </span>
        </button>

        <button
          onClick={() => setSubTab("trends")}
          className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition text-left border ${
            subTab === "trends"
              ? "bg-sky-50 dark:bg-sky-950/50 text-sky-600 dark:text-sky-400 border-sky-200 dark:border-sky-800/80 shadow-sm font-bold"
              : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <TrendingUp className="w-4 h-4 text-sky-500 flex-shrink-0" />
            <span className="truncate">Trend Radar</span>
          </div>
          <span className="hidden sm:inline-block lg:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-sky-100/50 dark:bg-sky-900/40 text-sky-600 dark:text-sky-400">
            Live RSS
          </span>
        </button>
      </div>


      {/* Right Content Pane */}
      <div className="flex-1 w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 lg:p-6 overflow-y-auto h-full">
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
