import React from "react";
import { CheckSquare, Square, Image as ImageIcon, ExternalLink, Send, Calendar, CheckCircle2 } from "lucide-react";
import { Deliverable } from "../types";

interface DeliverableCardProps {
  item: Deliverable;
  idx: number;
  isSelected: boolean;
  toggleSelectDeliverable: (contentId: string) => void;
  handlePublishSingleDeliverable: (contentId: string, mode: "instant" | "schedule") => void;
  publishingItemIds: string[];
  publishedStatus: Record<string, string>;
}

export function DeliverableCard({
  item,
  idx,
  isSelected,
  toggleSelectDeliverable,
  handlePublishSingleDeliverable,
  publishingItemIds,
  publishedStatus,
}: DeliverableCardProps) {
  const isThread = item.type === "thread";
  const isPoll = item.type === "poll";
  const isVisual = item.type === "visual";

  return (
    <div
      onClick={() => toggleSelectDeliverable(item.content_id)}
      className={`p-4 rounded-xl border transition cursor-pointer relative flex flex-col justify-between ${
        isSelected
          ? "border-indigo-500 bg-indigo-50/40 dark:bg-indigo-950/20 shadow-md shadow-indigo-500/5"
          : "border-slate-200 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/60 hover:border-slate-300 dark:hover:border-slate-700"
      }`}
    >
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div
              className={`w-4 h-4 rounded flex items-center justify-center transition ${
                isSelected ? "text-indigo-600 dark:text-indigo-400" : "text-slate-400"
              }`}
            >
              {isSelected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
            </div>
            <span
              className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                isThread
                  ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
                  : isPoll
                  ? "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/30"
                  : isVisual
                  ? "bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/30"
                  : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
              }`}
            >
              {item.type}
            </span>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">#{idx + 1}</span>
        </div>

        <h3 className="text-xs font-bold text-slate-900 dark:text-slate-200 mb-2 line-clamp-1">
          {item.topic}
        </h3>

        {isThread && item.thread_tweets ? (
          <div className="space-y-2 pl-2.5 border-l-2 border-amber-500/40 my-2">
            {item.thread_tweets.map((tw: string, tIdx: number) => (
              <div key={tIdx} className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-sans">
                {tw}
              </div>
            ))}
          </div>
        ) : isPoll ? (
          <div className="space-y-2 my-2 p-2.5 rounded-lg bg-slate-100/70 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800">
            <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">{item.question || item.text}</div>
            <div className="space-y-1 pt-1">
              {(item.options || ["Option 1", "Option 2"]).map((opt: string, optIdx: number) => (
                <div
                  key={optIdx}
                  className="p-1.5 rounded-md bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/60 text-xs text-slate-700 dark:text-slate-300 flex items-center justify-between"
                >
                  <span>{opt}</span>
                  <span className="text-[10px] text-slate-400 font-mono">Option {optIdx + 1}</span>
                </div>
              ))}
            </div>
            <div className="text-[10px] text-slate-500 pt-0.5">
              📊 7-Day Interactive Community Poll
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap font-sans my-2">
            {item.text}
          </div>
        )}

        {item.media_paths && item.media_paths.length > 0 && (
          <div className="flex items-center gap-1.5 mt-2.5 pt-2 border-t border-slate-200 dark:border-slate-800/60 text-[11px] text-indigo-600 dark:text-indigo-400 font-medium">
            <ImageIcon className="w-3.5 h-3.5" />
            <span>{item.media_paths.length} Scraped Viral Media Asset(s) Attached</span>
          </div>
        )}

        {item.extracted_link && (
          <div className="flex items-center gap-1.5 mt-2 text-[11px] text-sky-600 dark:text-sky-400 font-mono">
            <ExternalLink className="w-3 h-3" />
            <span className="truncate">1st-Reply: {item.extracted_link}</span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between gap-2 mt-3 pt-2.5 border-t border-slate-200 dark:border-slate-800/80">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handlePublishSingleDeliverable(item.content_id, "instant");
            }}
            disabled={publishingItemIds.includes(item.content_id)}
            className="px-2 py-1 rounded-md bg-sky-500/10 hover:bg-sky-500/20 text-sky-600 dark:text-sky-400 border border-sky-500/30 text-[10px] font-bold flex items-center gap-1 transition disabled:opacity-50"
          >
            <Send className="w-3 h-3" />
            {publishingItemIds.includes(item.content_id) ? "Queuing..." : "Publish Now"}
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handlePublishSingleDeliverable(item.content_id, "schedule");
            }}
            disabled={publishingItemIds.includes(item.content_id)}
            className="px-2 py-1 rounded-md bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30 text-[10px] font-bold flex items-center gap-1 transition disabled:opacity-50"
          >
            <Calendar className="w-3 h-3" />
            Schedule
          </button>
        </div>

        {publishedStatus[item.content_id] ? (
          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" />
            {publishedStatus[item.content_id]}
          </span>
        ) : item.status === "approved" || item.status === "queued" ? (
          <span className="text-[10px] font-bold text-sky-600 dark:text-sky-400 flex items-center gap-1 bg-sky-500/10 px-2 py-0.5 rounded-full border border-sky-500/30">
            <CheckCircle2 className="w-3 h-3" />
            Queued
          </span>
        ) : null}
      </div>
    </div>
  );
}
