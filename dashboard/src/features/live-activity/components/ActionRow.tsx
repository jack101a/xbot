import React from "react";
import { ExternalLink } from "lucide-react";
import { Action } from "@/lib/api";
import { ACTION_META, STATUS_META } from "../constants";
import { formatDuration } from "../utils";
import { formatISTTime } from "@/lib/time";

export function ActionRow({ action }: { action: Action }) {
  const meta = ACTION_META[action.action_type] || ACTION_META.browse;
  const status = STATUS_META[action.status] || STATUS_META.pending;
  const Icon = meta.icon;
  const StatusIcon = status.icon;

  return (
    <div className="flex items-start gap-2.5 sm:gap-3 px-3 sm:px-5 py-3 sm:py-3.5 border-b border-app-border/[0.05] last:border-b-0 hover:bg-app/50 transition-colors group">
      <div className={`mt-0.5 w-6 h-6 sm:w-7 sm:h-7 rounded-full flex items-center justify-center flex-shrink-0 ${meta.bg}`}>
        <Icon size={12} className={meta.color} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
          <span className={`text-[11px] sm:text-xs font-semibold uppercase tracking-wider ${meta.color}`}>{meta.label}</span>
          <span className={`flex items-center gap-1 text-[11px] sm:text-xs font-medium ${status.color}`}>
            <StatusIcon
              size={11}
              className={action.status === "executing" ? "animate-spin" : ""}
            />
            {status.label}
          </span>
          {action.duration_ms > 0 && (
            <span className="text-[10px] sm:text-xs text-app-text/30">{formatDuration(action.duration_ms)}</span>
          )}
        </div>

        {action.content && (
          <p className="mt-1 text-xs sm:text-sm text-app-text/80 leading-snug break-words bg-app/60 rounded px-2 py-1.5 border border-app-border/[0.04]">
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
            {action.target_url.length > 50 ? action.target_url.slice(0, 50) + "…" : action.target_url}
          </a>
        )}
        {!action.content && !action.target_url && (
          <p className="mt-0.5 text-xs text-app-text/40 italic">{meta.verb}</p>
        )}

        {action.error && (
          <p className="mt-1 text-xs text-rose-500 bg-rose-50 rounded px-2 py-1 break-words">⚠ {action.error}</p>
        )}
      </div>

      {action.executed_at && (
        <span className="text-[10px] sm:text-xs text-app-text/30 whitespace-nowrap flex-shrink-0 pt-0.5">
          {formatISTTime(action.executed_at)}
        </span>
      )}
    </div>
  );
}
