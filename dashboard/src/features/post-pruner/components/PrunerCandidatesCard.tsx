"use client";

import React, { useState } from "react";
import { EvaluatedPostItem, DeletedPostItem } from "../types";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Trash2,
  ExternalLink,
  ShieldAlert,
  Sparkles,
  Eye,
  Heart,
  MessageSquare,
  Bookmark,
} from "lucide-react";

interface PrunerCandidatesCardProps {
  scannedCount: number;
  candidatePosts: (DeletedPostItem | EvaluatedPostItem)[];
  evaluatedPosts: EvaluatedPostItem[];
  skippedSummary?: {
    too_recent?: number;
    pinned?: number;
    reply?: number;
    retweet?: number;
    passed_metrics?: number;
  };
  onDeleteSingle?: (tweetId: string) => Promise<void>;
  deletingTweetId?: string | null;
  minAgeHours: number;
}

export function PrunerCandidatesCard({
  scannedCount,
  candidatePosts,
  evaluatedPosts,
  skippedSummary,
  onDeleteSingle,
  deletingTweetId,
  minAgeHours,
}: PrunerCandidatesCardProps) {
  const [filterTab, setFilterTab] = useState<"candidates" | "protected" | "all">("candidates");

  const tooRecentCount = skippedSummary?.too_recent ?? 0;
  const passedCount = skippedSummary?.passed_metrics ?? 0;
  const candidatesCount = candidatePosts.length;

  const displayList =
    filterTab === "candidates"
      ? evaluatedPosts.filter(
          (p) => p.status === "candidate" || p.status === "deleted" || p.reason?.toLowerCase().includes("underperforming")
        )
      : filterTab === "protected"
      ? evaluatedPosts.filter((p) => p.status === "too_recent")
      : evaluatedPosts;

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs space-y-4 p-5">
      {/* Header & Stats Overview */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-sky-500" />
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">
              Scan Diagnostics & Candidate Posts
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Evaluated {scannedCount} posts against your engagement criteria. Review candidates or purge selectively.
          </p>
        </div>

        {/* Quick Diagnostic Badges */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="px-2.5 py-1 rounded-full bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 font-semibold border border-rose-200 dark:border-rose-900/40 flex items-center gap-1">
            <Trash2 className="w-3 h-3 text-rose-500" />
            {candidatesCount} Candidates
          </span>
          <span className="px-2.5 py-1 rounded-full bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 font-semibold border border-amber-200 dark:border-amber-900/40 flex items-center gap-1">
            <Clock className="w-3 h-3 text-amber-500" />
            {tooRecentCount} Grace Protected (&lt;{minAgeHours}h)
          </span>
          <span className="px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 font-semibold border border-emerald-200 dark:border-emerald-900/40 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-500" />
            {passedCount} Met Targets
          </span>
        </div>
      </div>

      {/* Helpful Explanatory Banner if 0 Candidates Found */}
      {candidatesCount === 0 && tooRecentCount > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2.5">
          <Clock className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Why were 0 posts pruned?</span> All {tooRecentCount} scanned original posts are newer than your configured {minAgeHours}h grace period. To evaluate and delete newer test posts immediately, select the <span className="font-semibold">&quot;Immediate (0h)&quot;</span> or <span className="font-semibold">&quot;Rapid (6h)&quot;</span> preset above and scan again.
          </div>
        </div>
      )}

      {/* Tab Filter */}
      <div className="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800/60 pb-2">
        <button
          type="button"
          onClick={() => setFilterTab("candidates")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            filterTab === "candidates"
              ? "bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 font-semibold border border-rose-200 dark:border-rose-900/50"
              : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
          }`}
        >
          Candidates ({candidatesCount})
        </button>
        <button
          type="button"
          onClick={() => setFilterTab("protected")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            filterTab === "protected"
              ? "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 font-semibold border border-amber-200 dark:border-amber-900/50"
              : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
          }`}
        >
          Protected by Grace Period ({tooRecentCount})
        </button>
        <button
          type="button"
          onClick={() => setFilterTab("all")}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            filterTab === "all"
              ? "bg-sky-50 dark:bg-sky-950/40 text-sky-700 dark:text-sky-300 font-semibold border border-sky-200 dark:border-sky-900/50"
              : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
          }`}
        >
          All Scanned Posts ({evaluatedPosts.length})
        </button>
      </div>

      {/* List of Posts */}
      <div className="divide-y divide-slate-100 dark:divide-slate-800/60 max-h-[440px] overflow-y-auto pr-1">
        {displayList.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500">
            No posts found matching this view filter.
          </div>
        ) : (
          displayList.map((post) => {
            const isCandidate =
              post.status === "candidate" ||
              post.status === "deleted" ||
              post.reason?.toLowerCase().includes("underperforming");
            const isTooRecent = post.status === "too_recent";
            const isPassed = post.status === "passed_metrics";
            const isDeleted = post.status === "deleted";

            const metrics = post.metrics || {};
            const ageStr = metrics.age_hours !== undefined ? `${metrics.age_hours}h ago` : "Recently";

            return (
              <div
                key={post.tweet_id}
                className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors rounded-lg px-2"
              >
                <div className="space-y-1 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {isDeleted ? (
                      <span className="text-[11px] font-semibold text-rose-600 bg-rose-50 dark:bg-rose-950/40 px-2 py-0.5 rounded flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Deleted
                      </span>
                    ) : isCandidate ? (
                      <span className="text-[11px] font-semibold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 px-2 py-0.5 rounded flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" /> Prune Candidate
                      </span>
                    ) : isTooRecent ? (
                      <span className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-2 py-0.5 rounded flex items-center gap-1">
                        <Clock className="w-3 h-3" /> Grace Protected
                      </span>
                    ) : isPassed ? (
                      <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Met Goals
                      </span>
                    ) : (
                      <span className="text-[11px] font-medium text-slate-500 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                        {post.status}
                      </span>
                    )}

                    <span className="text-[11px] text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {ageStr}
                    </span>
                  </div>

                  <p className="text-xs text-slate-800 dark:text-slate-200 line-clamp-2 font-mono">
                    {post.text || "(No snippet recorded)"}
                  </p>

                  <div className="text-[11px] text-slate-500 dark:text-slate-400">
                    <span className="font-medium text-slate-700 dark:text-slate-300">Verdict:</span>{" "}
                    {post.reason}
                  </div>
                </div>

                {/* Right Column: Metrics & Action */}
                <div className="flex items-center gap-4 shrink-0 sm:border-l sm:border-slate-100 sm:dark:border-slate-800 sm:pl-4">
                  <div className="text-right text-[11px] space-y-0.5">
                    <div className="text-slate-600 dark:text-slate-400 flex items-center gap-1 justify-end">
                      <Eye className="w-3 h-3 text-sky-500" />
                      <span className="font-semibold text-slate-800 dark:text-slate-200">{metrics.views ?? 0}</span>
                    </div>
                    <div className="text-slate-600 dark:text-slate-400 flex items-center gap-2 justify-end">
                      <span className="flex items-center gap-1">
                        <Heart className="w-3 h-3 text-rose-500" />
                        {metrics.likes ?? 0}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare className="w-3 h-3 text-emerald-500" />
                        {metrics.comments ?? 0}
                      </span>
                    </div>
                  </div>

                  {/* Individual Delete Action */}
                  {onDeleteSingle && isCandidate && !isDeleted && (
                    <button
                      type="button"
                      onClick={() => onDeleteSingle(post.tweet_id)}
                      disabled={deletingTweetId === post.tweet_id}
                      className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors disabled:opacity-50"
                      title="Purge this tweet specifically"
                    >
                      {deletingTweetId === post.tweet_id ? (
                        <span className="w-4 h-4 border-2 border-rose-500 border-t-transparent rounded-full animate-spin inline-block" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  )}

                  {post.tweet_url && (
                    <a
                      href={post.tweet_url}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-sky-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                      title="View tweet on X"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
