"use client";

import React from "react";
import {
  Cpu,
  Sparkles,
  Crosshair,
  Layers,
  Vote,
  TrendingUp,
  BrainCircuit,
  Heart,
  ArrowRight,
  ShieldCheck,
  Zap,
  Flame,
} from "lucide-react";
import { SystemConfig } from "@/lib/api";

interface TaskModelAssignmentsProps {
  config: Partial<SystemConfig>;
  setConfig: React.Dispatch<React.SetStateAction<Partial<SystemConfig>>>;
  availableModels: string[];
}

interface ModelFieldDef {
  key: keyof SystemConfig;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const MODEL_FIELDS: ModelFieldDef[] = [
  {
    key: "MODEL_POST_CREATION",
    label: "Post Creation & Viral Hooks",
    description: "Composing viral timeline posts, threads, and draft takes",
    icon: <Sparkles className="w-4 h-4 text-amber-500" />,
  },
  {
    key: "MODEL_REPLY_ANALYSIS",
    label: "AI Sniper Replies",
    description: "Crafting contrarian, roast, and framework replies to KOLs",
    icon: <Crosshair className="w-4 h-4 text-rose-500" />,
  },
  {
    key: "MODEL_HOOK_OPTIMIZER",
    label: "Hook Optimizer & Virality",
    description: "Evaluating curiosity gaps, open loops, and high-dwell hooks",
    icon: <Layers className="w-4 h-4 text-indigo-500" />,
  },
  {
    key: "MODEL_POLL_GENERATOR",
    label: "Interactive Poll Generator",
    description: "Constructing debate polls with options under 25 characters",
    icon: <Vote className="w-4 h-4 text-emerald-500" />,
  },
  {
    key: "MODEL_TREND_ANALYSIS",
    label: "Trend Radar & RSS Commentary",
    description: "Evaluating live breaking news and synthesizing hot takes",
    icon: <TrendingUp className="w-4 h-4 text-sky-500" />,
  },
  {
    key: "MODEL_REFLECTION",
    label: "Cognitive Reflection & Diary",
    description: "Synthesizing daily persona memory and subconscious traits",
    icon: <BrainCircuit className="w-4 h-4 text-purple-500" />,
  },
  {
    key: "MODEL_PLANNER",
    label: "Autonomous Session Planner",
    description: "Session opportunity triage and multi-action scheduling",
    icon: <Cpu className="w-4 h-4 text-blue-500" />,
  },
  {
    key: "MODEL_LIKE_RETWEET",
    label: "Timeline Engagement & Likes",
    description: "Rapid heuristic evaluation and timeline curation",
    icon: <Heart className="w-4 h-4 text-pink-500" />,
  },
];

const REAL_PROXY_MODELS = [
  "litellm/gemini-3.1-flash-lite",
  "litellm/gemini-flash-latest",
  "litellm/gemini-3.5-flash",
  "litellm/gemini-3.6-flash",
  "litellm/gemini-3.7-flash",
  "litellm/gemini-flash-latest-lite",
  "litellm/deepseek-v4-flash-0731",
  "litellm/deepseek-v4-pro-0813",
  "litellm/gpt-oss-120b",
  "litellm/nemotron-3-ultra-550b-a55b",
  "litellm/gemma-4-31b",
  "litellm/gemma-4-26b",
  "litellm/glm-5.2",
  "litellm/kimi-k3",
  "litellm/minimaxai/minimax-m3",
  "litellm/mistral-large",
  "litellm/mistral-medium",
  "litellm/mistral-small",
  "litellm/qwen-3.5",
  "chatgpt/auto",
];

export function TaskModelAssignments({
  config,
  setConfig,
  availableModels,
}: TaskModelAssignmentsProps) {
  // Combine real models from proxy + any custom configured models
  const allModelOptions = Array.from(
    new Set([
      ...REAL_PROXY_MODELS,
      ...availableModels.map((m) => (m.includes("/") ? m : `litellm/${m}`)),
    ])
  );

  const updateCascade = (
    fieldKey: keyof SystemConfig,
    tierIndex: 0 | 1 | 2,
    newValue: string
  ) => {
    const rawVal = (config[fieldKey] as string) || "";
    const tiers = rawVal.split(",").map((t) => t.trim()).filter(Boolean);

    // Pad tiers to 3 items
    while (tiers.length < 3) {
      tiers.push("");
    }

    tiers[tierIndex] = newValue.trim();
    const finalStr = tiers.filter(Boolean).join(",");
    setConfig((prev) => ({ ...prev, [fieldKey]: finalStr }));
  };

  const applyGlobalPreset = (preset: "speed" | "quality" | "resilience") => {
    let mapping: Record<string, string> = {};

    if (preset === "speed") {
      const fastChain = "litellm/gemini-3.1-flash-lite,litellm/deepseek-v4-flash-0731,litellm/gemini-flash-latest-lite";
      mapping = {
        MODEL_POST_CREATION: "litellm/gemini-3.5-flash,litellm/deepseek-v4-flash-0731,litellm/gemini-3.1-flash-lite",
        MODEL_REPLY_ANALYSIS: fastChain,
        MODEL_HOOK_OPTIMIZER: "litellm/gemini-3.5-flash,litellm/deepseek-v4-flash-0731,litellm/gemini-3.1-flash-lite",
        MODEL_POLL_GENERATOR: fastChain,
        MODEL_TREND_ANALYSIS: fastChain,
        MODEL_REFLECTION: fastChain,
        MODEL_PLANNER: fastChain,
        MODEL_LIKE_RETWEET: fastChain,
      };
    } else if (preset === "quality") {
      const reasoningChain = "litellm/deepseek-v4-pro-0813,litellm/gemini-3.5-flash,litellm/gpt-oss-120b";
      mapping = {
        MODEL_POST_CREATION: reasoningChain,
        MODEL_REPLY_ANALYSIS: "litellm/gemini-3.5-flash,litellm/deepseek-v4-pro-0813,litellm/gpt-oss-120b",
        MODEL_HOOK_OPTIMIZER: reasoningChain,
        MODEL_POLL_GENERATOR: "litellm/gemini-3.5-flash,litellm/deepseek-v4-flash-0731,litellm/gpt-oss-120b",
        MODEL_TREND_ANALYSIS: reasoningChain,
        MODEL_REFLECTION: "litellm/deepseek-v4-pro-0813,litellm/gemini-3.5-flash,litellm/gpt-oss-120b",
        MODEL_PLANNER: reasoningChain,
        MODEL_LIKE_RETWEET: "litellm/gemini-3.1-flash-lite,litellm/deepseek-v4-flash-0731,litellm/mistral-large",
      };
    } else if (preset === "resilience") {
      const triProvider = "litellm/gemini-flash-latest,litellm/deepseek-v4-flash-0731,litellm/mistral-large";
      mapping = {
        MODEL_POST_CREATION: "litellm/deepseek-v4-pro-0813,litellm/gemini-flash-latest,litellm/mistral-large",
        MODEL_REPLY_ANALYSIS: triProvider,
        MODEL_HOOK_OPTIMIZER: "litellm/deepseek-v4-pro-0813,litellm/gemini-flash-latest,litellm/mistral-large",
        MODEL_POLL_GENERATOR: triProvider,
        MODEL_TREND_ANALYSIS: triProvider,
        MODEL_REFLECTION: triProvider,
        MODEL_PLANNER: triProvider,
        MODEL_LIKE_RETWEET: triProvider,
      };
    }

    setConfig((prev) => ({ ...prev, ...mapping }));
  };

  const renderTierSelect = (
    fieldKey: keyof SystemConfig,
    tierIndex: 0 | 1 | 2,
    tierName: string,
    currentVal: string,
    badgeColor: string
  ) => {
    return (
      <div className="flex-1 min-w-[150px] space-y-1">
        <div className="flex items-center justify-between">
          <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${badgeColor}`}>
            {tierName}
          </span>
          {currentVal && (
            <span className="text-[10px] font-mono text-slate-400 truncate max-w-[120px]">
              {currentVal.split("/")[0]}
            </span>
          )}
        </div>
        <select
          value={currentVal}
          onChange={(e) => updateCascade(fieldKey, tierIndex, e.target.value)}
          className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700/80 bg-white dark:bg-slate-900 text-xs font-mono text-slate-800 dark:text-slate-200 focus:ring-1 focus:ring-indigo-500"
        >
          {tierIndex > 0 && <option value="">-- None (Disabled) --</option>}
          {currentVal && !allModelOptions.includes(currentVal) && (
            <option value={currentVal}>{currentVal}</option>
          )}
          {allModelOptions.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>
    );
  };

  const renderTaskCascadeCard = (field: ModelFieldDef) => {
    const rawVal = (config[field.key] as string) || "";
    const tiers = rawVal.split(",").map((t) => t.trim()).filter(Boolean);
    const tier1 = tiers[0] || "";
    const tier2 = tiers[1] || "";
    const tier3 = tiers[2] || "";

    return (
      <div
        key={field.key}
        className="p-3.5 rounded-2xl bg-white dark:bg-slate-900/90 border border-slate-200/90 dark:border-slate-800 shadow-sm space-y-2.5"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800/80">
              {field.icon}
            </div>
            <div>
              <h5 className="text-xs font-bold text-slate-900 dark:text-white">
                {field.label}
              </h5>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                {field.description}
              </p>
            </div>
          </div>
        </div>

        {/* 3-Tier Cascade Grid */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 bg-slate-50 dark:bg-slate-950/70 p-2.5 rounded-xl border border-slate-200/70 dark:border-slate-800/70">
          {renderTierSelect(
            field.key,
            0,
            "1. Primary",
            tier1,
            "bg-indigo-100 text-indigo-700 dark:bg-indigo-950/80 dark:text-indigo-300"
          )}
          <ArrowRight className="w-3.5 h-3.5 text-slate-400 hidden sm:block shrink-0" />
          {renderTierSelect(
            field.key,
            1,
            "2. Fallback 1",
            tier2,
            "bg-amber-100 text-amber-700 dark:bg-amber-950/80 dark:text-amber-300"
          )}
          <ArrowRight className="w-3.5 h-3.5 text-slate-400 hidden sm:block shrink-0" />
          {renderTierSelect(
            field.key,
            2,
            "3. Fallback 2",
            tier3,
            "bg-rose-100 text-rose-700 dark:bg-rose-950/80 dark:text-rose-300"
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Header and Quick 1-Click Presets */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-2xl bg-gradient-to-r from-indigo-50/70 via-slate-50 to-purple-50/70 dark:from-indigo-950/30 dark:via-slate-900/50 dark:to-purple-950/30 border border-indigo-100 dark:border-indigo-900/40">
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-500" />
            <span>3-Tier Model Fallback Selector</span>
          </h4>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            If Primary fails or times out, bot instantly cascades to Fallback 1, then Fallback 2.
          </p>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-1">
            Presets:
          </span>
          <button
            type="button"
            onClick={() => applyGlobalPreset("speed")}
            className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[11px] font-medium text-slate-700 dark:text-slate-200 hover:border-emerald-500 flex items-center gap-1 shadow-xs transition-colors"
          >
            <Zap className="w-3 h-3 text-emerald-500" />
            <span>High Speed</span>
          </button>
          <button
            type="button"
            onClick={() => applyGlobalPreset("quality")}
            className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[11px] font-medium text-slate-700 dark:text-slate-200 hover:border-amber-500 flex items-center gap-1 shadow-xs transition-colors"
          >
            <Flame className="w-3 h-3 text-amber-500" />
            <span>Max Quality</span>
          </button>
          <button
            type="button"
            onClick={() => applyGlobalPreset("resilience")}
            className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[11px] font-medium text-slate-700 dark:text-slate-200 hover:border-indigo-500 flex items-center gap-1 shadow-xs transition-colors"
          >
            <ShieldCheck className="w-3 h-3 text-indigo-500" />
            <span>Tri-Provider</span>
          </button>
        </div>
      </div>

      {/* Task Model Cards */}
      <div className="grid grid-cols-1 gap-3">
        {MODEL_FIELDS.map((field) => renderTaskCascadeCard(field))}
      </div>
    </div>
  );
}
