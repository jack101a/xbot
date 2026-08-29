import React from "react";
import { 
  Crosshair, Sparkles, TrendingUp, Vote, Plus, Trash2, 
  RefreshCw, CheckCircle, AlertCircle, ExternalLink, Send, 
  Zap, Layers, ArrowRight, HelpCircle, Check, BadgeCheck, 
  UserCheck, Users, Search 
} from "lucide-react";
import { useTrends } from "../hooks/useTrends";

export function TrendsTab({ profileId }: { profileId: string }) {
  const {
    trendsList,
    trendDrafts,
    loadingTrends,
    publishingTrendTake,
    trendMsg,
    handleScanTrends,
    handlePublishTrendTake
  } = useTrends(profileId);

  return (
      <>
        <div className="space-y-6">
          <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-sky-500" />
                  <span>Real-Time Trend Radar & Strategic Commentary</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">Monitors live tech news & RSS feeds, scores alignment to your persona, and drafts timely commentary takes.</p>
              </div>
              <button
                onClick={handleScanTrends}
                disabled={loadingTrends}
                className="w-full sm:w-auto px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-md shadow-sky-600/20"
              >
                <RefreshCw className={`w-4 h-4 ${loadingTrends ? "animate-spin" : ""}`} />
                <span>Scan Live Trends</span>
              </button>
            </div>

            {trendMsg && (
              <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-semibold">
                {trendMsg}
              </div>
            )}

            {/* Trends List */}
            {trendsList.length > 0 && (
              <div className="space-y-4 pt-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Live Trend Pipeline & AI Takes
                </h4>

                <div className="space-y-3">
                  {trendsList.map((trend, i) => {
                    const draft = trendDrafts[i];
                    return (
                      <div
                        key={i}
                        className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 space-y-3"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-xs text-slate-900 dark:text-white">
                              {trend.title}
                            </span>
                            <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-sky-100 dark:bg-sky-950 text-sky-700 dark:text-sky-400">
                              {trend.alignment_score}% match
                            </span>
                          </div>
                          <span className="text-[11px] text-slate-400 capitalize">{trend.category}</span>
                        </div>

                        {draft && (
                          <div className="p-3 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                              <span className="text-[11px] font-bold text-sky-600 dark:text-sky-400 uppercase">
                                Generated Take ({draft.angle})
                              </span>
                              <button
                                onClick={() => handlePublishTrendTake(i, draft.post_text)}
                                disabled={publishingTrendTake === i}
                                className="w-full sm:w-auto px-3 py-1 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-1 transition disabled:opacity-50"
                              >
                                {publishingTrendTake === i ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                                <span>Publish Take</span>
                              </button>
                            </div>
                            <p className="text-xs text-slate-800 dark:text-slate-200 font-mono whitespace-pre-wrap">
                              {draft.post_text}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
</>
  );
}
