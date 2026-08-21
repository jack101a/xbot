"use client";

import React, { useState, useEffect } from "react";
import {
  Sliders,
  ShieldCheck,
  Clock,
  Zap,
  Save,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Info,
  Calendar
} from "lucide-react";
import { Profile, api } from "@/lib/api";

interface LimitsSchedulerTabProps {
  profileId: string;
  selectedProfile: Profile;
  onRefresh: () => void;
}

export function LimitsSchedulerTab({
  profileId,
  selectedProfile,
  onRefresh
}: LimitsSchedulerTabProps) {
  const [config, setConfig] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    async function loadConfig() {
      if (!profileId) return;
      setLoading(true);
      try {
        const c = await api.getProfileConfig(profileId);
        setConfig(c || {});
      } catch (err: any) {
        console.error("Failed to load profile config", err);
      } finally {
        setLoading(false);
      }
    }
    loadConfig();
  }, [profileId]);

  const handleSave = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await api.updateProfileConfig(profileId, config);
      setMsg({ type: "success", text: "Rate limits and scheduling configuration saved successfully!" });
      onRefresh();
    } catch (err: any) {
      setMsg({ type: "error", text: err.message || "Failed to save config." });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Sliders className="w-5 h-5 text-indigo-500" />
            <span>Limits & Automation Safety</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Configure anti-ban sliding-window rate limits, randomized jitter cooldowns, active operating hours, and warm-up pacing.
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-600/20 transition disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          <span>{saving ? "Saving..." : "Save Configuration"}</span>
        </button>
      </div>

      {/* Alert Banner */}
      {msg && (
        <div
          className={`p-4 rounded-xl flex items-center justify-between border ${
            msg.type === "success"
              ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
              : "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300"
          }`}
        >
          <div className="flex items-center gap-3">
            {msg.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
            )}
            <span className="text-sm font-medium">{msg.text}</span>
          </div>
          <button onClick={() => setMsg(null)} className="text-xs font-semibold underline hover:opacity-75">
            Dismiss
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Card 1: Action Rate Limits */}
        <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-indigo-500" />
            <h3 className="font-bold text-sm text-slate-900 dark:text-white">Daily & Hourly Action Caps</h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Hard sliding-window limits enforced in Redis. If a cap is reached, the bot automatically stops that action type.
          </p>

          <div className="space-y-4 pt-2">
            <div>
              <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                <span>Max Posts / Day</span>
                <span className="text-indigo-600 dark:text-indigo-400 font-bold">
                  {config.max_posts_per_day ?? 15}
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="50"
                value={config.max_posts_per_day ?? 15}
                onChange={(e) => setConfig({ ...config, max_posts_per_day: parseInt(e.target.value) })}
                className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                <span>Max Sniper Replies / Day</span>
                <span className="text-indigo-600 dark:text-indigo-400 font-bold">
                  {config.max_replies_per_day ?? 35}
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="100"
                value={config.max_replies_per_day ?? 35}
                onChange={(e) => setConfig({ ...config, max_replies_per_day: parseInt(e.target.value) })}
                className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                <span>Max Organic Likes / Day</span>
                <span className="text-indigo-600 dark:text-indigo-400 font-bold">
                  {config.max_likes_per_day ?? 50}
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="150"
                value={config.max_likes_per_day ?? 50}
                onChange={(e) => setConfig({ ...config, max_likes_per_day: parseInt(e.target.value) })}
                className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                <span>Max Retweets / Day</span>
                <span className="text-indigo-600 dark:text-indigo-400 font-bold">
                  {config.max_retweets_per_day ?? 10}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="30"
                value={config.max_retweets_per_day ?? 10}
                onChange={(e) => setConfig({ ...config, max_retweets_per_day: parseInt(e.target.value) })}
                className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
            </div>
          </div>
        </div>

        {/* Card 2: Operating Schedule & Cooldowns */}
        <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-500" />
            <h3 className="font-bold text-sm text-slate-900 dark:text-white">Schedule & Stealth Delays</h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Configure human-like operating hours and randomized jitter pauses between browser actions.
          </p>

          <div className="grid grid-cols-2 gap-4 pt-2">
            <div>
              <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
                Active Hours Start
              </label>
              <input
                type="number"
                min="0"
                max="23"
                value={config.active_hours_start ?? 8}
                onChange={(e) => setConfig({ ...config, active_hours_start: parseInt(e.target.value) })}
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
                value={config.active_hours_end ?? 23}
                onChange={(e) => setConfig({ ...config, active_hours_end: parseInt(e.target.value) })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-semibold text-slate-900 dark:text-white"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">e.g. 23 (11:00 PM)</span>
            </div>
          </div>

          <div className="pt-2">
            <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              <span>Cooldown Delay Between Actions (Seconds)</span>
              <span className="text-indigo-600 dark:text-indigo-400 font-bold">
                {config.action_delay_seconds ?? 30}s
              </span>
            </div>
            <input
              type="range"
              min="10"
              max="120"
              value={config.action_delay_seconds ?? 30}
              onChange={(e) => setConfig({ ...config, action_delay_seconds: parseInt(e.target.value) })}
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
      </div>
    </div>
  );
}
