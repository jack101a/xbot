"use client";

import React from "react";
import { Clock, Info } from "lucide-react";

interface CircadianScheduleEditorProps {
  config: any;
  setConfig: React.Dispatch<React.SetStateAction<any>>;
}

export function CircadianScheduleEditor({
  config,
  setConfig,
}: CircadianScheduleEditorProps) {
  const activeHoursStart = config.schedule?.active_hours
    ? parseInt(config.schedule.active_hours.split("-")[0].split(":")[0])
    : (config.active_hours_start ?? 8);

  const activeHoursEnd = config.schedule?.active_hours
    ? parseInt(config.schedule.active_hours.split("-")[1].split(":")[0])
    : (config.active_hours_end ?? 22);

  const cooldownSeconds =
    config.limits?.cooldown_seconds ?? config.action_delay_seconds ?? 15;

  const handleStartHourChange = (start: number) => {
    const activeHours = `${String(start).padStart(2, "0")}:00-${String(activeHoursEnd).padStart(2, "0")}:00`;
    setConfig({
      ...config,
      schedule: { ...(config.schedule || {}), active_hours: activeHours },
      active_hours_start: start,
    });
  };

  const handleEndHourChange = (end: number) => {
    const activeHours = `${String(activeHoursStart).padStart(2, "0")}:00-${String(end).padStart(2, "0")}:00`;
    setConfig({
      ...config,
      schedule: { ...(config.schedule || {}), active_hours: activeHours },
      active_hours_end: end,
    });
  };

  const handleCooldownChange = (val: number) => {
    setConfig({
      ...config,
      limits: { ...(config.limits || {}), cooldown_seconds: val },
      action_delay_seconds: val,
    });
  };

  return (
    <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
      <div className="flex items-center gap-2">
        <Clock className="w-4 h-4 text-indigo-500" />
        <h3 className="font-bold text-sm text-slate-900 dark:text-white">Schedule & Stealth Delays</h3>
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        Configure human-like operating hours and randomized jitter pauses between browser actions.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 pt-2">
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
            Active Hours Start
          </label>
          <input
            type="number"
            min="0"
            max="23"
            value={activeHoursStart}
            onChange={(e) => handleStartHourChange(parseInt(e.target.value) || 0)}
            className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-semibold text-slate-900 dark:text-white"
          />
          <span className="text-[10px] text-slate-400 mt-1 block">e.g. 8 (8:00 AM)</span>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
            Active Hours End
          </label>
          <input
            type="number"
            min="0"
            max="23"
            value={activeHoursEnd}
            onChange={(e) => handleEndHourChange(parseInt(e.target.value) || 22)}
            className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-semibold text-slate-900 dark:text-white"
          />
          <span className="text-[10px] text-slate-400 mt-1 block">e.g. 22 (10:00 PM)</span>
        </div>
      </div>

      <div className="pt-2">
        <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
          <span>Cooldown Delay Between Actions (Seconds)</span>
          <span className="text-indigo-600 dark:text-indigo-400 font-bold">
            {cooldownSeconds}s
          </span>
        </div>
        <input
          type="range"
          min="0"
          max="120"
          value={cooldownSeconds}
          onChange={(e) => handleCooldownChange(parseInt(e.target.value))}
          className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
        />
      </div>

      <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-600 dark:text-slate-400 flex items-start gap-2">
        <Info className="w-4 h-4 text-indigo-500 flex-shrink-0 mt-0.5" />
        <span>
          The automation engine applies ±35% random timing jitter to all action delays to ensure organic, human-like activity patterns.
        </span>
      </div>
    </div>
  );
}
