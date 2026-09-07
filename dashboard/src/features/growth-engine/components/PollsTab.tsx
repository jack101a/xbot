import React from "react";
import { 
  Crosshair, Sparkles, TrendingUp, Vote, Plus, Trash2, 
  RefreshCw, CheckCircle, AlertCircle, ExternalLink, Send, 
  Zap, Layers, ArrowRight, HelpCircle, Check, BadgeCheck, 
  UserCheck, Users, Search 
} from "lucide-react";
import { usePolls } from "../hooks/usePolls";

export function PollsTab({ profileId }: { profileId: string }) {
  const {
    pollTopic, setPollTopic,
    generatingPoll,
    generatedPoll,
    publishingPoll,
    pollSuccessMsg,
    handleGeneratePoll,
    handlePublishLivePoll
  } = usePolls(profileId);

  return (
      <>
        <div className="space-y-6">
          <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                  <Vote className="w-4 h-4 text-emerald-500" />
                  <span>Native X Poll Generator</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">Automatically formulates debate-provoking questions with strictly compliant options (all &le; 25 chars).</p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-2.5">
              <input
                type="text"
                value={pollTopic}
                onChange={(e) => setPollTopic(e.target.value)}
                placeholder="Topic: eg. Dominant AI Agent Runtime Architecture in 2026"
                className="flex-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white"
              />
              <button
                onClick={handleGeneratePoll}
                disabled={generatingPoll}
                className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-md shadow-emerald-600/20"
              >
                {generatingPoll ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Vote className="w-4 h-4" />}
                <span>Generate Native Poll</span>
              </button>
            </div>

            {/* Generated Poll Preview */}
            {generatedPoll && (
              <div className="p-4 sm:p-5 rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/40 dark:bg-emerald-950/20 space-y-4">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                    Poll Question ({generatedPoll.question.length} chars)
                  </span>
                  <h4 className="font-bold text-sm text-slate-900 dark:text-white mt-1">
                    {generatedPoll.question}
                  </h4>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {generatedPoll.options.map((opt, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-between"
                    >
                      <span className="text-xs font-medium text-slate-900 dark:text-white truncate mr-2">
                        {opt}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400 flex-shrink-0">
                        {opt.length}/25 chars
                      </span>
                    </div>
                  ))}
                </div>

                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2 border-t border-emerald-200 dark:border-emerald-900/40">
                  <span className="text-xs text-slate-500">
                    Duration: {generatedPoll.duration_days || 1} day • {generatedPoll.reasoning || "Drives high engagement votes"}
                  </span>
                  <button
                    onClick={handlePublishLivePoll}
                    disabled={publishingPoll}
                    className="w-full sm:w-auto px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition disabled:opacity-50 shadow-sm"
                  >
                    {publishingPoll ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                    <span>Publish Poll to Live X</span>
                  </button>
                </div>

                {pollSuccessMsg && (
                  <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                    {pollSuccessMsg}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

</>
  );
}
