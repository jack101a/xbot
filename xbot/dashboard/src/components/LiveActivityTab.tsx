"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Activity, Heart, MessageSquare, Repeat2, UserPlus, UserMinus, Users,
  Eye, Search, TrendingUp, BarChart2, PenLine, ChevronDown, ChevronRight,
  Circle, CheckCircle2, XCircle, Clock, Loader2, Zap, RotateCcw,
  AlertTriangle, Radio, ExternalLink, FileText, BookOpen
} from "lucide-react";
import { api, Session, Action, Profile, getWebSocketUrl } from "@/lib/api";


// ── Action type metadata ─────────────────────────────────────────────────────

const ACTION_META: Record<string, {
  icon: React.ElementType;
  label: string;
  color: string;
  bg: string;
  verb: string;
}> = {
  post:                   { icon: PenLine,       label: "Post",         color: "text-violet-600", bg: "bg-violet-100",  verb: "Published tweet" },
  reply:                  { icon: MessageSquare, label: "Reply",        color: "text-sky-600",    bg: "bg-sky-100",     verb: "Replied to" },
  like:                   { icon: Heart,         label: "Like",         color: "text-rose-500",   bg: "bg-rose-100",    verb: "Liked tweet" },
  retweet:                { icon: Repeat2,       label: "Retweet",      color: "text-emerald-600",bg: "bg-emerald-100", verb: "Retweeted" },
  quote:                  { icon: FileText,      label: "Quote",        color: "text-amber-600",  bg: "bg-amber-100",   verb: "Quoted tweet" },
  follow:                 { icon: UserPlus,      label: "Follow",       color: "text-blue-600",   bg: "bg-blue-100",    verb: "Followed" },
  unfollow:               { icon: UserMinus,     label: "Unfollow",     color: "text-gray-500",   bg: "bg-gray-100",    verb: "Unfollowed" },
  browse:                 { icon: Eye,           label: "Browse",       color: "text-indigo-500", bg: "bg-indigo-100",  verb: "Browsed feed" },
  search:                 { icon: Search,        label: "Search",       color: "text-teal-600",   bg: "bg-teal-100",    verb: "Searched" },
  scrape_trends:          { icon: TrendingUp,    label: "Trends",       color: "text-orange-500", bg: "bg-orange-100",  verb: "Scraped trends" },
  scrape_metrics:         { icon: BarChart2,     label: "Metrics",      color: "text-purple-600", bg: "bg-purple-100",  verb: "Scraped metrics" },
  unfollow_non_followers: { icon: UserMinus,     label: "Clean Ratio",  color: "text-rose-600",   bg: "bg-rose-100",    verb: "Cleaned ratio (Unfollowed non-followers)" },
  follow_engagers:        { icon: Users,         label: "Target Follow",color: "text-emerald-600",bg: "bg-emerald-100", verb: "Followed engagers of tweet" },
};

const STATUS_META: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  pending:   { icon: Clock,        color: "text-gray-400",   label: "Pending" },
  executing: { icon: Loader2,      color: "text-blue-500",   label: "Running" },
  completed: { icon: CheckCircle2, color: "text-emerald-500",label: "Done" },
  failed:    { icon: XCircle,      color: "text-rose-500",   label: "Failed" },
  skipped:   { icon: AlertTriangle,color: "text-amber-500",  label: "Skipped" },
};

// ── Live event stream types ───────────────────────────────────────────────────

interface LiveEvent {
  id: string;
  session_id: string;
  event: string;
  timestamp: string;
  action_type?: string;
  action_id?: string;
  action_index?: number;
  status?: string;
  content?: string;
  target_url?: string;
  error?: string;
  message?: string;
  actions_count?: number;
  plan?: any;
  profile_slug?: string;
  completed?: number;
  failed?: number;
  reason?: string;
  reasoning?: string;
  priority?: number;
  duration_ms?: number;
}

// ── Utility helpers ────────────────────────────────────────────────────────────

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function timeSince(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  return `${Math.round(diff / 3600)}h ago`;
}

