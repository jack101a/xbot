"use client";

import React from "react";
import { Search } from "lucide-react";

interface ThreadResearchDossierProps {
  researchReport: any;
  downloadedMedia?: any[];
}

export function ThreadResearchDossier({
  researchReport,
  downloadedMedia,
}: ThreadResearchDossierProps) {
  if (!researchReport) return null;

  return (
    <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/80 border border-purple-200 dark:border-purple-900/50 space-y-3 mt-4">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
          <Search className="w-3.5 h-3.5 text-purple-500" />
          <span>Live X Research Dossier & Proof Grounding</span>
        </h4>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300">
          {researchReport.viral_tweets?.length || 0} Viral Posts Analyzed
        </span>
      </div>

      {researchReport.summary && (
        <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed bg-white dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-800">
          {researchReport.summary}
        </p>
      )}

      {/* Consensus vs Contrarian */}
      {researchReport.community_sentiment && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
          <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/50">
            <span className="text-[10px] font-bold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider block mb-1">
              Dominant X Sentiment (Consensus)
            </span>
            <span className="text-slate-700 dark:text-slate-300 text-[11px]">
              {researchReport.community_sentiment.consensus_view || "General agreement across timeline."}
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50">
            <span className="text-[10px] font-bold text-amber-700 dark:text-amber-400 uppercase tracking-wider block mb-1">
              Contrarian / Industry Critique
            </span>
            <span className="text-slate-700 dark:text-slate-300 text-[11px]">
              {researchReport.community_sentiment.contrarian_view || "Alternative perspective and nuanced arguments."}
            </span>
          </div>
        </div>
      )}

      {/* Downloaded Media / Proof Attachments */}
      {downloadedMedia && downloadedMedia.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Attached Media Assets ({downloadedMedia.length} Images/Statements)
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {downloadedMedia.map((media: any, mIdx: number) => (
              <div
                key={mIdx}
                className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-[11px] space-y-1"
              >
                <img
                  src={media.source_url}
                  alt="Viral Tweet Attachment"
                  className="w-full h-24 object-cover rounded"
                />
                <div className="text-slate-500 text-[10px] truncate">@{media.author_handle}</div>
                <p className="text-slate-700 dark:text-slate-300 line-clamp-2 text-[10px]">
                  {media.caption}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Viral Tweets */}
      {researchReport.viral_tweets && researchReport.viral_tweets.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Top Viral Posts on X
          </span>
          <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
            {researchReport.viral_tweets.slice(0, 6).map((tw: any, tIdx: number) => (
              <div
                key={tIdx}
                className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs flex items-start justify-between gap-2"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5 text-[11px]">
                    <span className="font-bold text-slate-900 dark:text-white">{tw.author}</span>
                    <span className="text-slate-500 font-mono text-[10px]">@{tw.handle}</span>
                    {tw.verified && <span className="text-blue-500 text-[10px]">✓</span>}
                  </div>
                  <p className="text-slate-600 dark:text-slate-300 text-[11px] line-clamp-2">
                    {tw.text}
                  </p>
                </div>
                <div className="text-right whitespace-nowrap text-[10px] text-slate-400 font-mono">
                  <div>{tw.views?.toLocaleString()} views</div>
                  <div>{tw.likes?.toLocaleString()} likes</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
