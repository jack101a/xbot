import React, { useState, useEffect, useRef } from "react";
import { Radio } from "lucide-react";
import { getWebSocketUrl } from "@/lib/api";
import { formatISTTime } from "@/lib/time";
import { LiveEvent } from "../types";
import { ACTION_META } from "../constants";

export function LiveFeed({ profileId, sessionId }: { profileId?: string; sessionId?: string }) {
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
        setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (e) => {
        try {
          const data: LiveEvent = JSON.parse(e.data);
          data.id = `${data.timestamp}-${Math.random()}`;
          setEvents(prev => [...prev.slice(-200), data]);
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
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 sm:px-4 py-2 border-b border-app-border/[0.05] bg-app/40">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400 animate-pulse" : "bg-gray-300"}`} />
          <span className="text-[11px] sm:text-xs font-medium text-app-text/60 truncate">
            {connected ? "Live — streaming events" : "Reconnecting..."}
          </span>
          {events.length > 0 && (
            <span className="text-[10px] sm:text-xs text-app-text/30">({events.length})</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1 text-[11px] sm:text-xs text-app-text/40 cursor-pointer">
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
            className="text-[11px] sm:text-xs text-app-text/30 hover:text-app-text/60 transition-colors"
          >
            Clear
          </button>
        </div>
      </div>

      <div
        ref={feedRef}
        className="flex-1 overflow-y-auto font-mono text-[11px] sm:text-xs space-y-0"
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
              className={`flex items-start gap-1.5 sm:gap-2 px-3 sm:px-4 py-1.5 border-b border-app-border/[0.03] transition-colors hover:bg-app/30 break-words min-w-0 ${
                isFailed ? "bg-rose-50/30" : ""
              } ${ev.event === "session_start" || ev.event === "session_complete" ? "bg-emerald-50/20" : ""}`}
            >
              <span className="text-app-text/25 w-14 sm:w-16 flex-shrink-0 pt-0.5 text-[10px] sm:text-xs">
                {formatISTTime(ev.timestamp, true)}
              </span>
              <span className="w-4 sm:w-5 flex-shrink-0">{eventIcon(ev)}</span>
              {actionMeta && isAction && (
                <span className={`${actionMeta.color} font-semibold uppercase w-14 sm:w-16 flex-shrink-0 text-[9px] sm:text-[10px]`}>
                  [{actionMeta.label}]
                </span>
              )}
              <span className="flex-1 text-app-text/80 text-[11px] sm:text-xs">
                {ev.message || ev.content || ev.event}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
