"use client";

import React, { useState, useEffect } from "react";
import { useAppStore } from "@/store/useAppStore";
import { api } from "@/lib/api";
import { PrunerCriteria, PrunerHistoryItem } from "./types";
import { PrunerFilterCard } from "./components/PrunerFilterCard";
import { PrunerHistoryTable } from "./components/PrunerHistoryTable";
import { Trash2, AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react";

export function PostPrunerTab() {
  const { selectedProfileId, appendActivityLog } = useAppStore();

  const [criteria, setCriteria] = useState<PrunerCriteria>({
    min_views: 200,
    min_likes: 5,
    min_comments: 2,
    min_age_hours: 24,
    max_posts_to_delete: 10,
    match_mode: "all",
  });

  const [isRunning, setIsRunning] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [history, setHistory] = useState<PrunerHistoryItem[]>([]);
  const [lastResult, setLastResult] = useState<any | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchHistory = async () => {
    if (!selectedProfileId) return;
    setLoadingHistory(true);
    try {
      const res = await api.getPostPrunerHistory(selectedProfileId, 50);
      setHistory(res.history || []);
    } catch (err) {
      console.error("Failed to load pruner history:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [selectedProfileId]);

  const handleRunPruner = async () => {
    if (!selectedProfileId) return;
    setIsRunning(true);
    setLastResult(null);
    setErrorMessage(null);
    appendActivityLog("Starting profile post pruner cleanup...", "info");

    try {
      const result = await api.runPostPruner(selectedProfileId, criteria);
      setLastResult(result);
      appendActivityLog(
        `Pruner finished: Scanned ${result.scanned_count} posts, pruned ${result.deleted_count} underperforming posts.`,
        "success"
      );
      await fetchHistory();
    } catch (err: any) {
      console.error("Failed to run post pruner:", err);
      const msg = err.message || String(err);
      setErrorMessage(msg);
      appendActivityLog(`Post pruner failed: ${msg}`, "error");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Trash2 className="w-6 h-6 text-rose-500" />
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Profile Post Pruner</h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Safely purge underperforming original tweets on your profile to maintain high engagement velocity and clean account health.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchHistory}
          disabled={loadingHistory || !selectedProfileId}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors shrink-0 self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? "animate-spin" : ""}`} />
          Refresh History
        </button>
      </div>

      {/* Error Alert Banner */}
      {errorMessage && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 flex items-start justify-between gap-3 text-xs text-rose-700 dark:text-rose-300">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Pruner Error:</span> {errorMessage}
            </div>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            className="text-rose-500 hover:text-rose-700 font-bold ml-2 text-sm leading-none"
          >
            ✕
          </button>
        </div>
      )}

      {/* Safety Notice Banner */}
      <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-start gap-3 text-xs text-amber-800 dark:text-amber-300">
        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold">Safety Isolation:</span> The pruner operates exclusively on your profile&apos;s main original tweets. Replies, thread comments, and quote tweets will never be deleted. Posts newer than your configured grace period ({criteria.min_age_hours}h) are strictly protected.
        </div>
      </div>

      {/* Last Result Banner */}
      {lastResult && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 flex items-center justify-between gap-3 text-xs text-emerald-800 dark:text-emerald-300">
          <div className="flex items-center gap-2 font-medium">
            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
            Cleanup Complete: Scanned {lastResult.scanned_count} posts • Deleted {lastResult.deleted_count} underperforming posts
          </div>
        </div>
      )}

      {/* Filter & Run Card */}
      <PrunerFilterCard
        criteria={criteria}
        setCriteria={setCriteria}
        onRun={handleRunPruner}
        isRunning={isRunning}
        disabled={!selectedProfileId}
      />

      {/* Deletion History Table */}
      <PrunerHistoryTable history={history} loading={loadingHistory} />
    </div>
  );
}
