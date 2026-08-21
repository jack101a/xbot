"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Settings,
  Key,
  Cpu,
  Save,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  RefreshCw,
  Server
} from "lucide-react";
import { api, SystemConfig } from "@/lib/api";

interface GlobalSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export function GlobalSettingsModal({
  isOpen,
  onClose,
  onSaved
}: GlobalSettingsModalProps) {
  const [config, setConfig] = useState<Partial<SystemConfig>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Show/hide API keys
  const [showKeys, setShowKeys] = useState<{ [key: string]: boolean }>({});

  useEffect(() => {
    if (!isOpen) return;
    async function loadConfig() {
      setLoading(true);
      try {
        const c = await api.getConfig();
        setConfig(c || {});
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
      setMsg({ type: "success", text: "Global AI and system settings saved successfully!" });
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
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
      <div className="w-full max-w-2xl max-h-[90vh] flex flex-col rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-100 dark:bg-indigo-950 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <Settings className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-900 dark:text-white">AI Provider & Global Settings</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Configure LLM intelligence providers and API keys</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {/* Notification */}
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

          {/* Model Config Section */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 flex items-center gap-2">
              <Cpu className="w-4 h-4" />
              <span>Default AI Models</span>
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Primary Reasoning Model
                </label>
                <input
                  type="text"
                  value={config.LITELLM_PRIMARY_MODEL || ""}
                  onChange={(e) => setConfig({ ...config, LITELLM_PRIMARY_MODEL: e.target.value })}
                  placeholder="gemini/gemini-1.5-flash or mistral/mistral-large-latest"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Fast Heuristic Model
                </label>
                <input
                  type="text"
                  value={config.LITELLM_FAST_MODEL || ""}
                  onChange={(e) => setConfig({ ...config, LITELLM_FAST_MODEL: e.target.value })}
                  placeholder="gemini/gemini-1.5-flash-8b or mistral/mistral-small-latest"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white"
                />
              </div>
            </div>
          </div>

          {/* API Keys Section */}
          <div className="space-y-3 pt-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 flex items-center gap-2">
              <Key className="w-4 h-4" />
              <span>Provider API Keys</span>
            </h4>

            <div className="space-y-3">
              {/* Google Gemini */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Google Gemini API Key
                </label>
                <div className="relative">
                  <input
                    type={showKeys["gemini"] ? "text" : "password"}
                    value={config.GEMINI_API_KEY || ""}
                    onChange={(e) => setConfig({ ...config, GEMINI_API_KEY: e.target.value })}
                    placeholder="AIzaSy..."
                    className="w-full px-3 py-2 pr-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white"
                  />
                  <button
                    type="button"
                    onClick={() => toggleShowKey("gemini")}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                  >
                    {showKeys["gemini"] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Mistral */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Mistral AI API Key
                </label>
                <div className="relative">
                  <input
                    type={showKeys["mistral"] ? "text" : "password"}
                    value={config.MISTRAL_API_KEY || ""}
                    onChange={(e) => setConfig({ ...config, MISTRAL_API_KEY: e.target.value })}
                    placeholder="mis_..."
                    className="w-full px-3 py-2 pr-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white"
                  />
                  <button
                    type="button"
                    onClick={() => toggleShowKey("mistral")}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                  >
                    {showKeys["mistral"] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* DeepSeek */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  DeepSeek API Key
                </label>
                <div className="relative">
                  <input
                    type={showKeys["deepseek"] ? "text" : "password"}
                    value={config.DEEPSEEK_API_KEY || ""}
                    onChange={(e) => setConfig({ ...config, DEEPSEEK_API_KEY: e.target.value })}
                    placeholder="sk-..."
                    className="w-full px-3 py-2 pr-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white"
                  />
                  <button
                    type="button"
                    onClick={() => toggleShowKey("deepseek")}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                  >
                    {showKeys["deepseek"] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* OpenRouter */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  OpenRouter API Key
                </label>
                <div className="relative">
                  <input
                    type={showKeys["openrouter"] ? "text" : "password"}
                    value={config.OPENROUTER_API_KEY || ""}
                    onChange={(e) => setConfig({ ...config, OPENROUTER_API_KEY: e.target.value })}
                    placeholder="sk-or-..."
                    className="w-full px-3 py-2 pr-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white"
                  />
                  <button
                    type="button"
                    onClick={() => toggleShowKey("openrouter")}
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                  >
                    {showKeys["openrouter"] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md transition disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? "Saving Settings..." : "Save Settings"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
