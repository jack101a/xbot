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

  const followGrowthInterval =
    config.schedule?.follow_growth_interval_minutes ??
    config.follow_growth_interval_minutes ??
    60;

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

  const handleFollowGrowthIntervalChange = (val: number) => {
    setConfig({
      ...config,
      schedule: { ...(config.schedule || {}), follow_growth_interval_minutes: val },
      follow_growth_interval_minutes: val,
    });
  };

  return (
    <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
      <div className="flex items-center gap-2">
        <Clock className="w-4 h-4 text-indigo-500" />
        <h3 className="font-bold text-sm text-slate-900 dark:text-white">Schedule & Stealth Delays</h3>
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        Configure human-like operating hours, follow growth cadence, and randomized jitter pauses between browser actions.
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

      {/* Follow Growth Post Cadence */}
      <div className="pt-3 border-t border-slate-200/60 dark:border-slate-800/60 space-y-2">
        <div className="flex justify-between items-center text-xs font-semibold text-slate-700 dark:text-slate-300">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span>Follow Growth Post Cadence</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
              {followGrowthInterval}m {followGrowthInterval === 60 ? "(1 hour)" : followGrowthInterval >= 60 ? `(${Math.round((followGrowthInterval / 60) * 10) / 10}h)` : ""}
            </span>
          </div>
          <span className="text-[11px] text-slate-400">Randomized ±15% anti-bot jitter</span>
        </div>

        <input
          type="range"
          min="15"
          max="240"
          step="5"
          value={followGrowthInterval}
          onChange={(e) => handleFollowGrowthIntervalChange(parseInt(e.target.value) || 60)}
          className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
        />

        <div className="flex items-center justify-between gap-1 flex-wrap pt-1">
          {[15, 30, 45, 60, 90, 120, 180, 240].map((mins) => (
            <button
              key={mins}
              type="button"
              onClick={() => handleFollowGrowthIntervalChange(mins)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition ${
                followGrowthInterval === mins
                  ? "bg-indigo-600 text-white shadow-sm shadow-indigo-600/20"
                  : "bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
              }`}
            >
              {mins === 60 ? "1h (Default)" : mins >= 60 ? `${mins / 60}h` : `${mins}m`}
            </button>
          ))}
        </div>
      </div>

      <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-600 dark:text-slate-400 flex items-start gap-2">
        <Info className="w-4 h-4 text-indigo-500 flex-shrink-0 mt-0.5" />
        <span>
          The automation engine applies ±15% to ±35% random timing jitter to action delays and growth post cycles to guarantee organic, human-like activity patterns.
        </span>
      </div>
    </div>
  );
}
