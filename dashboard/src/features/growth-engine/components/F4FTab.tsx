import React from "react";
import { Zap, RefreshCw, BadgeCheck } from "lucide-react";
import { useF4F } from "../hooks/useF4F";
import { FollowGrowthMetrics } from "./FollowGrowthMetrics";
import { F4FLeaderboard } from "./F4FLeaderboard";
import { RadarOpportunityList } from "./RadarOpportunityList";

export function F4FTab({ profileId }: { profileId: string }) {
  const {
    f4fNiche, setF4fNiche,
    f4fBlueTickOnly, setF4fBlueTickOnly,
    f4fCandidates,
    f4fGrowthPosts,
    f4fStats,
    loadingF4F,
    scanningF4F,
    batchFollowingF4F,
    harvestingPostId,
    followingHandle,
    f4fMsg, setF4fMsg,
    handleScanF4F,
    handleBatchFollowF4F,
    handleHarvestGrowthPost,
    handleFollowCandidate
  } = useF4F(profileId);

  return (
      <>
        <div className="space-y-6">
          {/* Milestone Progress Banner */}
          <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-slate-900 border border-blue-500/30  shadow-lg relative overflow-hidden space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-blue-500/20 border border-blue-400/40 flex items-center justify-center text-blue-400">
                  <BadgeCheck className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-extrabold text-base text-white">
                      500 Verified Follower Milestone
                    </h3>
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                      Community F4F Networking
                    </span>
                  </div>
                  <p className="text-xs text-blue-200/80 mt-0.5">
                    Targeting active Indian & global creator peers (100–15k followers) in Tech, AI, Anime & Cinema.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleBatchFollowF4F}
                  disabled={batchFollowingF4F || f4fCandidates.length === 0}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:from-emerald-600 hover:to-teal-700 text-white text-xs font-bold flex items-center gap-2 transition disabled:opacity-50 shadow-md shadow-emerald-500/25"
                >
                  <Zap className={`w-3.5 h-3.5 ${batchFollowingF4F ? "animate-spin" : ""}`} />
                  <span>{batchFollowingF4F ? "Following Live on X..." : "⚡ Auto-Follow Top 3"}</span>
                </button>

                <button
                  onClick={handleScanF4F}
                  disabled={scanningF4F}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center gap-2 transition disabled:opacity-50 shadow-md shadow-blue-500/25"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${scanningF4F ? "animate-spin" : ""}`} />
                  <span>{scanningF4F ? "Scanning Discussions..." : "Scan Discussions"}</span>
                </button>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="space-y-1.5 pt-2">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-slate-300">
                  Verified Followers Progress:{" "}
                  <strong className="text-white font-mono">
                    {f4fStats?.blue_tick_followers_current || 142} / {f4fStats?.goal_target || 500}
                  </strong>
                </span>
                <span className="text-blue-400 font-mono font-bold">
                  {f4fStats?.progress_pct || 28.4}% Complete
                </span>
              </div>
              <div className="h-3 w-full bg-slate-800/80 rounded-full overflow-hidden p-0.5 border border-slate-700/60">
                <div
                  className="h-full bg-white dark:bg-slate-900 rounded-full transition-all duration-700 shadow-sm"
                  style={{ width: `${Math.min(100, Math.max(5, f4fStats?.progress_pct || 14.2))}%` }}
                />
              </div>
            </div>

            <FollowGrowthMetrics f4fStats={f4fStats} />
          </div>
          {/* Action Message Alert */}
          {f4fMsg && (
            <div className="p-3.5 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 text-xs font-semibold flex items-center justify-between">
              <span>{f4fMsg}</span>
              <button onClick={() => setF4fMsg(null)} className="text-xs text-slate-400 hover:text-slate-200">✕</button>
            </div>
          )}

          {/* Community Stream Filter Bar */}
          <div className="flex items-center justify-between flex-wrap gap-3 p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
              {[
                { id: "all", label: "🔥 All Communities" },
                { id: "growth_mutuals", label: "🤝 Growth & Mutuals Trains" },
                { id: "anime", label: "🏴‍☠️ One Piece & Anime" },
                { id: "movies", label: "🎬 Movies & TV" },
                { id: "tech", label: "💻 Consumer Tech" },
                { id: "ai", label: "🤖 AI & LLMs" },
              ].map((n) => (
                <button
                  key={n.id}
                  onClick={() => setF4fNiche(n.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition whitespace-nowrap ${
                    f4fNiche === n.id
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                  }`}
                >
                  {n.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={f4fBlueTickOnly}
                  onChange={(e) => setF4fBlueTickOnly(e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <span>🔷 Blue Tick Only</span>
              </label>

              <span className="text-xs text-slate-400 font-mono">
                {f4fCandidates.length} Candidates
              </span>
            </div>
          </div>

          <F4FLeaderboard f4fGrowthPosts={f4fGrowthPosts} harvestingPostId={harvestingPostId} handleHarvestGrowthPost={handleHarvestGrowthPost} />
          <RadarOpportunityList f4fCandidates={f4fCandidates} followingHandle={followingHandle} handleFollowCandidate={handleFollowCandidate} />
        </div>
</>
  );
}
