import React from "react";
import { Sparkles, RefreshCw } from "lucide-react";
import { formatISTDateTime } from "@/lib/time";
import { LearnedState } from "../types";

export function MemoryBankViewer({
  learnedState,
  reflecting,
  handleTriggerReflection
}: {
  learnedState: LearnedState | null;
  reflecting: boolean;
  handleTriggerReflection: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 sm:p-5 rounded-2xl border border-indigo-200 dark:border-indigo-800/60 bg-white dark:bg-slate-900">
        <div>
          <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-500" />
            <span>Performance-Driven Subconscious Reflection</span>
          </h3>
          <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">
            Reflections processed: {learnedState?.reflection_count || 0} &bull; Last updated:{" "}
            {learnedState?.last_reflected_at ? formatISTDateTime(learnedState.last_reflected_at) : "Never"}
          </p>
        </div>

        <button
          onClick={handleTriggerReflection}
          disabled={reflecting}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${reflecting ? "animate-spin" : ""}`} />
          <span>{reflecting ? "Reflecting..." : "Trigger Reflection Now"}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-3">
          <h4 className="font-bold text-xs uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
            Behavioral Adaptations
          </h4>
          <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
            {(learnedState?.characteristics?.behavioral_adaptations || []).map((item: string, i: number) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-indigo-500 font-bold">&bull;</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
          {(!learnedState?.characteristics?.behavioral_adaptations || learnedState.characteristics.behavioral_adaptations.length === 0) && (
            <p className="text-xs text-slate-400 italic">No behavioral adaptations synthesized yet.</p>
          )}
        </div>

        <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-3">
          <h4 className="font-bold text-xs uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
            Discovered High-ROI Topics
          </h4>
          <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
            {(learnedState?.interests?.emerging_topics || []).map((item: string, i: number) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-emerald-500 font-bold">&bull;</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
          {(!learnedState?.interests?.emerging_topics || learnedState.interests.emerging_topics.length === 0) && (
            <p className="text-xs text-slate-400 italic">No emerging topics discovered yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
