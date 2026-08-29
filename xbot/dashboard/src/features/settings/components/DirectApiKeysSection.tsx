"use client";

import React from "react";
import { Key } from "lucide-react";
import { SystemConfig } from "@/lib/api";

import { ChatGPTBridgeCard } from "./ChatGPTBridgeCard";

interface DirectApiKeysSectionProps {
  config: Partial<SystemConfig>;
  setConfig: React.Dispatch<React.SetStateAction<Partial<SystemConfig>>>;
  showKeys: { [key: string]: boolean };
  toggleShowKey: (key: string) => void;
}

interface KeyFieldDef {
  key: keyof SystemConfig;
  fieldId: string;
  label: string;
  placeholder: string;
}

const KEY_FIELDS: KeyFieldDef[] = [
  {
    key: "GEMINI_API_KEY",
    fieldId: "gemini",
    label: "Google Gemini Key",
    placeholder: "AIzaSy...",
  },
  {
    key: "MISTRAL_API_KEY",
    fieldId: "mistral",
    label: "Mistral AI Key",
    placeholder: "mis_...",
  },
  {
    key: "DEEPSEEK_API_KEY",
    fieldId: "deepseek",
    label: "DeepSeek Key",
    placeholder: "sk-...",
  },
  {
    key: "OPENROUTER_API_KEY",
    fieldId: "openrouter",
    label: "OpenRouter Key",
    placeholder: "sk-or-...",
  },
  {
    key: "NVIDIA_API_KEY",
    fieldId: "nvidia",
    label: "NVIDIA GenAI Key (Flux Fallback)",
    placeholder: "nvapi-...",
  },
];

export function DirectApiKeysSection({
  config,
  setConfig,
  showKeys,
  toggleShowKey,
}: DirectApiKeysSectionProps) {
  return (
    <div className="space-y-3 pt-2">
      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-2">
        <Key className="w-4 h-4" />
        <span>Optional Direct Provider Keys</span>
      </h4>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {KEY_FIELDS.map((item) => (
          <div key={item.fieldId}>
            <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-1">
              {item.label}
            </label>
            <input
              type={showKeys[item.fieldId] ? "text" : "password"}
              value={(config[item.key] as string) || ""}
              onChange={(e) => setConfig({ ...config, [item.key]: e.target.value })}
              placeholder={item.placeholder}
              className="w-full px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white"
            />
          </div>
        ))}
      </div>

      <ChatGPTBridgeCard />
    </div>
  );
}
