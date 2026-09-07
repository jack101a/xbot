import React, { useState, useCallback } from "react";
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, AlertTriangle, Circle, Loader2, BookOpen } from "lucide-react";
import { api, Session, Action } from "@/lib/api";
import { formatFullDate, formatDuration } from "../utils";
import { ActionRow } from "./ActionRow";

export function SessionCard({ session, defaultExpanded = false }: { session: Session; defaultExpanded?: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [actions, setActions] = useState<Action[] | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (actions !== null) return;
    setLoading(true);
    try {
      const data = await api.getSessionActions(session.id);
      setActions(data);
    } catch {
      setActions([]);
    } finally {
      setLoading(false);
    }
  }, [session.id, actions]);

  const toggle = () => {
    if (!expanded) load();
    setExpanded(e => !e);
  };

  const isRunning = session.status === "running";
  const pct = session.actions_planned > 0
    ? Math.round((session.actions_completed / session.actions_planned) * 100)
    : 0;

  return (
    <div className={`rounded-xl border transition-all duration-200 overflow-hidden ${
      isRunning
        ? "bg-panel/90 border-blue-200 dark:border-blue-800 shadow-md shadow-blue-500/5"
        : "bg-panel/70 border-app-border/[0.06] hover:border-app-border/[0.15]"
    }`}>
      <button
        onClick={toggle}
        className="w-full flex items-center justify-between p-3.5 sm:p-4 text-left transition-colors hover:bg-app/40 gap-3"
      >
        <div className="flex items-center gap-2.5 sm:gap-3 min-w-0 flex-1">
          <div className={`w-8 h-8 sm:w-9 sm:h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
            isRunning ? "bg-blue-100 text-blue-600 animate-pulse" :
            session.status === "completed" ? "bg-emerald-100 text-emerald-600" :
            session.status === "aborted" ? "bg-amber-100 text-amber-600" :
            "bg-rose-100 text-rose-600"
          }`}>
            {isRunning ? <Loader2 size={16} className="animate-spin" /> :
             session.status === "completed" ? <CheckCircle2 size={16} /> :
             session.status === "aborted" ? <AlertTriangle size={16} /> :
             <XCircle size={16} />}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs sm:text-sm font-semibold text-app-text truncate">
                Session {session.id.slice(0, 8)}
              </span>
              {isRunning && (
                <span className="flex items-center gap-1 text-[10px] sm:text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 animate-pulse">
                  <Circle size={6} className="fill-blue-500 text-blue-500" /> LIVE
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5 text-[11px] sm:text-xs text-app-text/40 flex-wrap">
              <span>{formatFullDate(session.started_at)}</span>
              {session.ended_at && (
                <span>• {formatDuration(new Date(session.ended_at).getTime() - new Date(session.started_at).getTime())}</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3 justify-end flex-shrink-0">
          {session.actions_planned > 0 && (
            <div className="flex flex-col items-end gap-1">
              <span className="text-[11px] sm:text-xs text-app-text/50">
                {session.actions_completed}/{session.actions_planned}
              </span>
              <div className="w-16 sm:w-24 h-1.5 bg-app rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    session.status === "completed" ? "bg-emerald-400" :
                    isRunning ? "bg-blue-400" : "bg-rose-400"
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )}
          {session.actions_failed > 0 && (
            <span className="text-xs text-rose-500 hidden sm:inline">{session.actions_failed} failed</span>
          )}

          <div className="flex-shrink-0 ml-1">
            {expanded
              ? <ChevronDown size={16} className="text-app-text/30" />
              : <ChevronRight size={16} className="text-app-text/30" />
            }
          </div>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-app-border/[0.05]">
          {session.plan?.reasoning && (
            <div className="px-5 py-3 bg-indigo-50/40 border-b border-indigo-100/50 flex items-start gap-2">
              <BookOpen size={13} className="text-indigo-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-indigo-700 leading-snug">
                <span className="font-semibold">AI Reasoning: </span>{session.plan.reasoning}
              </p>
            </div>
          )}

          {loading && (
            <div className="flex items-center gap-2 px-5 py-6 text-app-text/40">
              <Loader2 size={16} className="animate-spin" />
              <span className="text-sm">Loading action details...</span>
            </div>
          )}

          {!loading && actions !== null && actions.length === 0 && (
            <div className="px-5 py-6 text-center text-sm text-app-text/30">
              No individual actions recorded for this session.
            </div>
          )}

          {!loading && actions && actions.length > 0 && (
            <div>
              {actions.map(action => (
                <ActionRow key={action.id} action={action} />
              ))}
            </div>
          )}

          {session.error_log && (
            <div className="px-5 py-3 bg-rose-50 border-t border-rose-100 flex items-start gap-2">
              <XCircle size={13} className="text-rose-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-rose-600">{session.error_log}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
