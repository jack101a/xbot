"use client";

import React, { useState, useEffect } from "react";
import { Zap, Flame, StopCircle, RefreshCw, Clock, Quote, CheckCircle2, AlertCircle } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";

interface ActiveCampaign {
  id: string;
  topic: string;
  status: string;
  duration_hours: number;
  interval_minutes: number;
  started_at: string;
  expires_at: string;
  hours_remaining: number;
  actions_executed_count: number;
  unique_seen_tweets_count: number;
  next_run_at: string | null;
}

export function InstantTrendSection({ profileSlug = "test_profile1" }: { profileSlug?: string }) {
  const [topic, setTopic] = useState("");
  const [durationHours, setDurationHours] = useState(48);
  const [intervalMinutes, setIntervalMinutes] = useState(20);
  const [activeCampaigns, setActiveCampaigns] = useState<ActiveCampaign[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const fetchActiveCampaigns = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/trends/instant/active`);
      if (res.ok) {
        const data = await res.json();
        setActiveCampaigns(data);
      }
    } catch (e) {
      console.error("Failed to load active instant campaigns", e);
    }
  };

  useEffect(() => {
    fetchActiveCampaigns();
    const timer = setInterval(fetchActiveCampaigns, 15000);
    return () => clearInterval(timer);
  }, []);

  const handleStartCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    setLoading(true);
    setActionMsg(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/trends/instant/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: topic.trim(),
          profile_slug: profileSlug,
          duration_hours: durationHours,
          interval_minutes: intervalMinutes,
          quote_percentage: 70,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setActionMsg(`Instant campaign launched for '${topic.trim()}'!`);
        setTopic("");
        fetchActiveCampaigns();
      } else {
        setActionMsg(`Error: ${data.detail || "Failed to start"}`);
      }
    } catch (err: any) {
      setActionMsg(`Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStopCampaign = async (id: string, name: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/trends/instant/${id}/stop`, { method: "POST" });
      if (res.ok) {
        setActionMsg(`Campaign '${name}' stopped.`);
        fetchActiveCampaigns();
      }
    } catch (e) {
      console.error("Failed to stop campaign", e);
    }
  };

  return (
    <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
            <Flame className="w-4 h-4 text-amber-500" />
            <span>Instant Trend Growth (X-Only Live Grounding)</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Target breaking trailers or viral events. Researches strictly on X, extracts media, and quotes top engagement tweets every few intervals (up to 48h).
          </p>
        </div>
        <button
          onClick={fetchActiveCampaigns}
          className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition"
          title="Refresh"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {actionMsg && (
        <div className="p-3 rounded-xl bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-800 text-sky-700 dark:text-sky-300 text-xs font-semibold flex items-center justify-between">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg(null)} className="text-slate-400 hover:text-slate-600 dark:hover:text-white">✕</button>
        </div>
      )}

      {/* Launcher Form */}
      <form onSubmit={handleStartCampaign} className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
        <div className="sm:col-span-6 space-y-1">
          <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300">Trending Topic / Event Query</label>
          <input
            type="text"
            placeholder="e.g. Harry Potter series trailer"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="w-full px-3 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
        </div>

        <div className="sm:col-span-2 space-y-1">
          <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300">Duration</label>
          <select
            value={durationHours}
            onChange={(e) => setDurationHours(Number(e.target.value))}
            className="w-full px-2.5 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
          >
            <option value={12}>12 Hours</option>
            <option value={24}>24 Hours</option>
            <option value={48}>48 Hours (Max)</option>
          </select>
        </div>

        <div className="sm:col-span-2 space-y-1">
          <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300">Interval</label>
          <select
            value={intervalMinutes}
            onChange={(e) => setIntervalMinutes(Number(e.target.value))}
            className="w-full px-2.5 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
          >
            <option value={15}>Every 15m</option>
            <option value={20}>Every 20m</option>
            <option value={30}>Every 30m</option>
            <option value={60}>Every 1h</option>
          </select>
        </div>

        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={loading || !topic.trim()}
            className="w-full px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition disabled:opacity-50 shadow-md shadow-amber-600/20"
          >
            {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
            <span>Launch</span>
          </button>
        </div>
      </form>

      {/* Active Campaigns List */}
      {activeCampaigns.length > 0 && (
        <div className="space-y-3 pt-2">
          <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Active Instant Trend Campaigns ({activeCampaigns.length})
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {activeCampaigns.map((c) => (
              <div
                key={c.id}
                className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 space-y-2.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    <span className="font-bold text-xs text-slate-900 dark:text-white truncate max-w-[200px]">{c.topic}</span>
                  </div>
                  <button
                    onClick={() => handleStopCampaign(c.id, c.topic)}
                    className="px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/40 dark:hover:bg-rose-900/60 text-rose-600 dark:text-rose-400 text-[11px] font-bold flex items-center gap-1 transition"
                  >
                    <StopCircle className="w-3 h-3" />
                    <span>Stop</span>
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-100 dark:border-slate-800">
                  <div>
                    <span className="block text-[10px] text-slate-400">Time Left</span>
                    <span className="font-mono font-bold text-amber-600 dark:text-amber-400">{c.hours_remaining}h</span>
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-400">Actions</span>
                    <span className="font-mono font-bold text-sky-600 dark:text-sky-400">{c.actions_executed_count}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-400">Interval</span>
                    <span className="font-mono font-bold text-slate-700 dark:text-slate-200">{c.interval_minutes}m</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
