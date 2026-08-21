"use client";

import React, { useState } from "react";
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
  Radio,
  Sun,
  Moon,
  Shield,
  Layers,
  User
} from "lucide-react";
import { Profile, SystemHealth } from "@/lib/api";

export type TabType = "overview" | "growth" | "activity" | "persona" | "limits";

interface SidebarProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  profiles: Profile[];
  selectedProfileId: string | null;
  onSelectProfile: (id: string) => void;
  onAddProfile: () => void;
  systemHealth: SystemHealth | null;
  onOpenSettings: () => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
}

export function Sidebar({
  activeTab,
  setActiveTab,
  profiles,
  selectedProfileId,
  onSelectProfile,
  onAddProfile,
  systemHealth,
  onOpenSettings,
  darkMode,
  onToggleDarkMode,
}: SidebarProps) {
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId);

  const navItems: { id: TabType; label: string; icon: React.ElementType; badge?: string }[] = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "growth", label: "Growth Engine", icon: Zap, badge: "AI" },
    { id: "activity", label: "Live Activity", icon: Activity },
    { id: "persona", label: "Persona & Memory", icon: Brain },
    { id: "limits", label: "Limits & Safety", icon: Sliders },
  ];

  return (
    <aside className="w-72 flex-shrink-0 flex flex-col h-screen border-r border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/80 backdrop-blur-xl transition-colors duration-200 z-30">
      {/* App Branding */}
      <div className="p-5 pb-3 flex items-center justify-between border-b border-slate-100 dark:border-slate-800/60">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 via-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 dark:from-white dark:via-indigo-200 dark:to-white">
                XBot Pro
              </span>
              <span className="text-[10px] uppercase tracking-wider font-extrabold px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/50">
                v2.0
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">Autonomous AI Persona</p>
          </div>
        </div>
      </div>

      {/* Profile Selector Section */}
      <div className="p-4 relative">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2 px-1">
          Active Account
        </div>

        {profiles.length > 0 ? (
          <div className="relative">
            <button
              onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
              className="w-full flex items-center justify-between gap-3 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700/70 bg-slate-50/70 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 transition shadow-sm text-left"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex-shrink-0 flex items-center justify-center border border-slate-300 dark:border-slate-600">
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
                  <div className="font-semibold text-sm truncate text-slate-900 dark:text-slate-100">
                    {selectedProfile?.display_name || "Select Profile"}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 truncate">
                    {selectedProfile?.x_handle ? `@${selectedProfile.x_handle.replace(/^@/, "")}` : "No Handle"}
                  </div>
                </div>
              </div>
              <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform duration-200 flex-shrink-0 ${profileDropdownOpen ? "rotate-180" : ""}`} />
            </button>

            {/* Dropdown Menu */}
            {profileDropdownOpen && (
              <div className="absolute top-full left-0 right-0 mt-2 p-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl z-50 space-y-1">
                {profiles.map((p) => {
                  const isSelected = p.id === selectedProfileId;
                  return (
                    <button
                      key={p.id}
                      onClick={() => {
                        onSelectProfile(p.id);
                        setProfileDropdownOpen(false);
                      }}
                      className={`w-full flex items-center justify-between p-2 rounded-lg text-left text-sm transition ${
                        isSelected
                          ? "bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 font-medium"
                          : "hover:bg-slate-50 dark:hover:bg-slate-800/60 text-slate-700 dark:text-slate-300"
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="w-7 h-7 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex-shrink-0 flex items-center justify-center text-xs font-bold">
                          {p.avatar_url || p.avatar ? (
                            <img src={p.avatar_url || p.avatar} alt="" className="w-full h-full object-cover" />
                          ) : (
                            p.display_name.charAt(0).toUpperCase()
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-xs font-semibold">{p.display_name}</p>
                          <p className="truncate text-[11px] text-slate-400">@{p.x_handle.replace(/^@/, "")}</p>
                        </div>
                      </div>
                      {isSelected && <Check className="w-4 h-4 text-indigo-500 flex-shrink-0 ml-2" />}
                    </button>
                  );
                })}

                <div className="pt-1 mt-1 border-t border-slate-100 dark:border-slate-800">
                  <button
                    onClick={() => {
                      setProfileDropdownOpen(false);
                      onAddProfile();
                    }}
                    className="w-full flex items-center gap-2 p-2 rounded-lg text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50/50 dark:hover:bg-indigo-950/30 transition"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Connect New Account</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={onAddProfile}
            className="w-full flex items-center justify-center gap-2 p-3 rounded-xl border border-dashed border-indigo-300 dark:border-indigo-700 bg-indigo-50/50 dark:bg-indigo-950/20 text-indigo-600 dark:text-indigo-400 text-xs font-semibold hover:bg-indigo-100/50 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Connect X Account</span>
          </button>
        )}
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 space-y-1.5 overflow-y-auto">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2 px-2">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all group ${
                isActive
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/25"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100/80 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-slate-200"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 transition-transform group-hover:scale-110 ${isActive ? "text-white" : "text-slate-400 dark:text-slate-500 group-hover:text-indigo-500"}`} />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                    isActive
                      ? "bg-white/20 text-white"
                      : "bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400"
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Health & System Settings */}
      <div className="p-3 border-t border-slate-200 dark:border-slate-800/80 space-y-2 bg-slate-50/50 dark:bg-slate-900/40">
        {/* Health status pill */}
        <div className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800/60 text-xs">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${systemHealth?.status === "healthy" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
            <span className="text-slate-600 dark:text-slate-400 font-medium">
              {systemHealth?.status === "healthy" ? "Backend Healthy" : "Offline / Check API"}
            </span>
          </div>
          <span className="text-[10px] font-semibold text-slate-400">Port 8200</span>
        </div>

        {/* Global Settings & Theme Toggle */}
        <div className="flex items-center gap-2">
          <button
            onClick={onOpenSettings}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-200/70 dark:hover:bg-slate-800 transition border border-slate-200 dark:border-slate-700/60"
          >
            <Settings className="w-3.5 h-3.5 text-slate-400" />
            <span>AI & Global Settings</span>
          </button>

          <button
            onClick={onToggleDarkMode}
            title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            className="p-2 rounded-xl text-slate-500 dark:text-slate-400 hover:bg-slate-200/70 dark:hover:bg-slate-800 transition border border-slate-200 dark:border-slate-700/60"
          >
            {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
          </button>
        </div>
      </div>
    </aside>
  );
}
