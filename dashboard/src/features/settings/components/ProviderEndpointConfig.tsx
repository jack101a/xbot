"use client";

import React from "react";
import { Server, RefreshCw, Eye, EyeOff } from "lucide-react";
import { SystemConfig } from "@/lib/api";

interface ProviderEndpointConfigProps {
  config: Partial<SystemConfig>;
  setConfig: React.Dispatch<React.SetStateAction<Partial<SystemConfig>>>;
  showKey: boolean;
  toggleShowKey: () => void;
  fetchingModels: boolean;
  onFetchModels: () => void;
  availableModelsCount: number;
}

export function ProviderEndpointConfig({
  config,
  setConfig,
  showKey,
  toggleShowKey,
  fetchingModels,
  onFetchModels,
  availableModelsCount,
}: ProviderEndpointConfigProps) {
  return (
    <div className="p-3.5 sm:p-4 rounded-xl border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/40 dark:bg-indigo-950/20 space-y-3 sm:space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-400 flex items-center gap-2">
          <Server className="w-4 h-4" />
          <span>OpenAI-Compatible / LiteLLM Provider</span>
        </h4>
        <button
          type="button"
          onClick={onFetchModels}
          disabled={fetchingModels}
          className="w-full sm:w-auto px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition disabled:opacity-50 shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${fetchingModels ? "animate-spin" : ""}`} />
          <span>Fetch Available Models</span>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            API Base URL
          </label>
          <input
            type="text"
            value={config.LITELLM_BASE_URL || ""}
            onChange={(e) => setConfig({ ...config, LITELLM_BASE_URL: e.target.value })}
            placeholder="https://llm.002529.xyz/v1"
            className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            API Key / Token
          </label>
          <div className="relative">
            <input
              type={showKey ? "text" : "password"}
              value={config.LITELLM_API_KEY || ""}
              onChange={(e) => setConfig({ ...config, LITELLM_API_KEY: e.target.value })}
              placeholder="sk-..."
              className="w-full px-3 py-2 pr-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white"
            />
            <button
              type="button"
              onClick={toggleShowKey}
              className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
            >
              {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </div>

      <div className="text-[11px] text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
        <span className="font-semibold text-emerald-600 dark:text-emerald-400">● {availableModelsCount} Models Loaded</span>
        <span>• Auto-routed via model prefixes</span>
      </div>
    </div>
  );
}
