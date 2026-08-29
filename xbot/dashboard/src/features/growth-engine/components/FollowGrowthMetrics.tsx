import React from "react";
import { F4FStats } from "../types";

export function FollowGrowthMetrics({ f4fStats }: { f4fStats: F4FStats | null }) {
  return (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Total Followed</span>
                <p className="text-base font-bold text-white font-mono">{f4fStats?.total_followed_all_time || 0}</p>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-[10px] font-medium text-blue-300 uppercase tracking-wider">Blue Tick Ratio</span>
                <p className="text-base font-bold text-blue-400 font-mono">
                  {f4fStats?.blue_tick_ratio_pct || 90.0}%
                </p>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-[10px] font-medium text-emerald-300 uppercase tracking-wider">Reciprocity Rate</span>
                <p className="text-base font-bold text-emerald-400 font-mono">{f4fStats?.reciprocity_rate_pct || 45.0}%</p>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-[10px] font-medium text-amber-300 uppercase tracking-wider">Grace Period Active</span>
                <p className="text-base font-bold text-amber-400 font-mono">{f4fStats?.active_grace_period_count || 0} peers</p>
              </div>
            </div>
  );
}
