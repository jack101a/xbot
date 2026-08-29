import React from "react";
import { Trophy, RefreshCw, Award, Flame, BarChart3 } from "lucide-react";

interface MonetizationTrackerProps {
  deepAnalytics: any;
  syncingAnalytics: boolean;
  onSyncLiveAnalytics: () => void;
}

export function MonetizationTracker({ deepAnalytics, syncingAnalytics, onSyncLiveAnalytics }: MonetizationTrackerProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      {/* Left Column: Official Creator Studio Milestones */}
      <div className="lg:col-span-7 p-4 rounded-2xl border-2 border-indigo-200/80 dark:border-indigo-800/60 bg-white dark:bg-slate-900 shadow-sm space-y-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-sm">
              <Trophy className="w-3.5 h-3.5" />
            </div>
            <div>
              <h3 className="text-xs sm:text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                Official Creator Studio Monetization
                <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300">
                  Live X Sync
                </span>
              </h3>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">
                Target milestones to qualify for Original Content Rewards on X
              </p>
            </div>
          </div>
          <button
            onClick={onSyncLiveAnalytics}
            disabled={syncingAnalytics}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 shadow-sm transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${syncingAnalytics ? "animate-spin text-indigo-600" : ""}`} />
            <span>{syncingAnalytics ? "Syncing..." : "Sync Live Stats"}</span>
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-0.5">
          {/* Milestone 1 */}
          <div className="p-3 rounded-xl border border-indigo-100 dark:border-indigo-900/60 bg-white/90 dark:bg-slate-900/90 shadow-sm space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Award className="w-3.5 h-3.5 text-blue-500" />
                Verified Followers
              </span>
              <span className="font-bold text-indigo-600 dark:text-indigo-400">
                {(deepAnalytics?.monetization_milestones?.verified_followers?.current ?? 0).toLocaleString()} / 500
              </span>
            </div>
            <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-700"
                style={{ width: `${Math.min(100, Math.max(1, deepAnalytics?.monetization_milestones?.verified_followers?.percentage ?? 0))}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400">
              <span>{deepAnalytics?.monetization_milestones?.verified_followers?.percentage ?? 0}% Complete</span>
              <span>{(deepAnalytics?.monetization_milestones?.verified_followers?.remaining ?? 500).toLocaleString()} remaining</span>
            </div>
          </div>

          {/* Milestone 2 */}
          <div className="p-3 rounded-xl border border-purple-100 dark:border-purple-900/60 bg-white/90 dark:bg-slate-900/90 shadow-sm space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Flame className="w-3.5 h-3.5 text-purple-500" />
                90d Verified Impressions
              </span>
              <span className="font-bold text-purple-600 dark:text-purple-400">
                {(deepAnalytics?.monetization_milestones?.verified_impressions_90d?.current ?? 0).toLocaleString()} / 500K
              </span>
            </div>
            <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-purple-600 h-2 rounded-full transition-all duration-700"
                style={{ width: `${Math.min(100, Math.max(1, deepAnalytics?.monetization_milestones?.verified_impressions_90d?.percentage ?? 0))}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400">
              <span>{deepAnalytics?.monetization_milestones?.verified_impressions_90d?.percentage ?? 0.0}% Complete</span>
              <span>Home Timeline (Excludes replies)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Column: Rolling 28-Day Deep Metrics Overview */}
      <div className="lg:col-span-5 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/70 shadow-sm flex flex-col justify-between space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-sm">
              <BarChart3 className="w-3.5 h-3.5" />
            </div>
            <div>
              <h3 className="text-xs sm:text-sm font-bold text-slate-900 dark:text-white">
                Rolling 28-Day Deep Analytics
              </h3>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">
                Total organic impressions & engagement velocity
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 pt-1 text-center">
          <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/60">
            <span className="text-[9px] font-semibold text-slate-500 dark:text-slate-400 block">28d Impressions</span>
            <span className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white mt-0.5 block">
              {(deepAnalytics?.rolling_28d?.total_impressions || 0).toLocaleString()}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/60">
            <span className="text-[9px] font-semibold text-slate-500 dark:text-slate-400 block">28d Engagements</span>
            <span className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white mt-0.5 block">
              {(deepAnalytics?.rolling_28d?.total_engagements || 0).toLocaleString()}
            </span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/60">
            <span className="text-[9px] font-semibold text-slate-500 dark:text-slate-400 block">Velocity Rate</span>
            <span className="text-sm sm:text-base font-extrabold text-emerald-600 dark:text-emerald-400 mt-0.5 block">
              {deepAnalytics?.rolling_28d?.engagement_rate || 0.0}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
