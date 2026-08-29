"use client";

import React from "react";
import { Zap, Crosshair, RefreshCw, Send } from "lucide-react";

interface SniperSimulatorProps {
  sniperAuthor: string;
  setSniperAuthor: (val: string) => void;
  sniperAngle: string;
  setSniperAngle: (val: any) => void;
  sniperTweetText: string;
  setSniperTweetText: (val: string) => void;
  sniperGenerating: boolean;
  handleGenerateReply: () => void;
  sniperResult: any;
  sniperTargetUrl: string;
  setSniperTargetUrl: (val: string) => void;
  publishingReply: boolean;
  handlePublishLiveReply: () => void;
  replyPublishMsg: string | null;
}

export function SniperSimulator({
  sniperAuthor,
  setSniperAuthor,
  sniperAngle,
  setSniperAngle,
  sniperTweetText,
  setSniperTweetText,
  sniperGenerating,
  handleGenerateReply,
  sniperResult,
  sniperTargetUrl,
  setSniperTargetUrl,
  publishingReply,
  handlePublishLiveReply,
  replyPublishMsg,
}: SniperSimulatorProps) {
  return (
    <div className="lg:col-span-7 space-y-4">
      <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
            <Zap className="w-4 h-4 text-rose-500" />
            <span>Interactive AI Sniper Reply</span>
          </h3>
          <span className="text-xs text-slate-500">Real-time model synthesis</span>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Author Handle
              </label>
              <input
                type="text"
                value={sniperAuthor}
                onChange={(e) => setSniperAuthor(e.target.value)}
                placeholder="sama"
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Sniper Angle
              </label>
              <select
                value={sniperAngle}
                onChange={(e: any) => setSniperAngle(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white"
              >
                <option value="contrarian">Contrarian (Challenge premise)</option>
                <option value="framework">Framework (Structured takeaway)</option>
                <option value="witty">Witty (Sharp cultural take)</option>
                <option value="data">Data (Statistical counter-metric)</option>
                <option value="insight">Insight (System design angle)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Target Tweet Content
            </label>
            <textarea
              rows={3}
              value={sniperTweetText}
              onChange={(e) => setSniperTweetText(e.target.value)}
              placeholder="Paste the tweet text here..."
              className="w-full p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white resize-none"
            />
          </div>

          <div className="flex justify-end items-center pt-1">
            <button
              onClick={handleGenerateReply}
              disabled={sniperGenerating || !sniperTweetText.trim()}
              className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-md shadow-rose-600/20"
            >
              {sniperGenerating ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Crosshair className="w-3.5 h-3.5" />
              )}
              <span>Generate Sniper Reply</span>
            </button>
          </div>
        </div>

        {/* Sniper Output */}
        {sniperResult && (
          <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/40 dark:bg-rose-950/20 space-y-3 animate-in fade-in duration-200">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <span className="text-xs font-bold text-rose-700 dark:text-rose-300 uppercase tracking-wider">
                Generated Sniper Take ({sniperResult.angle_used})
              </span>
              <span className="text-[11px] font-mono text-slate-500">
                {sniperResult.reply_text.length} chars • {Math.round(sniperResult.confidence * 100)}% match
              </span>
            </div>

            <p className="text-xs font-medium text-slate-900 dark:text-white bg-white dark:bg-slate-900 p-3 rounded-lg border border-rose-200 dark:border-rose-900/40 whitespace-pre-wrap">
              {sniperResult.reply_text}
            </p>

            <p className="text-[11px] text-slate-600 dark:text-slate-400 italic">
              Strategy Rationale: {sniperResult.reasoning}
            </p>

            {/* 1-Click Live Publish to X Thread */}
            <div className="pt-2 border-t border-rose-200 dark:border-rose-900/40 space-y-2">
              <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                Target Tweet URL for 1-Click Live Submission:
              </label>
              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  type="text"
                  value={sniperTargetUrl}
                  onChange={(e) => setSniperTargetUrl(e.target.value)}
                  placeholder="https://x.com/username/status/..."
                  className="flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono text-slate-900 dark:text-white"
                />
                <button
                  onClick={handlePublishLiveReply}
                  disabled={publishingReply || !sniperTargetUrl.trim()}
                  className="w-full sm:w-auto px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition disabled:opacity-50 shadow-sm"
                >
                  {publishingReply ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Send className="w-3.5 h-3.5" />
                  )}
                  <span>Publish to Live X</span>
                </button>
              </div>

              {replyPublishMsg && (
                <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mt-1">
                  {replyPublishMsg}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
