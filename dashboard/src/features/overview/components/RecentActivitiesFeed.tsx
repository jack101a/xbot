import React from "react";
import { Clock, ArrowRight } from "lucide-react";
import { Session } from "@/lib/api";
import { formatISTDateTime } from "@/lib/time";

interface RecentActivitiesFeedProps {
  sessions: Session[];
  onNavigateToTab: (tab: "activity") => void;
  onSelectSession?: (sessionId: string) => void;
  onRunSession: () => void;
}

export function RecentActivitiesFeed({
  sessions,
  onNavigateToTab,
  onSelectSession,
  onRunSession
}: RecentActivitiesFeedProps) {
  return (
    <div className="lg:col-span-2 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Clock className="w-4 h-4 text-indigo-500" />
          <h3 className="font-bold text-xs sm:text-sm text-slate-900 dark:text-white">Recent Automation Sessions</h3>
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
          {sessions.slice(0, 4).map((s) => (
            <div
              key={s.id}
              onClick={() => {
                if (onSelectSession) onSelectSession(s.id);
                onNavigateToTab("activity");
              }}
              className="py-2 flex items-center justify-between gap-3 hover:bg-slate-50/50 dark:hover:bg-slate-800/30 px-2 rounded-xl transition cursor-pointer group"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
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
                      className={`text-[9px] uppercase font-bold px-1.5 py-0.2 rounded capitalize ${
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
                  <p className="text-[10px] text-slate-500 dark:text-slate-400">
                    {formatISTDateTime(s.started_at)} &bull; {s.actions_completed || 0} /{" "}
                    {s.actions_planned || 0} actions
                  </p>
                </div>
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-600 transition group-hover:translate-x-0.5 flex-shrink-0" />
            </div>
          ))}
        </div>
      ) : (
        <div className="py-6 text-center text-slate-500 text-xs space-y-2">
          <p>No recent sessions recorded yet.</p>
          <button
            onClick={onRunSession}
            className="px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition"
          >
            Run First Session Now
          </button>
        </div>
      )}
    </div>
  );
}
