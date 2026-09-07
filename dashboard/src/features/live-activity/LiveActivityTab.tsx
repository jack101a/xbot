"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Activity, CheckCircle2, Clock, Loader2, Zap, Radio, RotateCcw } from "lucide-react";
import { api, Profile, Session } from "@/lib/api";
import { ActivityTimelineView } from "./components/ActivityTimelineView";
import { LiveFeed } from "./components/LiveFeed";
import { SessionCard } from "./components/SessionCard";

export function LiveActivityTab({
  profileId,
  selectedProfile: _selectedProfile,
  initialSessionId,
  onTriggerSession,
  triggeringSession = false,
  activeView,
  onViewChange,
}: {
  profileId: string;
  selectedProfile?: Profile;
  initialSessionId?: string;
  onTriggerSession?: () => void;
  triggeringSession?: boolean;
  activeView?: "timeline" | "stream" | "history";
  onViewChange?: (view: "timeline" | "stream" | "history") => void;
}) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [internalView, setInternalView] = useState<"timeline" | "stream" | "history">(
    initialSessionId ? "history" : "timeline"
  );
  const liveView = activeView || internalView;
  const setLiveView = (view: "timeline" | "stream" | "history") => {
    setInternalView(view);
    onViewChange?.(view);
  };
  const [refreshing, setRefreshing] = useState(false);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await api.getProfileSessions(profileId, 20);
      setSessions(data);
    } catch {}
    finally { setLoadingSessions(false); }
  }, [profileId]);

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 15000);
    return () => clearInterval(interval);
  }, [fetchSessions]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchSessions();
    setRefreshing(false);
  };

  const runningSession = sessions.find(s => s.status === "running");
  const recentSessions = sessions.slice(0, 20);

  const totalActions = sessions.reduce((a, s) => a + (s.actions_completed || 0), 0);
  const totalFailed = sessions.reduce((a, s) => a + (s.actions_failed || 0), 0);
  const successRate = totalActions + totalFailed > 0
    ? Math.round((totalActions / (totalActions + totalFailed)) * 100)
    : 0;

  return (
    <div className="space-y-5 max-w-5xl">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-3">
        {[
          { label: "Sessions Run",     value: sessions.length, icon: Activity,    color: "text-indigo-600 dark:text-indigo-400", bg: "bg-indigo-50 dark:bg-indigo-950/40" },
          { label: "Actions Done",     value: totalActions,    icon: Zap,         color: "text-emerald-600 dark:text-emerald-400",bg: "bg-emerald-50 dark:bg-emerald-950/40" },
          { label: "Success Rate",     value: `${successRate}%`, icon: CheckCircle2, color: "text-blue-600 dark:text-blue-400",  bg: "bg-blue-50 dark:bg-blue-950/40" },
          { label: "Running Now",      value: runningSession ? "YES" : "Idle", icon: Radio, color: runningSession ? "text-blue-600 dark:text-blue-400" : "text-gray-400", bg: runningSession ? "bg-blue-50 dark:bg-blue-950/40" : "bg-gray-50 dark:bg-slate-900/40" },
        ].map(stat => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className={`rounded-xl border border-app-border/[0.06] ${stat.bg} p-3 sm:px-4 sm:py-3 flex items-center gap-2.5 sm:gap-3`}>
              <div className={`w-8 h-8 rounded-lg bg-white/80 dark:bg-slate-800 shadow-sm flex items-center justify-center flex-shrink-0`}>
                <Icon size={16} className={stat.color} />
              </div>
              <div className="min-w-0">
                <p className="text-[11px] text-app-text/50 truncate">{stat.label}</p>
                <p className={`text-base sm:text-lg font-bold ${stat.color} truncate`}>{stat.value}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800/60 rounded-xl p-1 border border-slate-200 dark:border-slate-800 w-full sm:w-auto">
          <button
            onClick={() => setLiveView("timeline")}
            className={`flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-3.5 py-2.5 min-h-[44px] rounded-lg text-xs sm:text-sm font-medium transition-all active:scale-[0.98] ${
              liveView === "timeline" ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-bold border border-slate-200 dark:border-slate-700" : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <Activity size={14} className="text-indigo-500" /> Activity Timeline
          </button>
          <button
            onClick={() => setLiveView("stream")}
            className={`flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-3.5 py-2.5 min-h-[44px] rounded-lg text-xs sm:text-sm font-medium transition-all active:scale-[0.98] ${
              liveView === "stream" ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-bold border border-slate-200 dark:border-slate-700" : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <Radio size={14} className="text-blue-500" /> Live Stream
            {runningSession && <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />}
          </button>
          <button
            onClick={() => setLiveView("history")}
            className={`flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-3.5 py-2.5 min-h-[44px] rounded-lg text-xs sm:text-sm font-medium transition-all active:scale-[0.98] ${
              liveView === "history" ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-bold border border-slate-200 dark:border-slate-700" : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <Clock size={14} className="text-slate-400" /> Sessions
          </button>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={handleRefresh}
            className="p-2.5 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-all flex-shrink-0 active:scale-95"
            title="Refresh"
          >
            <RotateCcw size={16} className={refreshing ? "animate-spin" : ""} />
          </button>
          {onTriggerSession && (
            <button
              onClick={onTriggerSession}
              disabled={triggeringSession || !!runningSession}
              className={`flex-1 sm:flex-initial flex items-center justify-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl text-xs sm:text-sm font-semibold transition-all active:scale-[0.98] ${
                runningSession ? "bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 cursor-not-allowed" : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs"
              }`}
            >
              {runningSession ? <><Loader2 size={14} className="animate-spin" /> Running...</> : triggeringSession ? <><Loader2 size={14} className="animate-spin" /> Starting...</> : <><Activity size={14} /> Run Session Now</>}
            </button>
          )}
        </div>
      </div>


      {liveView === "timeline" && <ActivityTimelineView profileId={profileId} />}
      {liveView === "stream" && (
        <div className="bg-panel/80 rounded-xl border border-app-border/[0.06] shadow-2xl shadow-black/30 overflow-hidden">
          <div className="flex items-center gap-3 px-5 py-3.5 border-b border-app-border/[0.05]">
            <Radio size={15} className="text-indigo-400" />
            <div>
              <h3 className="text-sm font-semibold text-app-text/90">Real-Time Activity Stream</h3>
              <p className="text-xs text-app-text/40">All bot events streamed live via WebSocket</p>
            </div>
            {runningSession && (
              <div className="ml-auto flex items-center gap-1.5 text-xs text-blue-600 font-medium">
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-ping" /> Session in progress
              </div>
            )}
          </div>
          <LiveFeed profileId={profileId} />
        </div>
      )}
      {liveView === "history" && (
        <div className="space-y-3">
          {loadingSessions && (
            <div className="flex items-center gap-2 py-8 justify-center text-app-text/40">
              <Loader2 size={18} className="animate-spin" /> <span className="text-sm">Loading sessions...</span>
            </div>
          )}
          {!loadingSessions && sessions.length === 0 && (
            <div className="py-16 text-center bg-panel/60 rounded-xl border border-app-border/[0.06]">
              <Activity size={48} className="mx-auto mb-4 text-app-text/15" />
              <p className="text-app-text/40 font-medium">No sessions recorded yet</p>
              <p className="text-sm text-app-text/25 mt-1">Run a session to see activity here</p>
            </div>
          )}
          {!loadingSessions && recentSessions.map((session, idx) => (
            <SessionCard key={session.id} session={session} defaultExpanded={idx === 0 && session.status === "running"} />
          ))}
        </div>
      )}
    </div>
  );
}
