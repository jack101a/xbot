"use client";

import React from "react";
import { X, ShieldCheck } from "lucide-react";
import { Profile } from "@/lib/api";

interface ConnectAccountHeaderProps {
  profile: Profile;
  customHandle: string;
  onClose: () => void;
}

export function ConnectAccountHeader({
  profile,
  customHandle,
  onClose,
}: ConnectAccountHeaderProps) {
  return (
    <div className="relative z-10 flex items-start justify-between pb-3.5 sm:pb-4 border-b border-slate-800">
      <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
        <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20 flex-shrink-0">
          <ShieldCheck size={20} />
        </div>
        <div className="min-w-0">
          <h2 className="text-base sm:text-lg font-bold text-white tracking-tight flex items-center gap-1.5 sm:gap-2 truncate">
            <span>Connect X Account</span>
            <span className="text-[10px] sm:text-xs font-medium px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 truncate">
              @{customHandle || profile.profile_slug}
            </span>
          </h2>
          <p className="text-[11px] sm:text-xs text-slate-400 mt-0.5 truncate">
            Import session cookies to enable automated browsing & posting
          </p>
        </div>
      </div>
      <button
        onClick={onClose}
        className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800/80 transition-colors flex-shrink-0"
      >
        <X size={18} />
      </button>
    </div>
  );
}