function describeEvent(ev: LiveEvent): string {
  const meta = ev.action_type ? ACTION_META[ev.action_type] : null;
  switch (ev.event) {
    case "session_start":   return `🟢 Session started for @${ev.profile_slug || "profile"}`;
    case "mock_mode_active":return `🧪 Mock/Demo mode active — no live X requests`;
    case "session_planned": return `🧠 AI planned ${ev.actions_count || 0} actions`;
    case "action_start":    return `⚡ Starting: ${meta?.verb || ev.action_type}${ev.target_url ? ` → ${ev.target_url}` : ""}`;
    case "action_complete": return `✅ ${meta?.verb || ev.action_type} — ${ev.status === "completed" ? "success" : ev.status}${ev.error ? ` (${ev.error})` : ""}`;
    case "mock_action_executed": return ev.message || `🧪 [Mock] Simulated ${ev.action_type}`;
    case "session_complete":
      if (ev.status === "aborted") return `⏭ Session skipped: ${ev.reason || "natural break"}`;
      if (ev.status === "failed") return `❌ Session failed: ${ev.error || "unknown error"}`;
      return `🏁 Session complete — ${ev.completed || 0} done, ${ev.failed || 0} failed`;
    default: return ev.message || ev.event;
  }
}

// ── ActionRow component ────────────────────────────────────────────────────────

function ActionRow({ action }: { action: Action }) {
  const meta = ACTION_META[action.action_type] || ACTION_META.browse;
  const status = STATUS_META[action.status] || STATUS_META.pending;
  const Icon = meta.icon;
  const StatusIcon = status.icon;

  return (
    <div className="flex items-start gap-3 px-5 py-3.5 border-b border-app-border/[0.05] last:border-b-0 hover:bg-app/50 transition-colors group">
      {/* Action type icon */}
      <div className={`mt-0.5 w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${meta.bg}`}>
        <Icon size={13} className={meta.color} />
      </div>

      <div className="flex-1 min-w-0">
        {/* Action label + status */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs font-semibold uppercase tracking-wider ${meta.color}`}>{meta.label}</span>
          <span className={`flex items-center gap-1 text-xs font-medium ${status.color}`}>
            <StatusIcon
              size={11}
              className={action.status === "executing" ? "animate-spin" : ""}
            />
            {status.label}
          </span>
          {action.duration_ms > 0 && (
            <span className="text-xs text-app-text/30">{formatDuration(action.duration_ms)}</span>
          )}
        </div>

        {/* Content / target */}
        {action.content && (
          <p className="mt-1 text-sm text-app-text/80 leading-snug line-clamp-3 bg-app/60 rounded px-2 py-1.5 border border-app-border/[0.04]">
            "{action.content}"
          </p>
        )}
        {action.target_url && !action.content && (
          <a
            href={action.target_url.startsWith("http") ? action.target_url : `https://x.com${action.target_url}`}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 flex items-center gap-1 text-xs text-blue-500 hover:text-blue-600 hover:underline break-all"
          >
            <ExternalLink size={10} />
            {action.target_url.length > 70 ? action.target_url.slice(0, 70) + "…" : action.target_url}
          </a>
        )}
        {!action.content && !action.target_url && (
          <p className="mt-0.5 text-xs text-app-text/40 italic">{meta.verb}</p>
        )}

        {/* Error */}
        {action.error && (
          <p className="mt-1 text-xs text-rose-500 bg-rose-50 rounded px-2 py-1">⚠ {action.error}</p>
        )}
      </div>

      {/* Timestamp */}
      {action.executed_at && (
        <span className="text-xs text-app-text/30 whitespace-nowrap flex-shrink-0 pt-0.5">
          {new Date(action.executed_at).toLocaleTimeString()}
        </span>
      )}
    </div>
  );
}

// ── SessionCard component ──────────────────────────────────────────────────────

