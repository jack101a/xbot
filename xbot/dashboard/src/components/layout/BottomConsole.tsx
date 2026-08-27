"use client";

import React from "react";
import { useAppStore } from "@/store/useAppStore";
import { X, Terminal } from "lucide-react";

export function BottomConsole() {
  const { isConsoleOpen, setConsoleOpen, activityStream } = useAppStore();

  if (!isConsoleOpen) return null;

  return (
    <div className="fixed bottom-0 left-0 lg:left-72 right-0 h-48 bg-slate-950 border-t border-slate-800 z-40 flex flex-col shadow-2xl">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-900">
        <div className="flex items-center gap-2 text-slate-300">
          <Terminal className="w-4 h-4" />
          <span className="text-xs font-mono font-semibold uppercase tracking-wider">Live Activity Console</span>
        </div>
        <button onClick={() => setConsoleOpen(false)} className="text-slate-500 hover:text-slate-300">
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 font-mono text-[10px] sm:text-xs space-y-1">
        {activityStream.length === 0 ? (
          <div className="text-slate-600 italic px-2">No recent activity...</div>
        ) : (
          activityStream.map((log) => (
            <div key={log.id} className={`px-2 py-1 flex items-start gap-3 rounded ${
              log.type === 'error' ? 'text-red-400 bg-red-950/30' : 
              log.type === 'success' ? 'text-emerald-400 bg-emerald-950/30' : 
              'text-slate-300 hover:bg-slate-900'
            }`}>
              <span className="text-slate-600 shrink-0">{new Date(log.timestamp).toLocaleTimeString()}</span>
              <span className="break-all">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
