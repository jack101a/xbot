"use client";

import React, { useState } from "react";
import { User, ChevronDown, Check, Plus } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { Profile } from "@/lib/api";

interface ProfileSwitcherProps {
  profiles: Profile[];
  selectedProfileId: string | null;
  setSelectedProfileId: (id: string) => void;
  sidebarCollapsed: boolean;
  onOpenConnectModal: () => void;
}

export function ProfileSwitcher({
  profiles,
  selectedProfileId,
  setSelectedProfileId,
  sidebarCollapsed,
  onOpenConnectModal,
}: ProfileSwitcherProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const selectedProfile = profiles.find((p) => p.id === selectedProfileId);

  return (
    <div className={cn("relative", sidebarCollapsed ? "p-2 flex justify-center" : "p-3")}>
      {!sidebarCollapsed && (
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-1.5 px-1">
          Active Workspace
        </div>
      )}

      {profiles.length > 0 ? (
        <div className="relative w-full flex justify-center">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
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
                  dropdownOpen && "rotate-180"
                )}
              />
            )}
          </button>

          {/* Dropdown Menu */}
          {dropdownOpen && (
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
                      setDropdownOpen(false);
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
                    setDropdownOpen(false);
                    onOpenConnectModal();
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
          onClick={onOpenConnectModal}
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
  );
}
