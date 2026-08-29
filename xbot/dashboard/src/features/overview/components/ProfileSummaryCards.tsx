import React from "react";
import { Layers, Users, Eye, TrendingUp, Flame, CheckCircle2 } from "lucide-react";
import { Profile, Session } from "@/lib/api";

interface ProfileSummaryCardsProps {
  profile: Profile;
  deepAnalytics: any;
  sessions: Session[];
}

export function ProfileSummaryCards({ profile, deepAnalytics, sessions }: ProfileSummaryCardsProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {/* Total Posts / Tweets */}
      <div className="p-3.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Total Posts</span>
          <div className="w-6 h-6 rounded-lg bg-indigo-100 dark:bg-indigo-950 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
            <Layers className="w-3 h-3" />
          </div>
        </div>
        <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-1.5">
          {(deepAnalytics?.rolling_28d?.total_posts ?? profile.posts_count ?? 0).toLocaleString()}
        </div>
        <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 truncate">Live on @{profile.x_handle.replace(/^@+/, '')}</p>
      </div>

      {/* Total Followers */}
      <div className="p-3.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Followers</span>
          <div className="w-6 h-6 rounded-lg bg-sky-100 dark:bg-sky-950 flex items-center justify-center text-sky-600 dark:text-sky-400">
            <Users className="w-3 h-3" />
          </div>
        </div>
        <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-1.5">
          {(profile.followers_count ?? 0).toLocaleString()}
        </div>
        <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Organic audience</p>
      </div>

      {/* Total Following */}
      <div className="p-3.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Following</span>
          <div className="w-6 h-6 rounded-lg bg-violet-100 dark:bg-violet-950 flex items-center justify-center text-violet-600 dark:text-violet-400">
            <Eye className="w-3 h-3" />
          </div>
        </div>
        <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-1.5">
          {(profile.following_count ?? 0).toLocaleString()}
        </div>
        <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Curated accounts</p>
      </div>

      {/* Impressions */}
      <div className="p-3.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Impressions</span>
          <div className="w-6 h-6 rounded-lg bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
            <TrendingUp className="w-3 h-3" />
          </div>
        </div>
        <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-1.5">
          {(deepAnalytics?.rolling_28d?.total_impressions ?? profile.impressions_24h ?? 0).toLocaleString()}
        </div>
        <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Total post views</p>
      </div>

      {/* Engagements */}
      <div className="p-3.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Engagements</span>
          <div className="w-6 h-6 rounded-lg bg-rose-100 dark:bg-rose-950 flex items-center justify-center text-rose-600 dark:text-rose-400">
            <Flame className="w-3 h-3" />
          </div>
        </div>
        <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-1.5">
          {(deepAnalytics?.rolling_28d?.total_engagements ?? profile.engagements_24h ?? 0).toLocaleString()}
        </div>
        <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Likes & reposts</p>
      </div>

      {/* Sessions Completed */}
      <div className="p-3.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Sessions</span>
          <div className="w-6 h-6 rounded-lg bg-amber-100 dark:bg-amber-950 flex items-center justify-center text-amber-600 dark:text-amber-400">
            <CheckCircle2 className="w-3 h-3" />
          </div>
        </div>
        <div className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white mt-1.5">
          {sessions.length.toLocaleString()}
        </div>
        <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Autonomous runs</p>
      </div>
    </div>
  );
}
