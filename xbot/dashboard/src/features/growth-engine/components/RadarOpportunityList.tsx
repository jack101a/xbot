import React from "react";
import { BadgeCheck, ExternalLink, Check, RefreshCw, UserCheck } from "lucide-react";

export function RadarOpportunityList({
  f4fCandidates,
  followingHandle,
  handleFollowCandidate
}: {
  f4fCandidates: any[];
  followingHandle: string | null;
  handleFollowCandidate: (handle: string, isBlueTick: boolean, niche: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
      {f4fCandidates.map((cand) => (
        <div key={cand.id} className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col justify-between space-y-3 hover:border-blue-400/60 dark:hover:border-blue-500/60 transition group">
          <div className="space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-xs text-slate-900 dark:text-white truncate max-w-[150px]">
                  {cand.name}
                </span>
                {cand.is_blue_tick && <BadgeCheck className="w-4 h-4 text-blue-500 flex-shrink-0" />}
              </div>
              <span className="text-[11px] text-slate-500 font-mono">@{cand.handle}</span>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
              {cand.match_reason}
            </span>
            <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2 leading-relaxed">
              {cand.bio}
            </p>
            <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-1">
              <span>{cand.followers_count?.toLocaleString() || 0} followers</span>
              <span>{cand.following_count?.toLocaleString() || 0} following</span>
            </div>
          </div>
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <a href={`https://x.com/${cand.handle}`} target="_blank" rel="noopener noreferrer" className="text-[11px] text-slate-500 hover:text-blue-500 flex items-center gap-1 font-semibold">
              View <ExternalLink className="w-3 h-3" />
            </a>
            {cand.status === "followed" ? (
              <span className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-500 text-xs font-bold flex items-center gap-1">
                <Check className="w-3.5 h-3.5 text-emerald-500" />
                Followed
              </span>
            ) : (
              <button onClick={() => handleFollowCandidate(cand.handle, cand.is_blue_tick, "all")} disabled={followingHandle === cand.handle} className="px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center gap-1.5 transition disabled:opacity-50 shadow-sm shadow-blue-500/20">
                {followingHandle === cand.handle ? <RefreshCw className="w-3 h-3 animate-spin" /> : <UserCheck className="w-3 h-3" />}
                <span>{followingHandle === cand.handle ? "Following..." : "Follow on Live X"}</span>
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
