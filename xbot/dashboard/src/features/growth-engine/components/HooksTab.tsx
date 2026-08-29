import React from "react";
import { 
  Crosshair, Sparkles, TrendingUp, Vote, Plus, Trash2, 
  RefreshCw, CheckCircle, AlertCircle, ExternalLink, Send, 
  Zap, Layers, ArrowRight, HelpCircle, Check, BadgeCheck, 
  UserCheck, Users, Search 
} from "lucide-react";
import { useHooks } from "../hooks/useHooks";

export function HooksTab({ profileId }: { profileId: string }) {
  const {
    hookDraftText, setHookDraftText,
    hookTopic, setHookTopic,
    hookOptimizing,
    hookCandidates,
    winningHook, setWinningHook,
    optimizedPostResult, setOptimizedPostResult,
    publishingPost,
    postPublishMsg,
    handleOptimizeHooks,
    handlePublishHookPost
  } = useHooks(profileId);

  return (
      <>
        <div className="space-y-6">
          <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-500" />
                  <span>Viral Hook Optimizer (6 Psychological Archetypes)</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">Synthesizes and scores draft hooks using Curiosity Gap, Contrarian, Framework, Authority, Story, and Direct Metric angles.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Topic / Concept
                </label>
                <input
                  type="text"
                  value={hookTopic}
                  onChange={(e) => setHookTopic(e.target.value)}
                  placeholder="Deterministic State in Autonomous AI Agents"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Draft Post Body
                </label>
                <textarea
                  rows={2}
                  value={hookDraftText}
                  onChange={(e) => setHookDraftText(e.target.value)}
                  placeholder="Enter your initial post draft..."
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white resize-none"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleOptimizeHooks}
                disabled={hookOptimizing || (!hookDraftText.trim() && !hookTopic.trim())}
                className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-md shadow-indigo-600/20"
              >
                {hookOptimizing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                <span>Evaluate 6 Archetype Hooks</span>
              </button>
            </div>

            {/* Candidates Grid */}
            {hookCandidates.length > 0 && (
              <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-800">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                    Hook Archetype Scorecard
                  </h4>
                  <span className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
                    Winner: {winningHook?.archetype} ({winningHook?.score}/10)
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {hookCandidates.map((cand) => (
                    <div
                      key={cand.archetype}
                      onClick={() => {
                        setWinningHook(cand);
                        setOptimizedPostResult(`${cand.hook_text}\n\n${hookDraftText}`);
                      }}
                      className={`p-3.5 rounded-xl border transition cursor-pointer ${
                        winningHook?.archetype === cand.archetype
                          ? "border-indigo-500 bg-indigo-50/60 dark:bg-indigo-950/30 ring-1 ring-indigo-500"
                          : "border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 hover:border-slate-300"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-400">
                          {cand.archetype.replace("_", " ")}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-full font-bold bg-indigo-100 dark:bg-indigo-900/60 text-indigo-800 dark:text-indigo-300">
                          {cand.score}/10
                        </span>
                      </div>
                      <p className="text-xs font-medium text-slate-900 dark:text-white">
                        "{cand.hook_text}"
                      </p>
                      <p className="text-[11px] text-slate-500 mt-1.5">{cand.reasoning}</p>
                    </div>
                  ))}
                </div>

                {/* Final Formatted Post Preview & 1-Click Publish */}
                {optimizedPostResult && (
                  <div className="p-4 rounded-xl border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/30 dark:bg-indigo-950/20 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                      <span className="text-xs font-bold text-indigo-700 dark:text-indigo-300">
                        Final Formatted Post Preview ({optimizedPostResult.length} chars)
                      </span>
                      <button
                        onClick={handlePublishHookPost}
                        disabled={publishingPost}
                        className="w-full sm:w-auto px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition disabled:opacity-50 shadow-sm"
                      >
                        {publishingPost ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                        <span>Publish to Live X Timeline</span>
                      </button>
                    </div>

                    <p className="text-xs font-mono text-slate-900 dark:text-white bg-white dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-800 whitespace-pre-wrap">
                      {optimizedPostResult}
                    </p>

                    {postPublishMsg && (
                      <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                        {postPublishMsg}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

</>
  );
}
