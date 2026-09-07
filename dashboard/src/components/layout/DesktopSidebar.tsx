"use client";

import React from "react";
import { useAppStore } from "@/store/useAppStore";
import { Layers, PanelLeftClose } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { ProfileSwitcher } from "./ProfileSwitcher";
import { SidebarNav } from "./SidebarNav";
import { SidebarFooter } from "./SidebarFooter";

export function DesktopSidebar() {
  const {
    profiles,
    selectedProfileId,
    setSelectedProfileId,
    activeTab,
    setActiveTab,
    systemHealth,
    darkMode,
    setDarkMode,
    setModals,
    isConsoleOpen,
    setConsoleOpen,
    sidebarCollapsed,
    toggleSidebarCollapsed,
  } = useAppStore();

  return (
    <aside
      className={cn(
        "hidden lg:flex flex-shrink-0 flex-col h-screen border-r border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 transition-all duration-200 z-30 select-none",
        sidebarCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* App Branding */}
      <div
        className={cn(
          "p-4 flex items-center border-b border-slate-200/60 dark:border-slate-800/60",
          sidebarCollapsed ? "justify-center" : "justify-between"
        )}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div
            onClick={toggleSidebarCollapsed}
            title="XBot Pro v2.0 - Click to toggle rail"
            className="w-9 h-9 rounded-xl bg-blue-600 hover:bg-blue-700 flex items-center justify-center flex-shrink-0 shadow-sm cursor-pointer transition"
          >
            <Layers className="w-5 h-5 text-white" />
          </div>
          {!sidebarCollapsed && (
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-base tracking-tight text-slate-900 dark:text-slate-50 truncate">
                  XBot Pro
                </span>
                <span className="text-[9px] uppercase tracking-wider font-extrabold px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                  v2.0
                </span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">Autonomous SaaS</p>
            </div>
          )}
        </div>

        {!sidebarCollapsed && (
          <button
            onClick={toggleSidebarCollapsed}
            title="Collapse sidebar into compact rail"
            className="p-1 rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 transition"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Profile Selector Section */}
      <ProfileSwitcher
        profiles={profiles}
        selectedProfileId={selectedProfileId}
        setSelectedProfileId={setSelectedProfileId}
        sidebarCollapsed={sidebarCollapsed}
        onOpenConnectModal={() => setModals({ connect: true })}
      />

      {/* Navigation Links */}
      <SidebarNav
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        sidebarCollapsed={sidebarCollapsed}
      />

      {/* Bottom Settings & Status */}
      <SidebarFooter
        sidebarCollapsed={sidebarCollapsed}
        toggleSidebarCollapsed={toggleSidebarCollapsed}
        systemHealth={systemHealth}
        isConsoleOpen={isConsoleOpen}
        setConsoleOpen={setConsoleOpen}
        darkMode={darkMode}
        setDarkMode={setDarkMode}
        onOpenSettingsModal={() => setModals({ settings: true })}
      />
    </aside>
  );
}
