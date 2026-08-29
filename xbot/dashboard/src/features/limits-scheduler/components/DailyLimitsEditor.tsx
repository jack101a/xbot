"use client";

import React from "react";
import { ShieldCheck } from "lucide-react";

interface DailyLimitsEditorProps {
  config: any;
  setConfig: React.Dispatch<React.SetStateAction<any>>;
}

interface LimitDef {
  label: string;
  configKey: string;
  min: number;
  max: number;
  defaultValue: number;
}

const LIMIT_ITEMS: LimitDef[] = [
  {
    label: "Max Posts / Day",
    configKey: "max_posts_per_day",
    min: 1,
    max: 50,
    defaultValue: 15,
  },
  {
    label: "Max Sniper Replies / Day",
    configKey: "max_replies_per_day",
    min: 1,
    max: 100,
    defaultValue: 35,
  },
  {
    label: "Max Organic Likes / Day",
    configKey: "max_likes_per_day",
    min: 1,
    max: 150,
    defaultValue: 50,
  },
  {
    label: "Max Retweets / Day",
    configKey: "max_retweets_per_day",
    min: 0,
    max: 30,
    defaultValue: 10,
  },
];

export function DailyLimitsEditor({ config, setConfig }: DailyLimitsEditorProps) {
  const handleChange = (key: string, val: number) => {
    setConfig({
      ...config,
      limits: { ...(config.limits || {}), [key]: val },
      [key]: val,
    });
  };

  return (
    <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
      <div className="flex items-center gap-2">
        <ShieldCheck className="w-4 h-4 text-indigo-500" />
        <h3 className="font-bold text-sm text-slate-900 dark:text-white">Daily & Hourly Action Caps</h3>
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        Hard sliding-window limits enforced in Redis. If a cap is reached, the bot automatically stops that action type.
      </p>

      <div className="space-y-4 pt-2">
        {LIMIT_ITEMS.map((item) => {
          const currentValue =
            config.limits?.[item.configKey] ?? config[item.configKey] ?? item.defaultValue;

          return (
            <div key={item.configKey}>
              <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                <span>{item.label}</span>
                <span className="text-indigo-600 dark:text-indigo-400 font-bold">
                  {currentValue}
                </span>
              </div>
              <input
                type="range"
                min={item.min}
                max={item.max}
                value={currentValue}
                onChange={(e) => handleChange(item.configKey, parseInt(e.target.value))}
                className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
