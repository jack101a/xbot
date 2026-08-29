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
    description: "Used for composing viral timeline posts and drafts",
    icon: <Sparkles className="w-3.5 h-3.5 text-amber-500" />,
  },
  {
    key: "MODEL_REPLY_ANALYSIS",
    label: "AI Sniper Replies",
    description: "Used for crafting contrarian/framework replies to KOLs",
    icon: <Crosshair className="w-3.5 h-3.5 text-rose-500" />,
  },
  {
    key: "MODEL_HOOK_OPTIMIZER",
    label: "Hook Optimizer (6 Archetypes)",
    description: "Evaluates curiosity gap, contrarian, and story angles",
    icon: <Layers className="w-3.5 h-3.5 text-indigo-500" />,
  },
  {
    key: "MODEL_POLL_GENERATOR",
    label: "Interactive Poll Generator",
    description: "Constructs debate polls with choices under 25 chars",
    icon: <Vote className="w-3.5 h-3.5 text-emerald-500" />,
  },
  {
    key: "MODEL_TREND_ANALYSIS",
    label: "Trend Radar & Commentary",
    description: "Evaluates live RSS news & creates timely takes",
    icon: <TrendingUp className="w-3.5 h-3.5 text-sky-500" />,
  },
  {
    key: "MODEL_REFLECTION",
    label: "Cognitive Reflection & Diary",
    description: "Synthesizes subconscious learned state & diary",
    icon: <BrainCircuit className="w-3.5 h-3.5 text-purple-500" />,
  },
  {
    key: "MODEL_PLANNER",
    label: "Autonomous Session Planner",
    description: "Evaluates dynamic opportunity scoring and scheduling",
    icon: <Cpu className="w-3.5 h-3.5 text-blue-500" />,
  },
  {
    key: "MODEL_LIKE_RETWEET",
    label: "Timeline Engagement & Likes",
    description: "Rapid heuristic evaluation of feed tweets",
    icon: <Heart className="w-3.5 h-3.5 text-pink-500" />,
  },
];

export function TaskModelAssignments({
  config,
  setConfig,
  availableModels,
}: TaskModelAssignmentsProps) {
  const renderModelSelect = (field: ModelFieldDef) => {
    const rawVal = (config[field.key] as string) || "";
    const cleanVal = rawVal.replace(/^litellm\//, "");

    return (
      <div
        key={field.key}
        className="space-y-1.5 p-3 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80"
      >
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
            {field.icon}
            <span>{field.label}</span>
          </label>
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-400">{field.description}</p>
        <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center">
          <select
            value={cleanVal}
            onChange={(e) => {
              const selected = e.target.value;
              setConfig({ ...config, [field.key]: `litellm/${selected}` });
            }}
            className="w-full sm:flex-1 px-3 py-2 sm:py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono text-slate-900 dark:text-white"
          >
            {cleanVal && !availableModels.includes(cleanVal) && (
              <option value={cleanVal}>{cleanVal}</option>
            )}
            {availableModels.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <input
            type="text"
            value={rawVal}
            onChange={(e) => setConfig({ ...config, [field.key]: e.target.value })}
            placeholder="custom/model-id"
            className="w-full sm:w-36 px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-[11px] font-mono text-slate-700 dark:text-slate-300"
            title="Exact routing string or comma-separated fallback"
          />
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-2">
        <Cpu className="w-4 h-4 text-indigo-500" />
        <span>Select Model For Each Autonomous Task</span>
      </h4>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {MODEL_FIELDS.map((field) => renderModelSelect(field))}
      </div>
    </div>
  );
}
