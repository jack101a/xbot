"use client";

import React from "react";
import { useAppStore } from "@/store/useAppStore";
import {
  Search,
  Terminal,
  User,
  Activity,
  Sparkles,
  Zap,
  Brain,
  Sliders,
  LayoutDashboard,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { cn } from "@/lib/utils/cn";

export function DesktopTopBar() {
  const {
    profiles,
    selectedProfileId,
    activeTab,
    systemHealth,
    isConsoleOpen,
    setConsoleOpen,
    setCommandPaletteOpen,
    sidebarCollapsed,
    toggleSidebarCollapsed,
    setModals,
  } = useAppStore();

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId);

  const tabLabels: Record<string, { label: string; icon: React.ElementType; shortcut: string }> = {
    overview: { label: "Dashboard", icon: LayoutDashboard, shortcut: "⌘1" },
    campaigns: { label: "Content Studio", icon: Sparkles, shortcut: "⌘2" },
    growth: { label: "Audience & Growth", icon: Zap, shortcut: "⌘3" },
    activity: { label: "Live Activity", icon: Activity, shortcut: "⌘4" },
    persona: { label: "Persona & Knowledge", icon: Brain, shortcut: "⌘5" },
    limits: { label: "System & Safety", icon: Sliders, shortcut: "⌘6" },
  };

  const currentTab = tabLabels[activeTab] || tabLabels.overview;
  const CurrentIcon = currentTab.icon;

  return (
    <header className="hidden lg:flex items-center justify-between px-6 py-2.5 bg-white/75 dark:bg-slate-950/75 backdrop-blur-md border-b border-slate-200/80 dark:border-slate-800/80 sticky top-0 z-20 transition-colors duration-200">
      {/* Left Context: Sidebar Toggle & Active Workspace Context & Tab Breadcrumb */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={toggleSidebarCollapsed}
          title={sidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar (Compact Rail)"}
          className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
        >
          {sidebarCollapsed ? (
            <PanelLeftOpen className="w-4 h-4" />
          ) : (
            <PanelLeftClose className="w-4 h-4" />
          )}
        </button>

        {/* Profile Pill */}
        {selectedProfile ? (
          <button
            onClick={() => setModals({ settings: true })}
            title="Workspace Settings"
            className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-slate-100/80 dark:bg-slate-900/80 hover:bg-slate-200/70 dark:hover:bg-slate-800/70 border border-slate-200/60 dark:border-slate-800/60 text-xs font-medium text-slate-700 dark:text-slate-300 transition min-w-0"
          >
            <div className="w-5 h-5 rounded-md bg-slate-200 dark:bg-slate-800 overflow-hidden flex-shrink-0 flex items-center justify-center">
              {selectedProfile.avatar_url || selectedProfile.avatar ? (
                <img
                  src={selectedProfile.avatar_url || selectedProfile.avatar}
                  alt={selectedProfile.display_name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <User className="w-3 h-3 text-slate-400" />
              )}
            </div>
            <span className="font-semibold text-slate-900 dark:text-slate-100 truncate max-w-[120px]">
              {selectedProfile.display_name}
            </span>
            <span className="text-[11px] text-slate-400 font-normal truncate hidden xl:inline">
              @{selectedProfile.x_handle.replace(/^@/, "")}
            </span>
          </button>
        ) : null}

        <ChevronRight className="w-3.5 h-3.5 text-slate-300 dark:text-slate-700 flex-shrink-0" />

        {/* Active Tab Breadcrumb */}
        <div className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-400">
          <CurrentIcon className="w-3.5 h-3.5 text-blue-500" />
          <span className="text-slate-900 dark:text-slate-100 font-semibold">{currentTab.label}</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800/80 text-slate-500 dark:text-slate-400 border border-slate-200/50 dark:border-slate-700/50">
            {currentTab.shortcut}
          </span>
        </div>
      </div>

      {/* Right Controls: Command Palette hint, Console toggle, API Status */}
      <div className="flex items-center gap-2.5">
        {/* Command Palette Button / Hint */}
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100/90 dark:bg-slate-900/90 hover:bg-slate-200/80 dark:hover:bg-slate-800/80 border border-slate-200/80 dark:border-slate-800/80 text-xs text-slate-600 dark:text-slate-300 transition group"
        >
          <Search className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-500 transition-colors" />
          <span className="hidden sm:inline font-medium">Command Palette</span>
          <kbd className="font-mono text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
            ⌘K
          </kbd>
        </button>

        {/* Activity Console Toggle Button */}
        <button
          onClick={() => setConsoleOpen(!isConsoleOpen)}
          className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition",
            isConsoleOpen
              ? "bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800"
              : "bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border-slate-200 dark:border-slate-800"
          )}
          title="Toggle Activity Console (⌘\)"
        >
          <Terminal className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Console</span>
          <kbd className="font-mono text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
            ⌘\
          </kbd>
        </button>

        {/* API Health Indicator */}
        <div
          className={cn(
            "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border",
            systemHealth?.status === "healthy"
              ? "bg-emerald-50/60 dark:bg-emerald-950/20 text-emerald-700 dark:text-emerald-400 border-emerald-200/60 dark:border-emerald-900/40"
              : "bg-rose-50/60 dark:bg-rose-950/20 text-rose-700 dark:text-rose-400 border-rose-200/60 dark:border-rose-900/40"
          )}
        >
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              systemHealth?.status === "healthy" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
            )}
          />
          <span className="hidden sm:inline">
            {systemHealth?.status === "healthy" ? "API Online" : "API Offline"}
          </span>
        </div>
      </div>
    </header>
  );
}
