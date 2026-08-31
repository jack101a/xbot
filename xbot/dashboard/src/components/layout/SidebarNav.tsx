"use client";

import React from "react";
import {
  LayoutDashboard,
  Zap,
  Activity,
  Brain,
  Sliders,
  Sparkles,
  Trash2,
  BotMessageSquare,
} from "lucide-react";
import { TabType } from "@/store/useAppStore";
import { cn } from "@/lib/utils/cn";

interface SidebarNavProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  sidebarCollapsed: boolean;
}

interface NavItemDef {
  id: TabType;
  label: string;
  icon: React.ElementType;
  badge?: string;
  shortcut: string;
}

const NAV_ITEMS: NavItemDef[] = [
  { id: "overview", label: "Dashboard", icon: LayoutDashboard, shortcut: "⌘1" },
  { id: "campaigns", label: "Content Studio", icon: Sparkles, badge: "AI", shortcut: "⌘2" },
  { id: "growth", label: "Audience & Growth", icon: Zap, badge: "AI", shortcut: "⌘3" },
  { id: "activity", label: "Live Activity", icon: Activity, shortcut: "⌘4" },
  { id: "persona", label: "Persona & Knowledge", icon: Brain, shortcut: "⌘5" },
  { id: "ai-logs", label: "AI Prompt Logs", icon: BotMessageSquare, badge: "LIVE", shortcut: "⌘8" },
  { id: "limits", label: "System & Safety", icon: Sliders, shortcut: "⌘6" },
  { id: "pruner", label: "Post Pruner", icon: Trash2, shortcut: "⌘7" },
];

export function SidebarNav({
  activeTab,
  setActiveTab,
  sidebarCollapsed,
}: SidebarNavProps) {
  return (
    <nav className={cn("flex-1 space-y-1 overflow-y-auto", sidebarCollapsed ? "px-2 py-2" : "px-2.5 py-1")}>
      {!sidebarCollapsed && (
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-1 px-2 mt-1">
          Navigation
        </div>
      )}
      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const isActive = activeTab === item.id;
        return (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            title={sidebarCollapsed ? `${item.label} (${item.shortcut})` : undefined}
            className={cn(
              "flex items-center rounded-lg text-xs font-medium transition-all group relative",
              sidebarCollapsed
                ? cn(
                    "w-10 h-10 mx-auto justify-center",
                    isActive
                      ? "bg-blue-600 text-white shadow-sm font-semibold"
                      : "text-slate-600 dark:text-slate-400 hover:bg-slate-200/70 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100"
                  )
                : cn(
                    "w-full justify-between px-2.5 py-2",
                    isActive
                      ? "bg-slate-200/90 dark:bg-slate-800 text-slate-900 dark:text-slate-50 font-semibold shadow-2xs"
                      : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200"
                  )
            )}
          >
            <div className="flex items-center gap-2.5">
              <Icon
                className={cn(
                  "w-4 h-4 flex-shrink-0 transition-transform group-hover:scale-105",
                  sidebarCollapsed && isActive
                    ? "text-white"
                    : isActive
                    ? "text-blue-600 dark:text-blue-400"
                    : "text-slate-400 dark:text-slate-500"
                )}
              />
              {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
            </div>

            {!sidebarCollapsed ? (
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {item.badge && (
                  <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400">
                    {item.badge}
                  </span>
                )}
                <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 opacity-60 group-hover:opacity-100 transition-opacity">
                  {item.shortcut}
                </span>
              </div>
            ) : (
              item.badge && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-blue-500 ring-2 ring-slate-50 dark:ring-slate-950" />
              )
            )}
          </button>
        );
      })}
    </nav>
  );
}
