import React from "react";
import { Zap, StopCircle, Clock, CheckCircle2, Image as ImageIcon, Flame, Calendar, Activity } from "lucide-react";
import { ActiveCampaignSummary } from "../types";

interface ActiveCampaignsSectionProps {
  activeCampaigns: ActiveCampaignSummary[];
  handleStopActiveCampaign: (id: string) => Promise<void>;
  onRefresh?: () => void;
}

export function ActiveCampaignsSection({
  activeCampaigns,
  handleStopActiveCampaign,
  onRefresh,
}: ActiveCampaignsSectionProps) {
  if (activeCampaigns.length === 0) return null;

  return (
    <div className="mb-4 p-4 rounded-xl bg-slate-50/80 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-emerald-500" />
            Active Autonomous Campaigns ({activeCampaigns.length})
          </h3>
        </div>
        <span className="text-[11px] text-slate-400">
          Running in background worker
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {activeCampaigns.map((c) => (
          <div
            key={c.id}
            className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-2.5"
          >
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="font-bold text-xs text-slate-900 dark:text-white truncate max-w-[220px]">
                    {c.topic}
                  </span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded font-mono font-bold bg-sky-100 dark:bg-sky-950 text-sky-700 dark:text-sky-300">
                    {c.duration_hours > 0 ? `${c.duration_hours}h Horizon` : "Sprint"}
                  </span>
                  {c.media_preference === "x_official" && (
                    <span className="text-[9px] px-1.5 py-0.2 rounded font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
                      X Media
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleStopActiveCampaign(c.id)}
                className="px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/50 dark:hover:bg-rose-900/60 text-rose-600 dark:text-rose-400 text-[11px] font-bold flex items-center gap-1 transition flex-shrink-0"
                title="Stop continuous campaign"
              >
                <StopCircle className="w-3.5 h-3.5" />
                <span>Stop</span>
              </button>
            </div>

            <div className="grid grid-cols-3 gap-2 text-[11px] bg-slate-50 dark:bg-slate-950 p-2 rounded-lg border border-slate-100 dark:border-slate-800/60">
              <div>
                <span className="block text-[10px] text-slate-400">Time Left</span>
                <span className="font-mono font-bold text-amber-600 dark:text-amber-400">
                  {c.hours_remaining > 0 ? `${c.hours_remaining}h` : "Final Drop"}
                </span>
              </div>
              <div>
                <span className="block text-[10px] text-slate-400">Actions / Drops</span>
                <span className="font-mono font-bold text-sky-600 dark:text-sky-400">
                  {c.actions_executed_count || 0}
                </span>
              </div>
              <div>
                <span className="block text-[10px] text-slate-400">Cadence</span>
                <span className="font-mono font-bold text-slate-700 dark:text-slate-300">
                  {c.interval_minutes}m
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
