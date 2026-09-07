import React from "react";
import { Shield } from "lucide-react";
import { RateLimit, Profile } from "@/lib/api";

interface ActionLimitsProps {
  profile: Profile;
  rateLimits: RateLimit[];
  onNavigateToTab: (tab: "limits") => void;
}

export function ActionLimits({ profile, rateLimits, onNavigateToTab }: ActionLimitsProps) {
  const profileLimits = rateLimits.filter(
    (l) => l.profile_id === profile.id || l.profile_slug === profile.profile_slug
  );

  const postLimit = profileLimits.find((l) => l.action_type === "post")?.count_today || 0;
  const replyLimit = profileLimits.find((l) => l.action_type === "reply")?.count_today || 0;
  const likeLimit = profileLimits.find((l) => l.action_type === "like")?.count_today || 0;

  const maxPosts = profile.config?.limits?.max_posts_per_day || profile.config?.max_posts_per_day || 15;
  const maxReplies = profile.config?.limits?.max_replies_per_day || profile.config?.max_replies_per_day || 35;
  const maxLikes = profile.config?.limits?.max_likes_per_day || profile.config?.max_likes_per_day || 50;

  return (
    <div className="p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-3.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Shield className="w-4 h-4 text-indigo-500" />
          <h3 className="font-bold text-xs sm:text-sm text-slate-900 dark:text-white">24h Rate Limit Safety</h3>
        </div>
        <button
          onClick={() => onNavigateToTab("limits")}
          className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:underline"
        >
          Edit Caps
        </button>
      </div>

      <div className="space-y-3">
        {/* Posts */}
        <div>
          <div className="flex items-center justify-between text-xs font-medium mb-1">
            <span className="text-slate-600 dark:text-slate-400">Posts Today</span>
            <span className="font-bold text-slate-900 dark:text-white">
              {postLimit} / {maxPosts}
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: `${Math.min(100, (postLimit / (maxPosts || 1)) * 100)}%` }}
            />
          </div>
        </div>

        {/* Replies */}
        <div>
          <div className="flex items-center justify-between text-xs font-medium mb-1">
            <span className="text-slate-600 dark:text-slate-400">Sniper Replies Today</span>
            <span className="font-bold text-slate-900 dark:text-white">
              {replyLimit} / {maxReplies}
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: `${Math.min(100, (replyLimit / (maxReplies || 1)) * 100)}%` }}
            />
          </div>
        </div>

        {/* Likes */}
        <div>
          <div className="flex items-center justify-between text-xs font-medium mb-1">
            <span className="text-slate-600 dark:text-slate-400">Organic Likes Today</span>
            <span className="font-bold text-slate-900 dark:text-white">
              {likeLimit} / {maxLikes}
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: `${Math.min(100, (likeLimit / (maxLikes || 1)) * 100)}%` }}
            />
          </div>
        </div>
      </div>

      <p className="text-[10px] text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800/80 pt-2.5">
        Anti-ban safety prevents account flagging by strictly enforcing sliding-window rate limits.
      </p>
    </div>
  );
}
