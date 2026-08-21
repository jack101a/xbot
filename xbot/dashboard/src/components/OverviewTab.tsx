"use client";

import React, { useState } from "react";
import {
  Play,
  RefreshCw,
  Pause,
  CheckCircle2,
  AlertCircle,
  Clock,
  TrendingUp,
  Users,
  Eye,
  Brain,
  ExternalLink,
  Shield,
  Zap,
  ArrowRight,
  Flame
} from "lucide-react";
import { Profile, Session, RateLimit, api } from "@/lib/api";

interface OverviewTabProps {
  profile: Profile;
  sessions: Session[];
  rateLimits: RateLimit[];
  onRefresh: () => void;
  onNavigateToTab: (tab: "growth" | "activity" | "persona" | "limits") => void;
  onSelectSession?: (sessionId: string) => void;
}

export function OverviewTab({
  profile,
  sessions,
  rateLimits,
  onRefresh,
  onNavigateToTab,
  onSelectSession
}: OverviewTabProps) {
  const [triggering, setTriggering] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [actionMsg, setActionMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleRunSession = async () => {
    setTriggering(true);
    setActionMsg(null);
    try {
      const res = await api.triggerProfileSession(profile.id);
      setActionMsg({ type: "success", text: "Autonomous session queued! Check Live Activity tab to watch in real-time." });
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to trigger session." });
    } finally {
      setTriggering(false);
    }
  };

  const handleSyncFromX = async () => {
    setSyncing(true);
    setActionMsg(null);
    try {
      const res = await api.syncProfileFromX(profile.id);
      setActionMsg({ type: "success", text: "Profile stats and recent tweets synchronized from X!" });
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to sync profile from X." });
    } finally {
      setSyncing(false);
    }
  };

  const handleTogglePause = async () => {
    setActionMsg(null);
    try {
      if (profile.status === "active") {
        await api.pauseProfile(profile.id);
        setActionMsg({ type: "success", text: "Profile automation paused." });
      } else {
        await api.resumeProfile(profile.id);
        setActionMsg({ type: "success", text: "Profile automation resumed." });
      }
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to update status." });
    }
  };

  // Find rate limit stats for this profile
  const profileLimits = rateLimits.filter(
    (l) => l.profile_id === profile.id || l.profile_slug === profile.profile_slug
  );

  const postLimit = profileLimits.find((l) => l.action_type === "post")?.count_today || 0;
  const replyLimit = profileLimits.find((l) => l.action_type === "reply")?.count_today || 0;
  const likeLimit = profileLimits.find((l) => l.action_type === "like")?.count_today || 0;

  const maxPosts = profile.config?.max_posts_per_day || 15;
  const maxReplies = profile.config?.max_replies_per_day || 35;
  const maxLikes = profile.config?.max_likes_per_day || 50;

  return (
    <div className="space-y-6">
      {/* Alert Banner */}
      {actionMsg && (
        <div
          className={`p-4 rounded-xl flex items-center justify-between border ${
            actionMsg.type === "success"
              ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
              : "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300"
          }`}
        >
          <div className="flex items-center gap-3">
            {actionMsg.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
            )}
            <span className="text-sm font-medium">{actionMsg.text}</span>
          </div>
          <button
            onClick={() => setActionMsg(null)}
            className="text-xs font-semibold underline hover:opacity-75"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Hero Profile Card */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-gradient-to-br from-white via-indigo-50/30 to-purple-50/20 dark:from-slate-900 dark:via-slate-900/90 dark:to-indigo-950/30 p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="flex items-start sm:items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-500 to-violet-600 overflow-hidden flex-shrink-0 flex items-center justify-center text-white text-2xl font-bold border-2 border-white dark:border-slate-800 shadow-md">
              {profile.avatar_url || profile.avatar ? (
                <img src={profile.avatar_url || profile.avatar} alt="" className="w-full h-full object-cover" />
              ) : (
                profile.display_name.charAt(0).toUpperCase()
              )}
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
                  {profile.display_name}
                </h1>
                <a
                  href={`https://x.com/${profile.x_handle.replace(/^@/, "")}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-sm font-semibold text-sky-600 dark:text-sky-400 hover:underline"
                >
                  <span>@{profile.x_handle.replace(/^@/, "")}</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
                <span
                  className={`text-xs font-semibold px-2.5 py-0.5 rounded-full capitalize ${
                    profile.status === "active"
                      ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                      : "bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
                  }`}
                >
                  {profile.status}
                </span>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-300 mt-1 line-clamp-2 max-w-xl">
                {profile.persona_summary?.identity?.background ||
                  profile.persona_summary?.bio ||
                  "Autonomous AI creator voice configured for organic audience growth."}
              </p>
            </div>
          </div>

          {/* Quick Trigger CTAs */}
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={handleSyncFromX}
              disabled={syncing}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-750 transition shadow-sm disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`} />
              <span>{syncing ? "Syncing..." : "Sync from X"}</span>
            </button>

            <button
              onClick={handleTogglePause}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold border transition shadow-sm ${
                profile.status === "active"
                  ? "border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 hover:bg-amber-100/60"
                  : "border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100/60"
              }`}
            >
              {profile.status === "active" ? (
                <>
                  <Pause className="w-3.5 h-3.5" />
                  <span>Pause Bot</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5" />
                  <span>Resume Bot</span>
                </>
              )}
            </button>

            <button
              onClick={handleRunSession}
              disabled={triggering}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white shadow-lg shadow-indigo-500/25 transition disabled:opacity-50"
            >
              <Zap className={`w-4 h-4 ${triggering ? "animate-bounce" : ""}`} />
              <span>{triggering ? "Queuing Session..." : "Run Session Now"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Total Followers</span>
            <div className="w-8 h-8 rounded-xl bg-sky-100 dark:bg-sky-950 flex items-center justify-center text-sky-600 dark:text-sky-400">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {(profile.followers_count || 0).toLocaleString()}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Live from profile snapshot</p>
        </div>

        <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Total Following</span>
            <div className="w-8 h-8 rounded-xl bg-indigo-100 dark:bg-indigo-950 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <Eye className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {(profile.following_count || 0).toLocaleString()}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Curated niche accounts</p>
        </div>

        <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Target KOLs</span>
            <div className="w-8 h-8 rounded-xl bg-amber-100 dark:bg-amber-950 flex items-center justify-center text-amber-600 dark:text-amber-400">
              <Flame className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {profile.persona_summary?.target_kols?.length || 0}
          </div>
          <button
            onClick={() => onNavigateToTab("growth")}
            className="text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 mt-1"
          >
            <span>Manage Targets</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Sessions Completed</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {sessions.filter((s) => s.status === "completed").length}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">Autonomous growth runs</p>
        </div>
      </div>

      {/* Grid: 24h Action Limits & Recent Sessions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 24-Hour Limits Progress */}
        <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-indigo-500" />
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">24h Rate Limit Safety</h3>
            </div>
            <button
              onClick={() => onNavigateToTab("limits")}
              className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:underline"
            >
              Edit Caps
            </button>
          </div>

          <div className="space-y-4">
            {/* Posts */}
            <div>
              <div className="flex items-center justify-between text-xs font-medium mb-1.5">
                <span className="text-slate-600 dark:text-slate-400">Posts Today</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {postLimit} / {maxPosts}
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-violet-500 to-indigo-600 transition-all duration-300"
                  style={{ width: `${Math.min(100, (postLimit / (maxPosts || 1)) * 100)}%` }}
                />
              </div>
            </div>

            {/* Replies */}
            <div>
              <div className="flex items-center justify-between text-xs font-medium mb-1.5">
                <span className="text-slate-600 dark:text-slate-400">Sniper Replies Today</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {replyLimit} / {maxReplies}
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-sky-500 to-indigo-600 transition-all duration-300"
                  style={{ width: `${Math.min(100, (replyLimit / (maxReplies || 1)) * 100)}%` }}
                />
              </div>
            </div>

            {/* Likes */}
            <div>
              <div className="flex items-center justify-between text-xs font-medium mb-1.5">
                <span className="text-slate-600 dark:text-slate-400">Organic Likes Today</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {likeLimit} / {maxLikes}
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-rose-500 to-pink-600 transition-all duration-300"
                  style={{ width: `${Math.min(100, (likeLimit / (maxLikes || 1)) * 100)}%` }}
                />
              </div>
            </div>
          </div>

          <p className="text-[11px] text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800/80 pt-3">
            Anti-ban safety prevents account flagging by strictly enforcing sliding-window rate limits.
          </p>
        </div>

        {/* Recent Execution Sessions */}
        <div className="lg:col-span-2 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-500" />
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">Recent Automation Sessions</h3>
            </div>
            <button
              onClick={() => onNavigateToTab("activity")}
              className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:underline flex items-center gap-1"
            >
              <span>Live Terminal</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {sessions.length > 0 ? (
            <div className="divide-y divide-slate-100 dark:divide-slate-800/80">
              {sessions.slice(0, 5).map((s) => (
                <div
                  key={s.id}
                  onClick={() => {
                    if (onSelectSession) onSelectSession(s.id);
                    onNavigateToTab("activity");
                  }}
                  className="py-3 flex items-center justify-between gap-4 hover:bg-slate-50/50 dark:hover:bg-slate-800/30 px-2 rounded-xl transition cursor-pointer group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                        s.status === "completed"
                          ? "bg-emerald-500"
                          : s.status === "running"
                          ? "bg-sky-500 animate-ping"
                          : s.status === "failed"
                          ? "bg-rose-500"
                          : "bg-amber-500"
                      }`}
                    />
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate flex items-center gap-2">
                        <span>Session {s.id.slice(0, 8)}...</span>
                        <span
                          className={`text-[10px] uppercase font-bold px-1.5 py-0.2 rounded capitalize ${
                            s.status === "completed"
                              ? "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400"
                              : s.status === "running"
                              ? "bg-sky-100 dark:bg-sky-950/60 text-sky-700 dark:text-sky-400"
                              : "bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400"
                          }`}
                        >
                          {s.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        {new Date(s.started_at).toLocaleString()} &bull; {s.actions_completed || 0} /{" "}
                        {s.actions_planned || 0} actions completed
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 transition group-hover:translate-x-0.5 flex-shrink-0" />
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-slate-500 text-xs">
              No recent sessions recorded yet. Click "Run Session Now" to start!
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
