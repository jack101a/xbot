import React from "react";
import { Layers, Eye, Flame, RefreshCw } from "lucide-react";
import { Profile } from "@/lib/api";

interface LivePostsLogProps {
  profile: Profile;
}

export function LivePostsLog({ profile }: LivePostsLogProps) {
  if (!profile.recent_tweets || profile.recent_tweets.length === 0) return null;

  return (
    <div className="lg:col-span-3 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Layers className="w-4 h-4 text-indigo-500" />
          <h3 className="font-bold text-xs sm:text-sm text-slate-900 dark:text-white">Live Profile Posts & Engagement</h3>
        </div>
        <span className="text-[11px] text-slate-400 font-medium">
          Synced from X (@{profile.x_handle.replace(/^@+/, '')})
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {profile.recent_tweets.slice(0, 6).map((tw, idx) => (
          <div
            key={idx}
            className="p-3 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-slate-50/60 dark:bg-slate-800/40 flex flex-col justify-between space-y-2.5"
          >
            <p className="text-xs text-slate-800 dark:text-slate-200 line-clamp-3 leading-relaxed">
              "{tw.body}"
            </p>
            <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 border-t border-slate-200/60 dark:border-slate-700/50 pt-1.5">
              <span className="flex items-center gap-1">
                <Eye className="w-3 h-3 text-sky-500" /> {tw.views || 0}
              </span>
              <span className="flex items-center gap-1">
                <Flame className="w-3 h-3 text-rose-500" /> {tw.likes || 0}
              </span>
              <span className="flex items-center gap-1">
                <RefreshCw className="w-3 h-3 text-emerald-500" /> {tw.retweets || 0}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