function SessionCard({ session, defaultExpanded = false }: { session: Session; defaultExpanded?: boolean }) {
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

  const sessionStatus = isRunning ? "running" :
    (session.status === "completed" ? "completed" :
     session.status === "aborted" ? "skipped" : "failed");

  const sessionMeta = STATUS_META[sessionStatus] || STATUS_META.completed;
  const SessionIcon = sessionMeta.icon;

  // Compute mood from plan if available
  const mood = session.plan?.mood;

  return (
    <div className={`rounded-xl border transition-all duration-200 ${
      isRunning
        ? "border-blue-400/40 bg-blue-50/30 shadow-[0_0_20px_rgba(59,130,246,0.08)]"
        : "border-app-border/[0.06] bg-panel/60"
    }`}>
      {/* Header row */}
      <button
        onClick={toggle}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-app/30 transition-colors rounded-xl"
      >
        {/* Status indicator */}
        <div className={`relative flex-shrink-0 ${isRunning ? "animate-pulse" : ""}`}>
          <SessionIcon
            size={18}
            className={`${sessionMeta.color} ${isRunning ? "animate-spin" : ""}`}
          />
          {isRunning && (
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-blue-400 rounded-full border-2 border-white animate-ping" />
          )}
        </div>

        {/* Time */}
        <div className="flex flex-col min-w-[120px]">
          <span className="text-sm font-semibold text-app-text/90">
            {new Date(session.started_at).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}
          </span>
          {session.ended_at && (
            <span className="text-xs text-app-text/40">
              {Math.round((new Date(session.ended_at).getTime() - new Date(session.started_at).getTime()) / 1000)}s duration
            </span>
          )}
          {isRunning && <span className="text-xs text-blue-500 font-medium animate-pulse">● Live now</span>}
        </div>

        {/* Status badge */}
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
          isRunning ? "bg-blue-100 text-blue-700 border-blue-200" :
          session.status === "completed" ? "bg-emerald-100 text-emerald-700 border-emerald-200" :
          session.status === "aborted" ? "bg-amber-100 text-amber-700 border-amber-200" :
          "bg-rose-100 text-rose-700 border-rose-200"
        }`}>
          {session.status.toUpperCase()}
        </span>

        {/* Mood */}
        {mood && (
          <span className="text-xs text-app-text/50 italic hidden sm:block">{mood}</span>
        )}

        {/* Actions counter */}
        <div className="flex-1 flex items-center gap-3 justify-end">
          {session.actions_planned > 0 && (
            <div className="flex flex-col items-end gap-1">
              <span className="text-xs text-app-text/50">
                {session.actions_completed}/{session.actions_planned} actions
              </span>
              <div className="w-24 h-1.5 bg-app rounded-full overflow-hidden">
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
            <span className="text-xs text-rose-500">{session.actions_failed} failed</span>
          )}
        </div>

        {/* Expand chevron */}
        <div className="flex-shrink-0 ml-2">
          {expanded
            ? <ChevronDown size={16} className="text-app-text/30" />
            : <ChevronRight size={16} className="text-app-text/30" />
          }
        </div>
      </button>

      {/* Action list */}
      {expanded && (
        <div className="border-t border-app-border/[0.05]">
          {/* AI Plan summary */}
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

          {/* Session error */}
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

// ── LiveFeed: the real-time streaming panel ────────────────────────────────────

function LiveFeed({ profileId, sessionId }: { profileId?: string; sessionId?: string }) {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    const wsUrl = getWebSocketUrl(sessionId ? `/api/ws/sessions/${sessionId}` : '/api/ws/live');

    const connect = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, 3000); // auto-reconnect
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (e) => {
        try {
          const data: LiveEvent = JSON.parse(e.data);
          data.id = `${data.timestamp}-${Math.random()}`;
          setEvents(prev => [...prev.slice(-200), data]); // keep last 200 events
        } catch {}
      };
    };
    connect();
    return () => wsRef.current?.close();
  }, [sessionId]);

  useEffect(() => {
    if (autoScroll && feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  const eventIcon = (ev: LiveEvent) => {
    if (ev.event === "session_start") return "🟢";
    if (ev.event === "session_complete") return ev.status === "completed" ? "🏁" : ev.status === "failed" ? "❌" : "⏭";
    if (ev.event === "session_planned") return "🧠";
    if (ev.event === "mock_mode_active") return "🧪";
    if (ev.event === "mock_action_executed") return "🧪";
    if (ev.event === "action_start") return "⚡";
    if (ev.event === "action_complete") return ev.status === "completed" ? "✅" : ev.status === "failed" ? "❌" : "⏭";
    return "📡";
  };

  return (
    <div className="flex flex-col h-full">
      {/* Status bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-app-border/[0.05] bg-app/40">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400 animate-pulse" : "bg-gray-300"}`} />
          <span className="text-xs font-medium text-app-text/60">
            {connected ? "Live — streaming events" : "Reconnecting..."}
          </span>
          {events.length > 0 && (
            <span className="text-xs text-app-text/30">{events.length} events</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1 text-xs text-app-text/40 cursor-pointer">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={e => setAutoScroll(e.target.checked)}
              className="w-3 h-3"
            />
            Auto-scroll
          </label>
          <button
            onClick={() => setEvents([])}
            className="text-xs text-app-text/30 hover:text-app-text/60 transition-colors"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Event stream */}
      <div
        ref={feedRef}
        className="flex-1 overflow-y-auto font-mono text-xs space-y-0"
        style={{ maxHeight: "380px" }}
      >
        {events.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full py-12 text-app-text/25">
            <Radio size={28} className="mb-3" />
            <p>Waiting for bot activity...</p>
            <p className="text-xs mt-1">Start a session to see live events here</p>
          </div>
        )}
        {events.map(ev => {
          const actionMeta = ev.action_type ? ACTION_META[ev.action_type] : null;
          const isAction = ev.event === "action_start" || ev.event === "action_complete" || ev.event === "mock_action_executed";
          const isFailed = ev.event === "action_complete" && ev.status === "failed";

          return (
            <div
              key={ev.id}
              className={`flex items-start gap-2 px-4 py-1.5 border-b border-app-border/[0.03] transition-colors hover:bg-app/30 ${
                isFailed ? "bg-rose-50/30" : ""
              } ${ev.event === "session_start" || ev.event === "session_complete" ? "bg-emerald-50/20" : ""}`}
            >
              <span className="text-app-text/25 w-16 flex-shrink-0 pt-0.5">
                {new Date(ev.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
              <span className="w-5 flex-shrink-0">{eventIcon(ev)}</span>
              {actionMeta && isAction && (
                <span className={`${actionMeta.color} font-semibold uppercase w-16 flex-shrink-0`} style={{ fontSize: "10px" }}>
                  [{actionMeta.label}]
                </span>
              )}
              <span className={`flex-1 leading-snug ${isFailed ? "text-rose-600" : "text-app-text/75"}`}>
                {describeEvent(ev)}
                {ev.reasoning && (
                  <span className="block mt-0.5 text-app-text/40 italic truncate">
                    ↳ {ev.reasoning.slice(0, 100)}{ev.reasoning.length > 100 ? "…" : ""}
                  </span>
                )}
                {ev.content && !ev.reasoning && (
                  <span className="block mt-0.5 text-app-text/50 italic truncate max-w-xs">
                    "{ev.content?.slice(0, 80)}{(ev.content?.length || 0) > 80 ? "…" : ""}"
                  </span>
                )}
                {ev.content && ev.reasoning && (
                  <span className="block mt-0.5 text-violet-600/70 italic truncate max-w-xs">
                    📝 "{ev.content?.slice(0, 80)}{(ev.content?.length || 0) > 80 ? "…" : ""}"
                  </span>
                )}
                {ev.duration_ms && ev.duration_ms > 0 && (
                  <span className="text-app-text/25 ml-2">({(ev.duration_ms / 1000).toFixed(1)}s)</span>
                )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main LiveActivityTab component ────────────────────────────────────────────

interface LiveActivityTabProps {
  profileId: string;
  selectedProfile?: Profile;
  initialSessionId?: string;
  onTriggerSession?: () => void;
  triggeringSession?: boolean;
}

export function LiveActivityTab({
  profileId,
  selectedProfile,
  initialSessionId,
  onTriggerSession,
  triggeringSession
}: LiveActivityTabProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [liveView, setLiveView] = useState<"history" | "stream">("stream");
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
    const interval = setInterval(fetchSessions, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, [fetchSessions]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchSessions();
    setRefreshing(false);
  };

  const runningSession = sessions.find(s => s.status === "running");
  const recentSessions = sessions.slice(0, 20);

  // Stats
  const totalActions = sessions.reduce((a, s) => a + (s.actions_completed || 0), 0);
  const totalFailed = sessions.reduce((a, s) => a + (s.actions_failed || 0), 0);
  const successRate = totalActions + totalFailed > 0
    ? Math.round((totalActions / (totalActions + totalFailed)) * 100)
    : 0;

  return (
    <div className="space-y-5 max-w-5xl">
      {/* ── Summary stats ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Sessions Run",     value: sessions.length, icon: Activity,    color: "text-indigo-600", bg: "bg-indigo-50" },
          { label: "Actions Done",     value: totalActions,    icon: Zap,         color: "text-emerald-600",bg: "bg-emerald-50" },
          { label: "Success Rate",     value: `${successRate}%`, icon: CheckCircle2, color: "text-blue-600",  bg: "bg-blue-50" },
          { label: "Running Now",      value: runningSession ? "YES" : "Idle", icon: Radio, color: runningSession ? "text-blue-600" : "text-gray-400", bg: runningSession ? "bg-blue-50" : "bg-gray-50" },
        ].map(stat => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className={`rounded-xl border border-app-border/[0.06] ${stat.bg} px-4 py-3 flex items-center gap-3`}>
              <div className={`w-8 h-8 rounded-lg bg-white/80 shadow-sm flex items-center justify-center flex-shrink-0`}>
                <Icon size={16} className={stat.color} />
              </div>
              <div>
                <p className="text-xs text-app-text/50">{stat.label}</p>
                <p className={`text-lg font-bold ${stat.color}`}>{stat.value}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Tab switcher + actions ─────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1 bg-app rounded-lg p-1 border border-app-border/[0.06]">
          <button
            onClick={() => setLiveView("stream")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
              liveView === "stream"
                ? "bg-panel text-app-text shadow-sm"
                : "text-app-text/50 hover:text-app-text/70"
            }`}
          >
            <Radio size={13} />
            Live Stream
            {runningSession && <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />}
          </button>
          <button
            onClick={() => setLiveView("history")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
              liveView === "history"
                ? "bg-panel text-app-text shadow-sm"
                : "text-app-text/50 hover:text-app-text/70"
            }`}
          >
            <Clock size={13} />
            Session History
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            className="p-2 rounded-lg border border-app-border/[0.06] text-app-text/40 hover:text-app-text/70 hover:bg-app transition-all"
          >
            <RotateCcw size={14} className={refreshing ? "animate-spin" : ""} />
          </button>
          {onTriggerSession && (
            <button
              onClick={onTriggerSession}
              disabled={triggeringSession || !!runningSession}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                runningSession
                  ? "bg-blue-100 text-blue-600 cursor-not-allowed"
                  : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm"
              }`}
            >
              {runningSession ? (
                <><Loader2 size={13} className="animate-spin" /> Session Running...</>
              ) : triggeringSession ? (
                <><Loader2 size={13} className="animate-spin" /> Starting...</>
              ) : (
                <><Activity size={13} /> Run Session Now</>
              )}
            </button>
          )}
        </div>
      </div>

      {/* ── Live stream view ───────────────────────────────────────── */}
      {liveView === "stream" && (
        <div className="bg-panel/80 backdrop-blur-xl rounded-xl border border-app-border/[0.06] shadow-2xl shadow-black/30 overflow-hidden">
          <div className="flex items-center gap-3 px-5 py-3.5 border-b border-app-border/[0.05]">
            <Radio size={15} className="text-indigo-400" />
            <div>
              <h3 className="text-sm font-semibold text-app-text/90">Real-Time Activity Stream</h3>
              <p className="text-xs text-app-text/40">All bot events streamed live via WebSocket</p>
            </div>
            {runningSession && (
              <div className="ml-auto flex items-center gap-1.5 text-xs text-blue-600 font-medium">
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-ping" />
                Session in progress
              </div>
            )}
          </div>
          <LiveFeed profileId={profileId} />
        </div>
      )}

      {/* ── Session history view ───────────────────────────────────── */}
      {liveView === "history" && (
        <div className="space-y-3">
          {loadingSessions && (
            <div className="flex items-center gap-2 py-8 justify-center text-app-text/40">
              <Loader2 size={18} className="animate-spin" />
              <span className="text-sm">Loading sessions...</span>
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
            <SessionCard
              key={session.id}
              session={session}
              defaultExpanded={idx === 0 && session.status === "running"}
            />
          ))}
        </div>
      )}
    </div>
  );
}
