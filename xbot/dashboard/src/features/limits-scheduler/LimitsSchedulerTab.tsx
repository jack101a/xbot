"use client";

import React, { useState, useEffect } from "react";
import { Sliders, Save, CheckCircle2, AlertCircle } from "lucide-react";
import { Profile, api } from "@/lib/api";
import { DailyLimitsEditor } from "./components/DailyLimitsEditor";
import { CircadianScheduleEditor } from "./components/CircadianScheduleEditor";

interface LimitsSchedulerTabProps {
  profileId: string;
  selectedProfile: Profile;
  onRefresh: () => void;
}

export function LimitsSchedulerTab({
  profileId,
  selectedProfile: _selectedProfile,
  onRefresh,
}: LimitsSchedulerTabProps) {
  const [config, setConfig] = useState<any>({});
  const [, setLoading] = useState(false);
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
          <h2 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
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
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-600/20 transition disabled:opacity-50"
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <DailyLimitsEditor config={config} setConfig={setConfig} />
        <CircadianScheduleEditor config={config} setConfig={setConfig} />
      </div>
    </div>
  );
}
