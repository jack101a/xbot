"use client";

import React from "react";
import { useAppStore } from "@/store/useAppStore";
import { X, Terminal, Trash2 } from "lucide-react";

export function BottomConsole() {
  const { isConsoleOpen, setConsoleOpen, activityStream } = useAppStore();

  if (!isConsoleOpen) return null;

  return (
    <div className="fixed bottom-14 lg:bottom-0 left-0 lg:left-72 right-0 h-64 sm:h-52 bg-slate-950/95 backdrop-blur-xl border-t border-slate-800 z-45 flex flex-col shadow-2xl">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-900/90">
        <div className="flex items-center gap-2 text-slate-300">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-mono font-semibold uppercase tracking-wider">Live Activity Console</span>
          <span className="text-[10px] font-mono text-slate-500">({activityStream.length} logs)</span>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => useAppStore.setState({ activityStream: [] })} 
            className="p-1 rounded text-slate-500 hover:text-slate-300 transition" 
            title="Clear logs"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <button 
            onClick={() => setConsoleOpen(false)} 
            className="p-1 rounded text-slate-500 hover:text-slate-300 transition"
            title="Close console"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 font-mono text-[10px] sm:text-xs space-y-1">
        {activityStream.length === 0 ? (
          <div className="text-slate-600 italic px-2 py-3 text-center">No recent activity logged...</div>
        ) : (
          activityStream.map((log) => (
            <div
              key={log.id}
              className={`px-2 py-1 flex items-start gap-2 rounded ${
                log.type === "error"
                  ? "text-rose-400 bg-rose-950/30 border border-rose-900/30"
                  : log.type === "success"
                  ? "text-emerald-400 bg-emerald-950/30 border border-emerald-900/30"
                  : "text-slate-300 hover:bg-slate-900/60"
              }`}
            >
              <span className="text-slate-600 shrink-0 text-[10px] mt-0.5">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className="break-all">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
