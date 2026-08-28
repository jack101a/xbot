"use client";

import React from "react";
import { useAppStore, TabType } from "@/store/useAppStore";
import { LayoutDashboard, Sparkles, Zap, Menu, X, Activity, Brain, Sliders, Settings, Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils/cn";

export function MobileNavigation() {
  const { activeTab, setActiveTab, mobileMenuOpen, setModals, darkMode, setDarkMode } = useAppStore();

  const primaryTabs: { id: TabType | "menu"; label: string; icon: any; isLive?: boolean }[] = [
    { id: "overview", label: "Home", icon: LayoutDashboard },
    { id: "campaigns", label: "Studio", icon: Sparkles },
    { id: "activity", label: "Activity", icon: Activity, isLive: true },
    { id: "growth", label: "Growth", icon: Zap },
    { id: "menu", label: "Menu", icon: Menu },
  ];

  const secondaryTabs: { id: TabType; label: string; icon: any }[] = [
    { id: "persona", label: "Persona & Knowledge", icon: Brain },
    { id: "limits", label: "System & Safety", icon: Sliders },
  ];

  return (
    <>
      <div className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 pb-safe">
        <div className="flex items-center justify-around p-1.5 px-2">
          {primaryTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = tab.id === "menu" ? mobileMenuOpen : activeTab === tab.id && !mobileMenuOpen;
            return (
              <button
                key={tab.id}
                onClick={() => tab.id === "menu" ? setModals({ mobileMenu: true }) : setActiveTab(tab.id as TabType)}
                className={cn(
                  "flex flex-col items-center justify-center flex-1 py-1 gap-1 rounded-lg transition relative min-w-0",
                  isActive ? "text-blue-600 dark:text-blue-400 font-semibold" : "text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800"
                )}
              >
                <div className="relative">
                  <Icon className={cn("w-5 h-5", isActive && "fill-blue-600/20")} />
                  {tab.isLive && (
                    <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                  )}
                </div>
                <span className="text-[10px] truncate max-w-full">{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Menu Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex flex-col justify-end">
          <div className="absolute inset-0 bg-slate-900/50 " onClick={() => setModals({ mobileMenu: false })} />
          <div className="relative bg-white dark:bg-slate-900 rounded-t-2xl max-h-[85vh] flex flex-col pb-safe animate-fade-in-up">
            <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800">
              <span className="font-semibold text-slate-900 dark:text-slate-50">More Options</span>
              <button onClick={() => setModals({ mobileMenu: false })} className="p-2 rounded-full bg-slate-100 dark:bg-slate-800">
                <X className="w-5 h-5 text-slate-600 dark:text-slate-400" />
              </button>
            </div>
            
            <div className="p-2 overflow-y-auto space-y-1">
              {secondaryTabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      "w-full flex items-center gap-3 p-3 rounded-lg font-medium",
                      isActive ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-50" : "text-slate-600 dark:text-slate-400"
                    )}
                  >
                    <Icon className="w-5 h-5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            <div className="p-4 border-t border-slate-200 dark:border-slate-800 grid grid-cols-2 gap-2">
              <button
                onClick={() => { setModals({ mobileMenu: false, settings: true }); }}
                className="flex items-center justify-center gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-700 font-medium text-sm"
              >
                <Settings className="w-4 h-4" /> Settings
              </button>
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="flex items-center justify-center gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-700 font-medium text-sm"
              >
                {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />} Theme
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
