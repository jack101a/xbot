"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Cpu,
  Save,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { api, SystemConfig } from "@/lib/api";
import { ProviderEndpointConfig } from "./components/ProviderEndpointConfig";
import { TaskModelAssignments } from "./components/TaskModelAssignments";
import { DirectApiKeysSection } from "./components/DirectApiKeysSection";

interface GlobalSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

const DEFAULT_MODELS = [
  "gemini-3.1-flash-lite",
  "gemini-flash-latest",
  "gemini-3.5-flash",
  "gemini-3.6-flash",
  "gemini-3.7-flash",
  "gemini-flash-latest-lite",
  "deepseek-v4-flash-0731",
  "deepseek-v4-pro-0813",
  "gpt-oss-120b",
  "nemotron-3-ultra-550b-a55b",
  "gemma-4-31b",
  "gemma-4-26b",
  "glm-5.2",
  "kimi-k3",
  "minimaxai/minimax-m3",
  "mistral-large",
  "mistral-medium",
  "mistral-small",
  "qwen-3.5",
  "chatgpt/auto",
];

export function GlobalSettingsModal({
  isOpen,
  onClose,
  onSaved,
}: GlobalSettingsModalProps) {
  const [config, setConfig] = useState<Partial<SystemConfig>>({});
  const [, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [availableModels, setAvailableModels] = useState<string[]>(DEFAULT_MODELS);
  const [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [showKeys, setShowKeys] = useState<{ [key: string]: boolean }>({});

  const fetchModels = async (overrideBaseUrl?: string, overrideApiKey?: string) => {
    setFetchingModels(true);
    try {
      const bUrl = overrideBaseUrl || config.LITELLM_BASE_URL || "https://llm.002529.xyz/v1";
      const aKey = overrideApiKey || config.LITELLM_API_KEY || "sk-y_2_lD1m4Ojw1QFMDEWgwA";
      const res = await api.getSystemModels("litellm", bUrl, aKey);
      if (res?.models && res.models.length > 0) {
        const merged = Array.from(new Set([...res.models, ...DEFAULT_MODELS]));
        setAvailableModels(merged);
        setMsg({ type: "success", text: `Fetched ${res.models.length} active models from ${bUrl}` });
        setTimeout(() => setMsg(null), 3000);
      }
    } catch (err: any) {
      console.warn("Could not fetch remote models, using defaults", err);
    } finally {
      setFetchingModels(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    async function loadConfig() {
      setLoading(true);
      try {
        const c = await api.getConfig();
        setConfig(c || {});
        await fetchModels(c?.LITELLM_BASE_URL, c?.LITELLM_API_KEY);
      } catch (err: any) {
        console.error("Failed to load global config", err);
      } finally {
        setLoading(false);
      }
    }
    loadConfig();
  }, [isOpen]);

  if (!isOpen) return null;

  const toggleShowKey = (key: string) => {
    setShowKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await api.updateConfig(config);
      setMsg({ type: "success", text: "Global AI models & system settings saved successfully!" });
      setTimeout(() => {
        onSaved();
        onClose();
      }, 1200);
    } catch (err: any) {
      setMsg({ type: "error", text: err.message || "Failed to save settings." });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-2.5 sm:p-4 z-50 animate-in fade-in duration-200">
      <div className="w-full max-w-3xl max-h-[92vh] flex flex-col rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-3.5 sm:p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-indigo-100 dark:bg-indigo-950 flex items-center justify-center text-indigo-600 dark:text-indigo-400 flex-shrink-0">
              <Cpu className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="min-w-0">
              <h3 className="font-bold text-sm sm:text-base text-slate-900 dark:text-white truncate">
                AI Provider & Task Models
              </h3>
              <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 truncate">
                Configure OpenAI endpoints & model routing
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition flex-shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-3.5 sm:p-6 overflow-y-auto space-y-4 sm:space-y-6 flex-1">
          {msg && (
            <div
              className={`p-3.5 rounded-xl flex items-center justify-between border ${
                msg.type === "success"
                  ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
                  : "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300"
              }`}
            >
              <div className="flex items-center gap-2.5">
                {msg.type === "success" ? (
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                )}
                <span className="text-xs font-semibold">{msg.text}</span>
              </div>
            </div>
          )}

          <ProviderEndpointConfig
            config={config}
            setConfig={setConfig}
            showKey={!!showKeys["litellm"]}
            toggleShowKey={() => toggleShowKey("litellm")}
            fetchingModels={fetchingModels}
            onFetchModels={() => fetchModels()}
            availableModelsCount={availableModels.length}
          />

          <TaskModelAssignments
            config={config}
            setConfig={setConfig}
            availableModels={availableModels}
          />

          <DirectApiKeysSection
            config={config}
            setConfig={setConfig}
            showKeys={showKeys}
            toggleShowKey={toggleShowKey}
          />
        </div>

        {/* Footer */}
        <div className="p-3.5 sm:p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 flex flex-col-reverse sm:flex-row sm:items-center justify-between gap-3">
          <p className="text-[11px] sm:text-xs text-slate-500">
            Changes persist directly to <code className="text-indigo-600 dark:text-indigo-400 font-mono">.env</code> & active runtime
          </p>
          <div className="flex items-center justify-end gap-2 w-full sm:w-auto">
            <button
              onClick={onClose}
              className="flex-1 sm:flex-initial px-4 py-2.5 sm:py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 transition text-center"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 sm:flex-initial px-5 py-2.5 sm:py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-md shadow-indigo-600/20 text-center"
            >
              {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              <span>Save AI Settings</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
