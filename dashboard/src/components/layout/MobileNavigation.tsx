"use client";

import React from "react";
import { useAppStore, TabType } from "@/store/useAppStore";
import {
  LayoutDashboard,
  Sparkles,
  Zap,
  Menu,
  X,
  Activity,
  Brain,
  Sliders,
  Settings,
  Sun,
  Moon,
  Trash2,
  BotMessageSquare,
  Terminal,
  Command,
  ChevronRight,
  RotateCcw,
} from "lucide-react";
import { cn } from "@/lib/utils/cn";

export function MobileNavigation() {
  const {
    activeTab,
    setActiveTab,
    mobileMenuOpen,
    setModals,
    darkMode,
    setDarkMode,
    setCommandPaletteOpen,
    isConsoleOpen,
    setConsoleOpen,
    loadInitialData,
  } = useAppStore();

  const primaryTabs: { id: TabType | "menu"; label: string; icon: any; isLive?: boolean }[] = [
    { id: "overview", label: "Home", icon: LayoutDashboard },
    { id: "campaigns", label: "Studio", icon: Sparkles },
    { id: "activity", label: "Live", icon: Activity, isLive: true },
    { id: "growth", label: "Growth", icon: Zap },
    { id: "menu", label: "Menu", icon: Menu },
  ];

  const automationModules: { id: TabType; label: string; description: string; icon: any; color: string }[] = [
    {
      id: "persona",
      label: "Persona & Worldview",
      description: "Entity stances, Hinglish dialect & diary logs",
      icon: Brain,
      color: "text-sky-500 bg-sky-50 dark:bg-sky-950/60",
    },
    {
      id: "limits",
      label: "Limits & Anti-Ban Safety",
      description: "Jitter delays, circadian schedule & hourly caps",
      icon: Sliders,
      color: "text-indigo-500 bg-indigo-50 dark:bg-indigo-950/60",
    },
    {
      id: "pruner",
      label: "Profile Post Pruner",
      description: "Clean up underperforming tweets with grace periods",
      icon: Trash2,
      color: "text-rose-500 bg-rose-50 dark:bg-rose-950/60",
    },
    {
      id: "ai-logs",
      label: "AI Prompt Audit Logs",
      description: "Real-time inspection of prompts and completions",
      icon: BotMessageSquare,
      color: "text-purple-500 bg-purple-50 dark:bg-purple-950/60",
    },
  ];

  const handleTabClick = (tabId: TabType | "menu") => {
    if (tabId === "menu") {
      setModals({ mobileMenu: !mobileMenuOpen });
    } else {
      setActiveTab(tabId);
    }
  };

  return (
    <>
      {/* Primary Fixed Bottom Navigation Bar */}
      <nav 
        role="navigation"
        aria-label="Mobile Navigation"
        className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 dark:bg-slate-950/95 backdrop-blur-xl border-t border-slate-200/80 dark:border-slate-800/80 pb-safe shadow-lg"
      >
        <div className="flex items-center justify-around px-2 py-1">
          {primaryTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive =
              tab.id === "menu" ? mobileMenuOpen : activeTab === tab.id && !mobileMenuOpen;

            return (
              <button
                key={tab.id}
                onClick={() => handleTabClick(tab.id)}
                className={cn(
                  "flex flex-col items-center justify-center flex-1 py-1.5 px-1 min-h-[52px] rounded-2xl transition-all relative min-w-0 active:scale-90",
                  isActive
                    ? "text-blue-600 dark:text-sky-400 font-bold bg-blue-50/80 dark:bg-blue-950/60"
                    : "text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                )}
                aria-current={isActive ? "page" : undefined}
                aria-label={tab.label}
              >
                <div className="relative flex items-center justify-center mb-0.5">
                  <Icon
                    className={cn(
                      "w-5 h-5 transition-transform",
                      isActive ? "scale-105 stroke-[2.5]" : "stroke-[1.75]"
                    )}
                  />
                  {tab.isLive && (
                    <span className="absolute -top-1 -right-1.5 flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                    </span>
                  )}
                </div>
                <span className="text-[10px] tracking-tight leading-none truncate max-w-full">
                  {tab.label}
                </span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Modern Slide-Up Menu Drawer (Bottom Sheet) */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex flex-col justify-end animate-in fade-in duration-150">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-slate-950/60 backdrop-blur-xs"
            onClick={() => setModals({ mobileMenu: false })}
          />

          {/* Drawer Container */}
          <div className="relative bg-white dark:bg-slate-900 rounded-t-3xl max-h-[85dvh] flex flex-col pb-safe border-t border-slate-200 dark:border-slate-800 shadow-2xl animate-in slide-in-from-bottom duration-200">
            {/* Grab Handle */}
            <div className="w-12 h-1.5 bg-slate-300 dark:bg-slate-700 rounded-full mx-auto my-3 shrink-0" />

            {/* Drawer Header */}
            <div className="flex items-center justify-between px-5 pb-3 border-b border-slate-200 dark:border-slate-800">
              <div>
                <span className="font-bold text-base text-slate-900 dark:text-slate-50">
                  Workspace Modules & Tools
                </span>
                <p className="text-xs text-slate-500">Autonomous capabilities & developer console</p>
              </div>
              <button
                onClick={() => setModals({ mobileMenu: false })}
                className="p-2 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 active:scale-90 transition"
                aria-label="Close menu"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Content */}
            <div className="p-3 overflow-y-auto space-y-4 max-h-[58dvh]">
              {/* Automation Modules */}
              <div className="space-y-1.5">
                <div className="px-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  Automation & Growth
                </div>
                {automationModules.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        setActiveTab(item.id);
                        setModals({ mobileMenu: false });
                      }}
                      className={cn(
                        "w-full flex items-center justify-between p-3 min-h-[54px] rounded-2xl border text-left transition active:scale-[0.98]",
                        isActive
                          ? "bg-blue-50 dark:bg-blue-950/50 border-blue-200 dark:border-blue-800/80 text-blue-700 dark:text-sky-300 shadow-xs"
                          : "border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 text-slate-700 dark:text-slate-200"
                      )}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className={cn(
                            "w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0",
                            item.color
                          )}
                        >
                          <Icon className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-xs truncate">{item.label}</p>
                          <p className="text-[11px] text-slate-400 truncate">{item.description}</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
                    </button>
                  );
                })}
              </div>

              {/* Developer & Diagnostic Tools */}
              <div className="space-y-1.5">
                <div className="px-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  Quick Utilities
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => {
                      setModals({ mobileMenu: false });
                      setCommandPaletteOpen(true);
                    }}
                    className="flex items-center gap-2.5 p-3 min-h-[48px] rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-left text-xs font-semibold text-slate-700 dark:text-slate-200 active:scale-95 transition"
                  >
                    <Command className="w-4 h-4 text-blue-500 shrink-0" />
                    <span className="truncate">Command Palette</span>
                  </button>

                  <button
                    onClick={() => {
                      setModals({ mobileMenu: false });
                      setConsoleOpen(!isConsoleOpen);
                    }}
                    className="flex items-center gap-2.5 p-3 min-h-[48px] rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-left text-xs font-semibold text-slate-700 dark:text-slate-200 active:scale-95 transition"
                  >
                    <Terminal className="w-4 h-4 text-emerald-500 shrink-0" />
                    <span className="truncate">Activity Console</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Bottom Utility Grid */}
            <div className="p-3 border-t border-slate-200 dark:border-slate-800 grid grid-cols-3 gap-2">
              <button
                onClick={() => {
                  setModals({ mobileMenu: false, settings: true });
                }}
                className="flex flex-col items-center justify-center gap-1 p-2 min-h-[48px] rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 font-semibold text-xs text-slate-700 dark:text-slate-200 active:scale-95 transition"
              >
                <Settings className="w-4 h-4 text-indigo-500" />
                <span className="text-[10px]">Settings</span>
              </button>

              <button
                onClick={() => setDarkMode(!darkMode)}
                className="flex flex-col items-center justify-center gap-1 p-2 min-h-[48px] rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 font-semibold text-xs text-slate-700 dark:text-slate-200 active:scale-95 transition"
              >
                {darkMode ? (
                  <Sun className="w-4 h-4 text-amber-400" />
                ) : (
                  <Moon className="w-4 h-4 text-slate-600" />
                )}
                <span className="text-[10px]">{darkMode ? "Light" : "Dark"}</span>
              </button>

              <button
                onClick={async () => {
                  setModals({ mobileMenu: false });
                  await loadInitialData();
                }}
                className="flex flex-col items-center justify-center gap-1 p-2 min-h-[48px] rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 font-semibold text-xs text-slate-700 dark:text-slate-200 active:scale-95 transition"
              >
                <RotateCcw className="w-4 h-4 text-blue-500" />
                <span className="text-[10px]">Refresh</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
