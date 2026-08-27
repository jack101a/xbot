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
  } = useAppStore();

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId);

  const navItems: { id: TabType; label: string; icon: React.ElementType; badge?: string }[] = [
    { id: "overview", label: "Dashboard", icon: LayoutDashboard },
    { id: "campaigns", label: "Content Studio", icon: Sparkles, badge: "AI" },
    { id: "growth", label: "Audience & Growth", icon: Zap, badge: "AI" },
    { id: "activity", label: "Live Activity", icon: Activity },
    { id: "persona", label: "Persona & Knowledge", icon: Brain },
    { id: "limits", label: "System & Safety", icon: Sliders },
  ];

  return (
    <aside className="hidden lg:flex w-72 flex-shrink-0 flex-col h-screen border-r border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 transition-colors duration-200 z-30">
      {/* App Branding */}
      <div className="p-5 pb-3 flex items-center justify-between border-b border-slate-200/60 dark:border-slate-800/60">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-lg tracking-tight text-slate-900 dark:text-slate-50">
                XBot Pro
              </span>
              <span className="text-[10px] uppercase tracking-wider font-extrabold px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                v2.0
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">Autonomous SaaS</p>
          </div>
        </div>
      </div>

      {/* Profile Selector Section */}
      <div className="p-4 relative">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2 px-1">
          Active Workspace
        </div>

        {profiles.length > 0 ? (
          <div className="relative">
            <button
              onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
              className="w-full flex items-center justify-between gap-3 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/80 transition text-left"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-md bg-slate-100 dark:bg-slate-800 overflow-hidden flex-shrink-0 flex items-center justify-center border border-slate-200 dark:border-slate-700">
                  {selectedProfile?.avatar_url || selectedProfile?.avatar ? (
                    <img
                      src={selectedProfile.avatar_url || selectedProfile.avatar}
                      alt={selectedProfile.display_name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <User className="w-5 h-5 text-slate-400" />
                  )}
                </div>
                <div className="min-w-0">
                  <div className="font-medium text-sm truncate text-slate-900 dark:text-slate-100">
                    {selectedProfile?.display_name || "Select Profile"}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 truncate">
                    {selectedProfile?.x_handle ? `@${selectedProfile.x_handle.replace(/^@/, "")}` : "No Handle"}
                  </div>
                </div>
              </div>
              <ChevronDown className={cn("w-4 h-4 text-slate-400 transition-transform duration-200 flex-shrink-0", profileDropdownOpen && "rotate-180")} />
            </button>

            {/* Dropdown Menu */}
            {profileDropdownOpen && (
              <div className="absolute top-full left-0 right-0 mt-1 p-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-md z-50 space-y-1">
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
                        "w-full flex items-center justify-between p-2 rounded-md text-left text-sm transition",
                        isSelected
                          ? "bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 font-medium"
                          : "hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
                      )}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="w-7 h-7 rounded-md bg-slate-100 dark:bg-slate-800 overflow-hidden flex-shrink-0 flex items-center justify-center text-xs font-medium">
                          {p.avatar_url || p.avatar ? (
                            <img src={p.avatar_url || p.avatar} alt="" className="w-full h-full object-cover" />
                          ) : (
                            p.display_name.charAt(0).toUpperCase()
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-xs font-medium">{p.display_name}</p>
                          <p className="truncate text-[11px] text-slate-400">@{p.x_handle.replace(/^@/, "")}</p>
                        </div>
                      </div>
                      {isSelected && <Check className="w-4 h-4 text-blue-500 flex-shrink-0 ml-2" />}
                    </button>
                  );
                })}

                <div className="pt-1 mt-1 border-t border-slate-100 dark:border-slate-800">
                  <button
                    onClick={() => {
                      setProfileDropdownOpen(false);
                      setModals({ connect: true });
                    }}
                    className="w-full flex items-center gap-2 p-2 rounded-md text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Connect Account</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={() => setModals({ connect: true })}
            className="w-full flex items-center justify-center gap-2 p-3 rounded-lg border border-dashed border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-sm font-medium transition"
          >
            <Plus className="w-4 h-4" />
            <span>Connect X Account</span>
          </button>
        )}
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2 px-2 mt-2">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={cn(
                "w-full flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-slate-200 dark:bg-slate-800 text-slate-900 dark:text-slate-50"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200"
              )}
            >
              <div className="flex items-center gap-3">
                <Icon className={cn("w-4 h-4", isActive ? "text-slate-900 dark:text-slate-50" : "text-slate-400")} />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Settings */}
      <div className="p-3 border-t border-slate-200 dark:border-slate-800 space-y-2">
        <div className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs">
          <div className="flex items-center gap-2">
            <span className={cn("w-2 h-2 rounded-full", systemHealth?.status === "healthy" ? "bg-emerald-500" : "bg-rose-500")} />
            <span className="text-slate-700 dark:text-slate-300 font-medium">
              {systemHealth?.status === "healthy" ? "API Online" : "API Offline"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setConsoleOpen(!isConsoleOpen)}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 transition border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Console</span>
          </button>

          <button
            onClick={() => setModals({ settings: true })}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 transition border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
          >
            <Settings className="w-3.5 h-3.5" />
            <span>Settings</span>
          </button>

          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 rounded-md text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 transition border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </aside>
  );
}
