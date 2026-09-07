"use client";

import React from "react";
import { Search, RefreshCw, Trash2, Cpu, Activity } from "lucide-react";
import { AILogFilterState } from "../types";

interface AILogHeaderProps {
  filter: AILogFilterState;
  setFilter: React.Dispatch<React.SetStateAction<AILogFilterState>>;
  totalCount: number;
  loading: boolean;
  onRefresh: () => void;
  onClear: () => void;
}

const PROVIDERS = [
  { id: "", label: "All Providers" },
  { id: "chatgpt", label: "ChatGPT Web Bridge" },
  { id: "gemini", label: "Google Gemini" },
  { id: "deepseek", label: "DeepSeek" },
  { id: "mistral", label: "Mistral" },
  { id: "openrouter", label: "OpenRouter" },
  { id: "litellm", label: "LiteLLM / Ollama" },
];

export function AILogHeader({
  filter,
  setFilter,
  totalCount,
  loading,
  onRefresh,
  onClear,
}: AILogHeaderProps) {
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 sm:p-5 mb-5 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-600 dark:text-purple-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              AI Prompt & Output Inspector
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 font-semibold">
                {totalCount} logged
              </span>
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Inspect full raw system prompts, user directives, and AI response payloads across all providers.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          <button
            onClick={() => setFilter((prev) => ({ ...prev, autoRefresh: !prev.autoRefresh }))}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition flex items-center gap-1.5 ${
              filter.autoRefresh
                ? "bg-emerald-50 border-emerald-300 text-emerald-700 dark:bg-emerald-950/40 dark:border-emerald-800 dark:text-emerald-300"
                : "bg-slate-50 border-slate-200 text-slate-600 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-400"
            }`}
          >
            <Activity className={`w-3.5 h-3.5 ${filter.autoRefresh ? "animate-pulse" : ""}`} />
            {filter.autoRefresh ? "Live Polling On" : "Auto-Refresh Off"}
          </button>

          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition disabled:opacity-50"
            title="Refresh logs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>

          <button
            onClick={onClear}
            className="p-2 rounded-lg border border-rose-200 dark:border-rose-900/60 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition"
            title="Clear prompt logs"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-2.5">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search prompts, responses, actions, or topics..."
            value={filter.searchQuery}
            onChange={(e) => setFilter((prev) => ({ ...prev, searchQuery: e.target.value }))}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-purple-500"
          />
        </div>

        <select
          value={filter.providerFilter}
          onChange={(e) => setFilter((prev) => ({ ...prev, providerFilter: e.target.value }))}
          className="px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500"
        >
          {PROVIDERS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
