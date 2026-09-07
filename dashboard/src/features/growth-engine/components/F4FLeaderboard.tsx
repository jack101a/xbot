import React from "react";
import { Zap, BadgeCheck, ExternalLink, RefreshCw } from "lucide-react";

export function F4FLeaderboard({
  f4fGrowthPosts,
  harvestingPostId,
  handleHarvestGrowthPost
}: {
  f4fGrowthPosts: any[];
  harvestingPostId: string | null;
  handleHarvestGrowthPost: (postId: string, tweetUrl: string) => void;
}) {
  return (
    <>
      {/* Active Growth & Follow-Back Trains Hunter Card */}
      {f4fGrowthPosts && f4fGrowthPosts.length > 0 && (
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-amber-500/30 shadow-md space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
                    <Zap className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-bold text-xs text-amber-300 flex items-center gap-1.5">
                      <span>Live Growth Posts & Follow-Back Trains</span>
                      <span className="px-2 py-0.2 rounded-full text-[9px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase">
                        High Reciprocity (80%+)
                      </span>
                    </h4>
                    <p className="text-[11px] text-slate-400">
                      Active threads where creators and participants are explicitly asking for mutual follow-backs.
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {f4fGrowthPosts.map((post) => (
                  <div
                    key={post.id}
                    className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between space-y-2.5 hover:border-amber-500/50 transition"
                  >
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1.5 font-bold text-slate-200">
                          <span>{post.author_name}</span>
                          {post.is_blue_tick && (
                            <BadgeCheck className="w-3.5 h-3.5 text-blue-500" />
                          )}
                          <span className="text-[10px] text-slate-500 font-mono">@{post.author_handle}</span>
                        </div>
                        <span className="text-[10px] text-slate-400">{post.posted_ago}</span>
                      </div>

                      <p className="text-xs text-slate-300 whitespace-pre-line leading-relaxed font-sans">
                        {post.tweet_text}
                      </p>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-[10px] text-slate-400">
                      <div className="flex items-center gap-3 font-mono">
                        <span>💬 {post.reply_count} replies</span>
                        <span>🔄 {post.retweet_count} reposts</span>
                        <span>❤️ {post.like_count}</span>
                      </div>

                      <div className="flex items-center gap-2">
                        <a
                          href={post.tweet_url}
                          target="_blank"
                          rel="noreferrer"
                          className="hover:text-amber-400 flex items-center gap-1 text-[11px] font-semibold"
                        >
                          <span>View Thread</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                        <button
                          onClick={() => handleHarvestGrowthPost(post.id, post.tweet_url)}
                          disabled={harvestingPostId === post.id}
                          className="px-2.5 py-1 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-[11px] font-bold flex items-center gap-1 transition disabled:opacity-50"
                        >
                          <RefreshCw className={`w-3 h-3 ${harvestingPostId === post.id ? "animate-spin" : ""}`} />
                          <span>{harvestingPostId === post.id ? "Harvesting..." : "Harvest Blue Ticks"}</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
    </>
  );
}
