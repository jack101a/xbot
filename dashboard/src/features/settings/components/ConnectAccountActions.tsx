"use client";

import React from "react";
import { Loader2, Monitor, ShieldCheck } from "lucide-react";

interface ConnectAccountActionsProps {
  isLaunchingBrowser: boolean;
  isSubmitting: boolean;
  onLaunchBrowser: () => void;
  onClose: () => void;
}

export function ConnectAccountActions({
  isLaunchingBrowser,
  isSubmitting,
  onLaunchBrowser,
  onClose,
}: ConnectAccountActionsProps) {
  return (
    <div className="pt-2 flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
      <button
        type="button"
        onClick={onLaunchBrowser}
        disabled={isLaunchingBrowser || isSubmitting}
        className="w-full sm:w-auto text-[11px] font-medium text-slate-400 hover:text-indigo-300 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-slate-800 hover:border-indigo-500/40 hover:bg-indigo-950/30 transition-all disabled:opacity-50 text-center"
        title="Launch browser GUI to log in manually"
      >
        {isLaunchingBrowser ? <Loader2 size={12} className="animate-spin" /> : <Monitor size={12} />}
        <span>Launch Browser Login</span>
      </button>

      <div className="flex items-center gap-2 w-full sm:w-auto">
        <button
          type="button"
          onClick={onClose}
          disabled={isSubmitting}
          className="flex-1 sm:flex-initial px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors text-center"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="flex-1 sm:flex-initial px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-lg shadow-indigo-600/30 transition-all flex items-center justify-center gap-2 disabled:opacity-50 text-center"
        >
          {isSubmitting ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              <span>Connecting...</span>
            </>
          ) : (
            <>
              <ShieldCheck size={14} />
              <span>Connect Account</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
