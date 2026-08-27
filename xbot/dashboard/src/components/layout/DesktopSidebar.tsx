"use client";

import React, { useState } from "react";
import { useAppStore } from "@/store/useAppStore";
import { TabType } from "@/store/useAppStore";
import {
  LayoutDashboard,
  Zap,
  Activity,
  Brain,
  Sliders,
  Settings,
  Plus,
  ChevronDown,
  Check,
  Sun,
  Moon,
  Layers,
  User,
  Sparkles,
  Terminal,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { cn } from "@/lib/utils/cn";

export function DesktopSidebar() {
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);

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

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId);

  const navItems: { id: TabType; label: string; icon: React.ElementType; badge?: string; shortcut: string }[] = [
    { id: "overview", label: "Dashboard", icon: LayoutDashboard, shortcut: "⌘1" },
    { id: "campaigns", label: "Content Studio", icon: Sparkles, badge: "AI", shortcut: "⌘2" },
    { id: "growth", label: "Audience & Growth", icon: Zap, badge: "AI", shortcut: "⌘3" },
    { id: "activity", label: "Live Activity", icon: Activity, shortcut: "⌘4" },
    { id: "persona", label: "Persona & Knowledge", icon: Brain, shortcut: "⌘5" },
    { id: "limits", label: "System & Safety", icon: Sliders, shortcut: "⌘6" },
  ];

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
      <div className={cn("relative", sidebarCollapsed ? "p-2 flex justify-center" : "p-3")}>
        {!sidebarCollapsed && (
          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-1.5 px-1">
            Active Workspace
          </div>
        )}

        {profiles.length > 0 ? (
          <div className="relative w-full flex justify-center">
            <button
              onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
              title={
                sidebarCollapsed
                  ? `${selectedProfile?.display_name || "Workspace"} (@${selectedProfile?.x_handle?.replace(/^@/, "") || ""})`
                  : undefined
              }
              className={cn(
                "rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/80 transition text-left flex items-center",
                sidebarCollapsed
                  ? "w-10 h-10 justify-center p-0"
                  : "w-full justify-between gap-2.5 p-2"
              )}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-7 h-7 rounded-md bg-slate-100 dark:bg-slate-800 overflow-hidden flex-shrink-0 flex items-center justify-center border border-slate-200 dark:border-slate-700">
                  {selectedProfile?.avatar_url || selectedProfile?.avatar ? (
                    <img
                      src={selectedProfile.avatar_url || selectedProfile.avatar}
                      alt={selectedProfile.display_name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <User className="w-4 h-4 text-slate-400" />
                  )}
                </div>
                {!sidebarCollapsed && (
                  <div className="min-w-0">
                    <div className="font-semibold text-xs truncate text-slate-900 dark:text-slate-100">
                      {selectedProfile?.display_name || "Select Profile"}
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                      {selectedProfile?.x_handle ? `@${selectedProfile.x_handle.replace(/^@/, "")}` : "No Handle"}
                    </div>
                  </div>
                )}
              </div>
              {!sidebarCollapsed && (
                <ChevronDown
                  className={cn(
                    "w-3.5 h-3.5 text-slate-400 transition-transform duration-200 flex-shrink-0",
                    profileDropdownOpen && "rotate-180"
                  )}
                />
              )}
            </button>

            {/* Dropdown Menu (Flyout in compact mode, Accordion in full mode) */}
            {profileDropdownOpen && (
              <div
                className={cn(
                  "p-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-xl z-50 space-y-1",
                  sidebarCollapsed
                    ? "absolute left-full top-0 ml-2 w-56"
                    : "absolute top-full left-0 right-0 mt-1"
                )}
              >
                {profiles.map((p) => {
                  const isSelected = p.id === selectedProfileId;
                  return (
                    <button
                      key={p.id}
                      onClick={() => {
                        setSelectedProfileId(p.id);
                        setProfileDropdownOpen(false);
                      }}
                      className={cn(
                        "w-full flex items-center justify-between p-2 rounded-md text-left text-xs transition",
                        isSelected
                          ? "bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 font-semibold"
                          : "hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-6 h-6 rounded-md bg-slate-100 dark:bg-slate-800 overflow-hidden flex-shrink-0 flex items-center justify-center text-[10px] font-medium">
                          {p.avatar_url || p.avatar ? (
                            <img src={p.avatar_url || p.avatar} alt="" className="w-full h-full object-cover" />
                          ) : (
                            p.display_name.charAt(0).toUpperCase()
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate font-medium">{p.display_name}</p>
                          <p className="truncate text-[10px] text-slate-400">@{p.x_handle.replace(/^@/, "")}</p>
                        </div>
                      </div>
                      {isSelected && <Check className="w-3.5 h-3.5 text-blue-500 flex-shrink-0 ml-1.5" />}
                    </button>
                  );
                })}

                <div className="pt-1 mt-1 border-t border-slate-100 dark:border-slate-800">
                  <button
                    onClick={() => {
                      setProfileDropdownOpen(false);
                      setModals({ connect: true });
                    }}
                    className="w-full flex items-center gap-2 p-1.5 rounded-md text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Connect Account</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={() => setModals({ connect: true })}
            title="Connect X Account"
            className={cn(
              "rounded-lg border border-dashed border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-medium transition flex items-center justify-center",
              sidebarCollapsed ? "w-10 h-10 p-0" : "w-full gap-2 p-2.5"
            )}
          >
            <Plus className="w-4 h-4" />
            {!sidebarCollapsed && <span>Connect Account</span>}
          </button>
        )}
      </div>

      {/* Navigation Links */}
      <nav className={cn("flex-1 space-y-1 overflow-y-auto", sidebarCollapsed ? "px-2 py-2" : "px-2.5 py-1")}>
        {!sidebarCollapsed && (
          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-1 px-2 mt-1">
            Navigation
          </div>
        )}
        {navItems.map((item) => {
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

      {/* Bottom Settings & Status */}
      <div className={cn("border-t border-slate-200 dark:border-slate-800", sidebarCollapsed ? "p-2 space-y-2 flex flex-col items-center" : "p-3 space-y-2")}>
        {!sidebarCollapsed ? (
          <>
            <div className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "w-2 h-2 rounded-full",
                    systemHealth?.status === "healthy" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
                  )}
                />
                <span className="text-slate-700 dark:text-slate-300 font-medium text-[11px]">
                  {systemHealth?.status === "healthy" ? "API Online" : "API Offline"}
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
                onClick={() => setModals({ settings: true })}
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
              title={systemHealth?.status === "healthy" ? "API Online" : "API Offline"}
              className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-center"
            >
              <span
                className={cn(
                  "w-2.5 h-2.5 rounded-full",
                  systemHealth?.status === "healthy" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
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
              onClick={() => setModals({ settings: true })}
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
    </aside>
  );
}
