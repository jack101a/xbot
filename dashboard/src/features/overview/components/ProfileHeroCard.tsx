import React from "react";
import { ExternalLink, RefreshCw, Pause, Play, Zap } from "lucide-react";
import { Profile } from "@/lib/api";

interface ProfileHeroCardProps {
  profile: Profile;
  syncing: boolean;
  triggering: boolean;
  onSyncFromX: () => void;
  onTogglePause: () => void;
  onRunSession: () => void;
}

export function ProfileHeroCard({
  profile,
  syncing,
  triggering,
  onSyncFromX,
  onTogglePause,
  onRunSession
}: ProfileHeroCardProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm h-full flex flex-col justify-between gap-3.5">
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3.5">
        <div className="w-13 h-13 sm:w-14 sm:h-14 rounded-2xl bg-blue-600 overflow-hidden flex-shrink-0 flex items-center justify-center text-white text-lg sm:text-xl font-bold border-2 border-white dark:border-slate-800 shadow-md">
          {profile.avatar_url || profile.avatar ? (
            <img src={profile.avatar_url || profile.avatar} alt="" className="w-full h-full object-cover" />
          ) : (
            profile.display_name.charAt(0).toUpperCase()
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-base sm:text-xl font-bold text-slate-900 dark:text-white tracking-tight truncate">
              {profile.display_name}
            </h1>
            <a
              href={`https://x.com/${profile.x_handle.replace(/^@/, "")}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs sm:text-sm font-semibold text-sky-600 dark:text-sky-400 hover:underline"
            >
              <span>@{profile.x_handle.replace(/^@/, "")}</span>
              <ExternalLink className="w-3 h-3" />
            </a>
            <span
              className={`text-[10px] sm:text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${
                profile.status === "active"
                  ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                  : "bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
              }`}
            >
              {profile.status}
            </span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 line-clamp-2">
            {profile.persona_summary?.identity?.background ||
              profile.persona_summary?.bio ||
              "Autonomous AI creator voice configured for organic audience growth."}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100 dark:border-slate-800/80">
        <button
          onClick={onSyncFromX}
          disabled={syncing}
          className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-750 transition shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`} />
          <span>{syncing ? "Syncing..." : "Sync from X"}</span>
        </button>

        <button
          onClick={onTogglePause}
          className={`flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border transition shadow-sm ${
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
          onClick={onRunSession}
          disabled={triggering}
          className="w-full sm:w-auto sm:ml-auto flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition disabled:opacity-50"
        >
          <Zap className={`w-3.5 h-3.5 ${triggering ? "animate-bounce" : ""}`} />
          <span>{triggering ? "Queuing..." : "Run Session Now"}</span>
        </button>
      </div>
    </div>
  );
}
