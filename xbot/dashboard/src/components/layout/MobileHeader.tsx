"use client";

import React from "react";
import { useAppStore } from "@/store/useAppStore";
import { Layers, ChevronDown, User, Check, Plus, Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils/cn";

export function MobileHeader() {
  const { profiles, selectedProfileId, setSelectedProfileId, setModals, darkMode, setDarkMode } = useAppStore();
  const [dropdownOpen, setDropdownOpen] = React.useState(false);
  const selectedProfile = profiles.find(p => p.id === selectedProfileId);

  return (
    <header className="lg:hidden sticky top-0 z-30 flex items-center justify-between px-4 py-3 bg-white/85 dark:bg-slate-900/85  border-b border-slate-200 dark:border-slate-800 shadow-sm">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
          <Layers className="w-4 h-4 text-white" />
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-bold text-sm text-slate-900 dark:text-white">XBot Pro</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Theme Toggle */}
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
          aria-label="Toggle Theme"
        >
          {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
        </button>

        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-1.5 p-1.5 pr-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-xs font-medium text-slate-800 dark:text-slate-200"
          >
          <div className="w-6 h-6 rounded-md bg-slate-200 dark:bg-slate-800 flex items-center justify-center overflow-hidden">
            {selectedProfile?.avatar_url || selectedProfile?.avatar ? (
              <img src={selectedProfile.avatar_url || selectedProfile.avatar} alt="" className="w-full h-full object-cover" />
            ) : (
              <User className="w-3.5 h-3.5 text-slate-400" />
            )}
          </div>
          <span className="max-w-[70px] truncate">
            {selectedProfile?.x_handle ? `@${selectedProfile.x_handle.replace(/^@/, "")}` : "Profile"}
          </span>
          <ChevronDown className={cn("w-3.5 h-3.5 text-slate-400", dropdownOpen && "rotate-180")} />
        </button>

        {dropdownOpen && (
          <div className="absolute right-0 mt-2 w-56 p-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-xl z-50 space-y-1">
            {profiles.map(p => (
              <button
                key={p.id}
                onClick={() => { setSelectedProfileId(p.id); setDropdownOpen(false); }}
                className={cn(
                  "w-full flex items-center justify-between p-2 rounded-md text-left text-sm",
                  p.id === selectedProfileId ? "bg-blue-50 dark:bg-blue-900/20 text-blue-600" : "hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
                )}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div className="w-6 h-6 rounded-md bg-slate-100 flex items-center justify-center text-[10px]">
                    {p.display_name[0]}
                  </div>
                  <span className="truncate text-xs">{p.display_name}</span>
                </div>
                {p.id === selectedProfileId && <Check className="w-3.5 h-3.5" />}
              </button>
            ))}
            <div className="pt-1 mt-1 border-t border-slate-100 dark:border-slate-800">
              <button
                onClick={() => { setDropdownOpen(false); setModals({ connect: true }); }}
                className="w-full flex items-center gap-2 p-2 rounded-md text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <Plus className="w-4 h-4" />
                Connect
              </button>
            </div>
          </div>
        )}
        </div>
      </div>
    </header>
  );
}
