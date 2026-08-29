"use client";

import React from "react";
import { Sparkles, RefreshCw, Send, Layers } from "lucide-react";
import { useThreads } from "../hooks/useThreads";
import { ThreadResearchDossier } from "./ThreadResearchDossier";

export function ThreadsTab({ profileId }: { profileId: string }) {
  const {
    threadTopic,
    setThreadTopic,
    threadArchetype,
    setThreadArchetype,
    threadNumTweets,
    setThreadNumTweets,
    threadDeepResearch,
    setThreadDeepResearch,
    threadGenerating,
    threadResult,
    publishingThread,
    threadPublishMsg,
    handleGenerateThread,
    handleUpdateThreadTweet,
    handlePublishLiveThread,
  } = useThreads(profileId);

  return (
    <div className="space-y-6">
      <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-500" />
              <span>3-Tier Multi-Tweet Thread Generator</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Synthesizes high-retention threads (Hook &rarr; Atomic Bullet Takeaways &rarr; Conversion Closer & CTA) with strict Anti-AI typography.
            </p>
          </div>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-50 dark:bg-purple-950/50 text-purple-600 dark:text-purple-400 font-bold">
            Viral 3-Tier Formula
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
          <div className="md:col-span-6">
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Thread Topic or Core Thesis
            </label>
            <input
              type="text"
              value={threadTopic}
              onChange={(e) => setThreadTopic(e.target.value)}
              placeholder="e.g. Why 90% of Autonomous AI Agents Fail in Production"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white"
            />
          </div>

          <div className="md:col-span-3">
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Thread Archetype
            </label>
            <select
              value={threadArchetype}
              onChange={(e) => setThreadArchetype(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white"
            >
              <option value="Framework">Framework / Systems</option>
              <option value="Contrarian Breakdown">Contrarian Breakdown</option>
              <option value="Case Study">Case Study / Proof</option>
              <option value="Tactical Guide">Tactical Step-by-Step</option>
            </select>
          </div>

          <div className="md:col-span-3">
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Number of Tweets ({threadNumTweets})
            </label>
            <input
              type="range"
              min={3}
              max={6}
              value={threadNumTweets}
              onChange={(e) => setThreadNumTweets(Number(e.target.value))}
              className="w-full mt-2 accent-purple-600"
            />
          </div>
        </div>

        <div className="flex items-center justify-between flex-wrap gap-3 pt-2">
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={threadDeepResearch}
              onChange={(e) => setThreadDeepResearch(e.target.checked)}
              className="w-4 h-4 rounded text-purple-600 focus:ring-purple-500 accent-purple-600"
            />
            <span className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-purple-500" />
              <span>Deep Research on X (Live 20-30 Viral Posts, Media & Sentiment)</span>
            </span>
          </label>

          <button
            onClick={handleGenerateThread}
            disabled={threadGenerating || !threadTopic.trim()}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-md shadow-purple-600/20"
          >
            {threadGenerating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Layers className="w-4 h-4" />}
            <span>Generate {threadNumTweets}-Tweet Thread</span>
          </button>
        </div>

        {/* Generated Thread Canvas */}
        {threadResult && (
          <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900 dark:text-white">
                  Generated Thread ({threadResult.tweets.length} Tweets)
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-400">
                  Hook Score: {threadResult.hook_score}/100
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                  {threadResult.archetype}
                </span>
              </div>

              <button
                onClick={handlePublishLiveThread}
                disabled={publishingThread}
                className="w-full sm:w-auto px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition disabled:opacity-50 shadow-sm"
              >
                {publishingThread ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                <span>Publish Multi-Tweet Thread to Live X</span>
              </button>
            </div>

            {threadPublishMsg && (
              <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-semibold">
                {threadPublishMsg}
              </div>
            )}

            {/* Connected Vertical Spine Cards */}
            <div className="space-y-3 relative pl-6 my-2">
              {threadResult.tweets.map((tweetText, idx) => (
                <div key={idx} className="relative">
                  {idx < threadResult.tweets.length - 1 && (
                    <div className="absolute left-[-15px] top-6 bottom-[-16px] w-0.5 bg-purple-200 dark:bg-purple-800/60" />
                  )}
                  <div className="absolute left-[-24px] top-3 w-5 h-5 rounded-full bg-purple-100 dark:bg-purple-900 border-2 border-purple-400 dark:border-purple-600 flex items-center justify-center text-[10px] font-bold text-purple-700 dark:text-purple-300">
                    {idx + 1}
                  </div>

                  <div className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/60 space-y-2">
                    <div className="flex items-center justify-between text-[11px] text-slate-500">
                      <span className="font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
                        {idx === 0
                          ? "Tweet 1 (Viral Hook)"
                          : idx === threadResult.tweets.length - 1
                          ? `Tweet ${idx + 1} (Conversion Closer & CTA)`
                          : `Tweet ${idx + 1} (Atomic Takeaway)`}
                      </span>
                      <span className="font-mono text-[10px]">{tweetText.length}/280 chars</span>
                    </div>
                    <textarea
                      rows={3}
                      value={tweetText}
                      onChange={(e) => handleUpdateThreadTweet(idx, e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono text-slate-900 dark:text-white resize-none"
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Live X Research Dossier */}
            <ThreadResearchDossier
              researchReport={threadResult.research_report}
              downloadedMedia={threadResult.downloaded_media}
            />
          </div>
        )}
      </div>
    </div>
  );
}
