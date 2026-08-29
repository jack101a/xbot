"use client";

import React from "react";
import { Terminal, Settings, Sun, Moon, PanelLeftOpen } from "lucide-react";
import { cn } from "@/lib/utils/cn";

interface SidebarFooterProps {
  sidebarCollapsed: boolean;
  toggleSidebarCollapsed: () => void;
  systemHealth: any;
  isConsoleOpen: boolean;
  setConsoleOpen: (open: boolean) => void;
  darkMode: boolean;
  setDarkMode: (dark: boolean) => void;
  onOpenSettingsModal: () => void;
}

export function SidebarFooter({
  sidebarCollapsed,
  toggleSidebarCollapsed,
  systemHealth,
  isConsoleOpen,
  setConsoleOpen,
  darkMode,
  setDarkMode,
  onOpenSettingsModal,
}: SidebarFooterProps) {
  const isHealthy = systemHealth?.status === "healthy";

  return (
    <div
      className={cn(
        "border-t border-slate-200 dark:border-slate-800",
        sidebarCollapsed
          ? "p-2 space-y-2 flex flex-col items-center"
          : "p-3 space-y-2"
      )}
    >
      {!sidebarCollapsed ? (
        <>
          <div className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "w-2 h-2 rounded-full",
                  isHealthy ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
                )}
              />
              <span className="text-slate-700 dark:text-slate-300 font-medium text-[11px]">
                {isHealthy ? "API Online" : "API Offline"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setConsoleOpen(!isConsoleOpen)}
              title="Toggle Activity Console (⌘\)"
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium transition border",
                isConsoleOpen
                  ? "bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800"
                  : "bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border-slate-200 dark:border-slate-800"
              )}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Console</span>
            </button>

            <button
              onClick={onOpenSettingsModal}
              title="Global Settings"
              className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
            >
              <Settings className="w-3.5 h-3.5" />
              <span>Settings</span>
            </button>

            <button
              onClick={() => setDarkMode(!darkMode)}
              title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
              className="p-1.5 rounded-md text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
            >
              {darkMode ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
            </button>
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center gap-2">
          <div
            title={isHealthy ? "API Online" : "API Offline"}
            className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-center"
          >
            <span
              className={cn(
                "w-2.5 h-2.5 rounded-full",
                isHealthy ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
              )}
            />
          </div>

          <button
            onClick={() => setConsoleOpen(!isConsoleOpen)}
            title="Toggle Console (⌘\)"
            className={cn(
              "p-2 rounded-lg border transition",
              isConsoleOpen
                ? "bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800"
                : "bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border-slate-200 dark:border-slate-800"
            )}
          >
            <Terminal className="w-4 h-4" />
          </button>

          <button
            onClick={onOpenSettingsModal}
            title="Global Settings"
            className="p-2 rounded-lg bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 transition"
          >
            <Settings className="w-4 h-4" />
          </button>

          <button
            onClick={() => setDarkMode(!darkMode)}
            title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            className="p-2 rounded-lg bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 transition"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          <button
            onClick={toggleSidebarCollapsed}
            title="Expand Sidebar"
            className="p-2 rounded-lg bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700 transition"
          >
            <PanelLeftOpen className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
