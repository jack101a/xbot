import React from "react";
import { Layers, Search, Sparkles, Calendar, Send } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center p-6 my-auto">
      <div className="w-14 h-14 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-100 dark:border-indigo-900/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400 mb-3 shadow-sm">
        <Layers className="w-7 h-7" />
      </div>
      <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-1">
        No Campaign Generated Yet
      </h3>
      <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mb-6 leading-relaxed">
        Enter your campaign directive or select an inspiration template on the left panel, then click &apos;Research &amp; Generate Campaign&apos;.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-md w-full text-left">
        <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 flex items-start gap-2">
          <Search className="w-3.5 h-3.5 text-sky-500 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">Live X Intelligence</div>
            <div className="text-[10px] text-slate-500 dark:text-slate-400">Scrapes real-time trending context & media</div>
          </div>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 flex items-start gap-2">
          <Sparkles className="w-3.5 h-3.5 text-indigo-500 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">Multi-Asset Generation</div>
            <div className="text-[10px] text-slate-500 dark:text-slate-400">Creates threads, polls, and media posts</div>
          </div>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 flex items-start gap-2">
          <Calendar className="w-3.5 h-3.5 text-purple-500 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">Smart Scheduling</div>
            <div className="text-[10px] text-slate-500 dark:text-slate-400">Auto-space deliverables across optimal slots</div>
          </div>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 flex items-start gap-2">
          <Send className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">One-Click Dispatch</div>
            <div className="text-[10px] text-slate-500 dark:text-slate-400">Publish immediately or queue for approval</div>
          </div>
        </div>
      </div>
    </div>
  );
}
