"use client";

import React, { useState } from "react";
import { useAppStore } from "@/store/useAppStore";
import { Layers, ChevronDown, User, Check, Plus, Sun, Moon, RotateCcw, X } from "lucide-react";
import { cn } from "@/lib/utils/cn";

export function MobileHeader() {
  const { 
    profiles, 
    selectedProfileId, 
    setSelectedProfileId, 
    setModals, 
    darkMode, 
    setDarkMode, 
    loadInitialData,
    loadingProfiles,
    systemHealth 
  } = useAppStore();
  
  const [sheetOpen, setSheetOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const selectedProfile = profiles.find((p) => p.id === selectedProfileId);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadInitialData();
    setTimeout(() => setRefreshing(false), 500);
  };

  const isHealthy = systemHealth?.status === "healthy";

  return (
    <>
      <header className="lg:hidden sticky top-0 z-30 flex items-center justify-between px-4 py-2.5 bg-white/90 dark:bg-slate-950/90 backdrop-blur-xl border-b border-slate-200/80 dark:border-slate-800/80 shadow-xs">
        {/* Left: Brand & Status Indicator */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center shadow-xs text-white">
            <Layers className="w-4 h-4" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-sm text-slate-900 dark:text-white leading-none">XBot Pro</span>
              <span className="flex h-2 w-2 relative">
                <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", isHealthy ? "bg-emerald-400" : "bg-amber-400")} />
                <span className={cn("relative inline-flex rounded-full h-2 w-2", isHealthy ? "bg-emerald-500" : "bg-amber-500")} />
              </span>
            </div>
            <span className="text-[10px] text-slate-400 font-medium">Autonomous Ops</span>
          </div>
        </div>

        {/* Right: Quick Actions & Profile Button */}
        <div className="flex items-center gap-1.5">
          {/* Quick Refresh Button */}
          <button
            onClick={handleRefresh}
            className="p-2 min-h-[40px] min-w-[40px] flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition active:scale-95"
            title="Refresh dashboard"
            aria-label="Refresh data"
          >
            <RotateCcw className={cn("w-4 h-4", (refreshing || loadingProfiles) && "animate-spin text-blue-500")} />
          </button>

          {/* Theme Toggle */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 min-h-[40px] min-w-[40px] flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition active:scale-95"
            title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            aria-label="Toggle Theme"
          >
            {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
          </button>

          {/* Profile Switcher Trigger */}
          <button
            onClick={() => setSheetOpen(true)}
            className="flex items-center gap-1.5 p-1 pr-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80 text-xs font-semibold text-slate-800 dark:text-slate-200 min-h-[40px] active:scale-95 transition"
            aria-label="Switch account"
          >
            <div className="w-7 h-7 rounded-lg bg-slate-200 dark:bg-slate-800 flex items-center justify-center overflow-hidden flex-shrink-0">
              {selectedProfile?.avatar_url || selectedProfile?.avatar ? (
                <img src={selectedProfile.avatar_url || selectedProfile.avatar} alt="" className="w-full h-full object-cover" />
              ) : (
                <User className="w-4 h-4 text-slate-400" />
              )}
            </div>
            <span className="max-w-[75px] truncate font-medium">
              {selectedProfile?.x_handle ? `@${selectedProfile.x_handle.replace(/^@/, "")}` : "Profile"}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          </button>
        </div>
      </header>

      {/* Mobile Account Switcher Bottom Sheet */}
      {sheetOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex flex-col justify-end animate-in fade-in duration-150">
          <div 
            className="absolute inset-0 bg-slate-950/60 backdrop-blur-xs" 
            onClick={() => setSheetOpen(false)} 
          />
          <div className="relative bg-white dark:bg-slate-900 rounded-t-3xl max-h-[85dvh] flex flex-col pb-safe border-t border-slate-200 dark:border-slate-800 shadow-2xl animate-in slide-in-from-bottom duration-200">
            {/* Grab Handle */}
            <div className="w-12 h-1.5 bg-slate-300 dark:bg-slate-700 rounded-full mx-auto my-3 shrink-0" />
            
            {/* Header */}
            <div className="flex items-center justify-between px-5 pb-3 border-b border-slate-200 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-base text-slate-900 dark:text-white">Switch Profile</h3>
                <p className="text-xs text-slate-500">Connected X accounts & credentials</p>
              </div>
              <button 
                onClick={() => setSheetOpen(false)} 
                className="p-2 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 active:scale-90 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Profile List */}
            <div className="p-3 overflow-y-auto space-y-2 max-h-[50dvh]">
              {profiles.map((p) => {
                const isSelected = p.id === selectedProfileId;
                return (
                  <button
                    key={p.id}
                    onClick={() => {
                      setSelectedProfileId(p.id);
                      setSheetOpen(false);
                    }}
                    className={cn(
                      "w-full flex items-center justify-between p-3 min-h-[56px] rounded-2xl border text-left transition active:scale-[0.98]",
                      isSelected
                        ? "bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800/80 shadow-xs"
                        : "border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                    )}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-10 h-10 rounded-xl bg-slate-200 dark:bg-slate-800 flex items-center justify-center overflow-hidden flex-shrink-0">
                        {p.avatar_url || p.avatar ? (
                          <img src={p.avatar_url || p.avatar} alt="" className="w-full h-full object-cover" />
                        ) : (
                          <span className="font-bold text-sm text-slate-600 dark:text-slate-300">
                            {p.display_name?.[0]?.toUpperCase() || "X"}
                          </span>
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-sm text-slate-900 dark:text-white truncate">
                            {p.display_name}
                          </span>
                          <span className={cn(
                            "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold",
                            p.status === "active"
                              ? "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400"
                              : "bg-slate-100 dark:bg-slate-800 text-slate-500"
                          )}>
                            {p.status || "active"}
                          </span>
                        </div>

                        <span className="text-xs text-slate-500 dark:text-slate-400 truncate block">
                          @{p.x_handle?.replace(/^@/, "")}
                        </span>
                      </div>
                    </div>
                    {isSelected && (
                      <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-white flex-shrink-0">
                        <Check className="w-3.5 h-3.5 stroke-[3]" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Connect Account CTA */}
            <div className="p-4 border-t border-slate-200 dark:border-slate-800">
              <button
                onClick={() => {
                  setSheetOpen(false);
                  setModals({ connect: true });
                }}
                className="w-full flex items-center justify-center gap-2 py-3 min-h-[48px] rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition active:scale-[0.98] shadow-xs"
              >
                <Plus className="w-4 h-4 stroke-[2.5]" />
                Connect New X Account
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
