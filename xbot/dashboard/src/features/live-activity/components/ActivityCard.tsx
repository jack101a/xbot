import React from "react";
import { ArrowUpRight, Sparkles, AlertTriangle } from "lucide-react";
import { ActivityItem } from "@/lib/api";
import { ACTION_META, STATUS_META } from "../constants";
import { formatDuration, formatFullDate } from "../utils";

export function ActivityCard({ item }: { item: ActivityItem }) {
  const meta = ACTION_META[item.action_type] || ACTION_META.browse;
  const status = STATUS_META[item.status] || STATUS_META.pending;
  const Icon = meta.icon;
  const StatusIcon = status.icon;

  const reasoning = item.result?.reasoning || item.result?.rationale;
  const angleUsed = item.result?.angle_used || item.result?.angle;

  return (
    <div className={`rounded-xl border border-app-border/[0.08] bg-panel/70 p-4 sm:p-5 transition-all hover:border-app-border/[0.18] shadow-sm space-y-3`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider ${meta.bg} ${meta.color} border ${meta.border}`}>
            <Icon size={13} />
            {meta.label}
          </span>
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium ${status.bg} ${status.color}`}>
            <StatusIcon size={12} className={item.status === "executing" ? "animate-spin" : ""} />
            {status.label}
          </span>
          {item.duration_ms > 0 && (
            <span className="text-[11px] text-app-text/40 font-mono">
              {formatDuration(item.duration_ms)}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-right">
          {item.executed_at && (
            <span className="text-xs text-app-text/50 font-medium hidden sm:inline">
              {formatFullDate(item.executed_at)}
            </span>
          )}
          {item.time_ago && (
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-app text-app-text/70 border border-app-border/[0.06]">
              {item.time_ago}
            </span>
          )}
        </div>
      </div>

      {item.target_url && (
        <div className="flex items-center gap-2 text-xs bg-app/50 rounded-lg px-3 py-2 border border-app-border/[0.05]">
          <span className="text-app-text/50 flex-shrink-0 font-medium">Target Context:</span>
          {item.target_author && (
            <span className="font-semibold text-blue-600 dark:text-blue-400">
              {item.target_author}
            </span>
          )}
          <a
            href={item.target_url.startsWith("http") ? item.target_url : `https://x.com${item.target_url}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-blue-500 hover:text-blue-600 hover:underline truncate ml-auto flex-shrink min-w-0"
          >
            <span className="truncate">{item.target_url}</span>
            <ArrowUpRight size={13} className="flex-shrink-0" />
          </a>
        </div>
      )}

      {item.content && (
        <div className="bg-white/80 dark:bg-slate-900/80 rounded-xl p-3.5 sm:p-4 border border-app-border/[0.08] shadow-inner space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-app-text/40 font-medium">
            <span>Actual Content Generated / Posted:</span>
            <span>{item.content.length} chars</span>
          </div>
          <p className="text-sm sm:text-base text-app-text font-normal leading-relaxed whitespace-pre-wrap">
            "{item.content}"
          </p>
        </div>
      )}

      {(reasoning || angleUsed) && (
        <div className="flex items-start gap-2 bg-indigo-50/50 dark:bg-indigo-950/30 rounded-lg p-2.5 border border-indigo-100/60 dark:border-indigo-900/40 text-xs text-indigo-800 dark:text-indigo-300">
          <Sparkles size={14} className="text-indigo-500 mt-0.5 flex-shrink-0" />
          <div className="space-y-0.5 min-w-0">
            {angleUsed && (
              <p className="font-semibold capitalize text-indigo-700 dark:text-indigo-200">
                Strategy Angle: <span className="underline decoration-indigo-400">{angleUsed}</span>
              </p>
            )}
            {reasoning && (
              <p className="text-indigo-900/80 dark:text-indigo-300/80 leading-snug">
                {reasoning}
              </p>
            )}
          </div>
        </div>
      )}

      {item.error && (
        <div className={`flex items-start gap-2 rounded-lg p-2.5 text-xs ${
          item.status === "skipped"
            ? "bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
            : "bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800"
        }`}>
          <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
          <div>
            <span className="font-semibold">{item.status === "skipped" ? "Skipped by Safety Guard: " : "Execution Error: "}</span>
            <span>{item.error}</span>
          </div>
        </div>
      )}
    </div>
  );
}
