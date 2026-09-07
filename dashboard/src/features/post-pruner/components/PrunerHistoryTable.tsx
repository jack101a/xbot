"use client";

import React from "react";
import { PrunerHistoryItem } from "../types";
import { Trash2, ExternalLink, Calendar, CheckCircle2 } from "lucide-react";

interface PrunerHistoryTableProps {
  history: PrunerHistoryItem[];
  loading: boolean;
}

export function PrunerHistoryTable({ history, loading }: PrunerHistoryTableProps) {
  if (loading) {
    return (
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 text-center">
        <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        <p className="text-xs text-slate-500">Loading pruning history...</p>
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8 text-center">
        <Trash2 className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">No Posts Pruned Yet</h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
          When you execute cleanup runs, the history of deleted tweets with their metric reasons will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800/80 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Deletion History & Audit Log</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Log of tweets deleted from your X profile with the corresponding metrics.
          </p>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-medium">
          {history.length} Total Deleted
        </span>
      </div>

      <div className="divide-y divide-slate-100 dark:divide-slate-800/60 overflow-x-auto">
        {history.map((item) => {
          const metrics = item.result?.metrics || {};
          const reason = item.result?.reason || "Underperforming threshold";
          const dateStr = item.executed_at ? new Date(item.executed_at).toLocaleString() : "Recently";

          return (
            <div key={item.id} className="p-4 hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-1.5 flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 px-2 py-0.5 rounded">
                    <CheckCircle2 className="w-3 h-3" />
                    Deleted
                  </span>
                  <span className="text-[11px] text-slate-400 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {dateStr}
                  </span>
                </div>

                <p className="text-xs text-slate-800 dark:text-slate-200 line-clamp-2 font-mono">
                  {item.content || "(No snippet recorded)"}
                </p>

                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  <span className="font-medium text-slate-700 dark:text-slate-300">Reason:</span> {reason}
                </div>
              </div>

              <div className="flex items-center gap-4 shrink-0 sm:border-l sm:border-slate-100 sm:dark:border-slate-800 sm:pl-4">
                <div className="text-right text-[11px] space-y-0.5">
                  <div className="text-slate-600 dark:text-slate-400">
                    Views: <span className="font-semibold text-slate-800 dark:text-slate-200">{metrics.views ?? 0}</span>
                  </div>
                  <div className="text-slate-600 dark:text-slate-400">
                    Likes: <span className="font-semibold text-slate-800 dark:text-slate-200">{metrics.likes ?? 0}</span> • Replies: <span className="font-semibold text-slate-800 dark:text-slate-200">{metrics.comments ?? 0}</span>
                  </div>
                </div>

                {item.target_url && (
                  <a
                    href={item.target_url}
                    target="_blank"
                    rel="noreferrer"
                    className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                    title="View Target URL"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
