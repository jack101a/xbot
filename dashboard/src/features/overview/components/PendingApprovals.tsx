import React from "react";
import { CheckCircle2, Image as ImageIcon } from "lucide-react";
import { formatISTTime } from "@/lib/time";
import { API_BASE_URL } from "@/lib/api";

interface PendingApprovalsProps {
  drafts: any[];
  approvingId: string | null;
  onApproveAll: () => void;
  onDismissAll: () => void;
  onApproveDraft: (id: string) => void;
  onDismissDraft: (id: string) => void;
}

export function PendingApprovals({
  drafts,
  approvingId,
  onApproveAll,
  onDismissAll,
  onApproveDraft,
  onDismissDraft
}: PendingApprovalsProps) {
  if (drafts.length === 0) return null;

  return (
    <div className="lg:col-span-3 p-4 rounded-2xl border-2 border-amber-300/80 dark:border-amber-700/80 bg-amber-50/50 dark:bg-amber-950/20 shadow-sm space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
          </span>
          <h2 className="text-xs sm:text-sm font-bold text-amber-900 dark:text-amber-200">
            Pending Posts Staged for Your Approval ({drafts.length})
          </h2>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={onApproveAll}
            className="px-2.5 py-1 rounded-lg text-xs font-bold text-emerald-800 dark:text-emerald-200 bg-emerald-100 dark:bg-emerald-950/80 hover:bg-emerald-200 dark:hover:bg-emerald-900 border border-emerald-300 dark:border-emerald-700 transition flex items-center gap-1 shadow-sm"
          >
            <span>⚡ Publish All Now ({drafts.length})</span>
          </button>
          <button
            onClick={onDismissAll}
            className="px-2.5 py-1 rounded-lg text-xs font-bold text-rose-700 dark:text-rose-300 bg-rose-100 dark:bg-rose-950/60 hover:bg-rose-200 dark:hover:bg-rose-900/80 border border-rose-300 dark:border-rose-800 transition"
          >
            Discard All
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
        {drafts.map((d) => (
          <div
            key={d.id}
            className="p-3.5 rounded-xl border border-amber-200 dark:border-amber-800/60 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between space-y-2.5"
          >
            <div>
              <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1.5">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className={`px-2 py-0.5 rounded-md uppercase tracking-wider text-[10px] font-bold ${
                    d.content_type === "thread"
                      ? "bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300"
                      : d.content_type === "poll"
                      ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                  }`}>
                    {d.content_type === "thread" ? `🧵 THREAD (${d.thread_items?.length || d.ai_metadata?.tweets?.length || "multi"})` : d.content_type}
                  </span>
                  {d.ai_metadata?.visual_spec && (
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                      🖼️ 4:5 MEME ({d.ai_metadata.visual_spec.format_type || "visual"})
                    </span>
                  )}
                  {d.ai_metadata?.gif_query && (
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-pink-100 dark:bg-pink-950 text-pink-700 dark:text-pink-300 border border-pink-200 dark:border-pink-800">
                      🎬 GIF: "{d.ai_metadata.gif_query}"
                    </span>
                  )}
                </div>
                <span>{d.created_at ? formatISTTime(d.created_at) : "Just now"}</span>
              </div>

              {(d.content_type === "thread" || d.ai_metadata?.is_thread) && (d.thread_items?.length > 0 || d.ai_metadata?.thread_items?.length > 0 || d.ai_metadata?.tweets?.length > 0) ? (
                <div className="space-y-2 my-2">
                  {(d.thread_items && d.thread_items.length > 0
                    ? d.thread_items
                    : (d.ai_metadata?.thread_items || d.ai_metadata?.tweets || []).map((t: any, i: number, arr: any[]) => ({
                        id: `idx-${i}`,
                        position: i,
                        item_type: i === 0 ? "hook" : i === arr.length - 1 ? "closer" : "body",
                        text: typeof t === 'string' ? t : (t?.text || '')
                      }))
                  ).map((item: any, idx: number, arr: any[]) => (
                    <div key={item.id || idx} className="relative pl-5">
                      {idx < arr.length - 1 && (
                        <div className="absolute left-[8px] top-3.5 bottom-[-8px] w-0.5 bg-purple-200 dark:bg-purple-800/60" />
                      )}
                      <div className="absolute left-0 top-0.5 w-4 h-4 rounded-full bg-purple-100 dark:bg-purple-900 border-2 border-purple-400 dark:border-purple-600 flex items-center justify-center text-[8px] font-bold text-purple-700 dark:text-purple-300">
                        {idx + 1}
                      </div>
                      <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-200/80 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-200">
                        <div className="flex items-center justify-between text-[10px] text-slate-400 mb-0.5 font-mono">
                          <span className="capitalize">{item.item_type || `tweet ${idx + 1}`}</span>
                          <span>{item.text?.length || 0}/280</span>
                        </div>
                        <p className="whitespace-pre-wrap font-medium">{item.text}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs sm:text-sm text-slate-800 dark:text-slate-100 whitespace-pre-wrap font-medium">
                  {d.body}
                </p>
              )}

              {d.ai_metadata?.visual_spec && (
                <div className="p-2.5 rounded-xl bg-blue-600 border border-indigo-200 dark:border-indigo-800/80 my-2 space-y-1 shadow-sm">
                  <div className="flex items-center justify-between text-[10px] font-bold text-indigo-700 dark:text-indigo-300">
                    <span className="flex items-center gap-1">
                      <span>📸 4:5 Visual Punchline ({d.ai_metadata.visual_spec.aspect_ratio || "4:5"} Mobile Takeover)</span>
                    </span>
                    <span className="px-1.5 py-0.5 rounded-md bg-indigo-200/60 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200 capitalize font-mono text-[9px]">
                      {d.ai_metadata.visual_spec.format_type?.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-700 dark:text-slate-200 font-medium leading-relaxed">
                    {d.ai_metadata.visual_spec.image_prompt || d.ai_metadata.visual_spec.visual_description}
                  </p>
                  {d.ai_metadata.visual_spec.one_two_punch_strategy && (
                    <p className="text-[10px] text-indigo-600 dark:text-indigo-400 italic pt-0.5">
                      🎯 Strategy: {d.ai_metadata.visual_spec.one_two_punch_strategy}
                    </p>
                  )}
                </div>
              )}

              {d.ai_metadata?.media_paths && d.ai_metadata.media_paths.length > 0 && (
                <div className="my-2 rounded-xl overflow-hidden border border-indigo-200/80 dark:border-indigo-800/60 bg-slate-900/40">
                  <div className="flex items-center justify-between px-2.5 py-1 bg-indigo-50 dark:bg-indigo-950/60 text-[10px] font-bold text-indigo-700 dark:text-indigo-300 border-b border-indigo-200/60 dark:border-indigo-800/50">
                    <span className="flex items-center gap-1">
                      <ImageIcon className="w-3 h-3 text-indigo-500" />
                      <span>Attached Visual ({d.ai_metadata.media_paths[0].split('/').pop()})</span>
                    </span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-200/60 dark:bg-indigo-900/60 font-mono">
                      {d.ai_metadata.media_paths.length} Asset{d.ai_metadata.media_paths.length > 1 ? "s" : ""}
                    </span>
                  </div>
                  <div className="p-2 flex flex-wrap gap-2 justify-center bg-slate-950/40">
                    {d.ai_metadata.media_paths.map((mPath: string, mIdx: number) => {
                      const cleanRel = mPath.replace(/^.*\/data\//, "");
                      const base = (API_BASE_URL || "").replace(/\/$/, "");
                      const fullUrl = mPath.startsWith("http://") || mPath.startsWith("https://") 
                        ? mPath 
                        : `${base}/data/${cleanRel}`;
                      return (
                        <img
                          key={mIdx}
                          src={fullUrl}
                          alt={`Post Visual Media ${mIdx + 1}`}
                          className="max-h-48 max-w-full rounded-lg object-contain border border-slate-700/50 shadow-md hover:scale-[1.02] transition cursor-pointer"
                          onClick={() => window.open(fullUrl, '_blank')}
                        />
                      );
                    })}
                  </div>
                </div>
              )}

              {d.ai_metadata?.reasoning && (
                <p className="text-[10px] text-slate-500 dark:text-slate-400 italic mt-1.5">
                  💡 {d.ai_metadata.reasoning}
                </p>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              <button
                onClick={() => onDismissDraft(d.id)}
                className="px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                Dismiss
              </button>
              <button
                onClick={() => onApproveDraft(d.id)}
                disabled={approvingId === d.id}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition disabled:opacity-50"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{approvingId === d.id ? "Publishing..." : d.content_type === "thread" ? "Approve & Post Thread" : "Approve & Post"}</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
