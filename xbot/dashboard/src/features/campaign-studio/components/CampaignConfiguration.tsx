import React from "react";
import { Sparkles, AlertCircle, CheckCircle2, Lightbulb, RefreshCw, Search, Flame, BarChart2, MessageSquare } from "lucide-react";
import { Profile } from "@/lib/api";

interface CampaignConfigurationProps {
  selectedProfile: Profile | null;
  errorMessage: string | null;
  publishSuccessMessage: string | null;
  prompt: string;
  setPrompt: (prompt: string) => void;
  isGenerating: boolean;
  handleStartCampaign: () => void;
}

const quickPromptTemplates = [
  {
    icon: Flame,
    label: "Viral Controversy + Media",
    text: "build a thread on giva jewellery kriti senon rakshabandhan controversy with multiple media, and a poll on public reaction",
  },
  {
    icon: BarChart2,
    label: "Tech Launch + Polls",
    text: "a thread and 2 polls on apple upcoming launch event hardware leaks and AI pricing",
  },
  {
    icon: MessageSquare,
    label: "Cinema & Pop Culture Pack",
    text: "multiple posts on toxic film teaser hype, casting expectations, and cinematography",
  },
  {
    icon: Sparkles,
    label: "AI Architecture Breakdown",
    text: "build a deep-dive thread comparing DeepSeek V3 architecture vs GPT-4o with media and a poll",
  },
];

export function CampaignConfiguration({
  selectedProfile,
  errorMessage,
  publishSuccessMessage,
  prompt,
  setPrompt,
  isGenerating,
  handleStartCampaign,
}: CampaignConfigurationProps) {
  return (
    <div className="w-full lg:w-[400px] flex-shrink-0 flex flex-col gap-4 overflow-y-auto h-full pr-1">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                AI Campaign Studio
              </h1>
              <span className="text-[10px] uppercase font-bold text-indigo-600 dark:text-indigo-400">
                Director Mode
              </span>
            </div>
          </div>
          {selectedProfile && (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <div className="w-5 h-5 rounded-full bg-indigo-600 flex items-center justify-center font-bold text-[10px] text-white">
                {selectedProfile.display_name?.charAt(0) || "P"}
              </div>
              <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                @{selectedProfile.x_handle}
              </span>
            </div>
          )}
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
          Write what you want in plain English. AI autonomously decomposes ideas, conducts live X research, and crafts ready-to-publish campaigns.
        </p>
      </div>

      {errorMessage && (
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 flex items-start gap-2.5 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {publishSuccessMessage && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 flex items-start gap-2.5 text-xs">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>{publishSuccessMessage}</span>
        </div>
      )}

      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl space-y-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
              Campaign Directive
            </label>
            <span className="text-[11px] text-slate-400 font-mono">
              {prompt.length} chars
            </span>
          </div>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isGenerating}
            rows={4}
            placeholder="e.g. build a thread on giva jewellery kriti senon controversy with media, and a poll on public reaction..."
            className="w-full p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-950/70 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs leading-relaxed resize-none transition"
          />
        </div>

        <button
          onClick={handleStartCampaign}
          disabled={isGenerating || !prompt.trim()}
          className={`w-full py-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-2 text-white shadow-md transition ${
            isGenerating
              ? "bg-slate-600 cursor-not-allowed opacity-75"
              : "bg-blue-600 hover:bg-blue-700 shadow-blue-500/20 active:scale-[0.99]"
          }`}
        >
          {isGenerating ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              Researching & Crafting...
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5" />
              Research & Generate Campaign
            </>
          )}
        </button>

        <div className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
          <Search className="w-3 h-3 text-sky-400 flex-shrink-0" />
          <span>Autonomously conducts live X search, media retrieval & synthesis</span>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl space-y-3">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
          <Flame className="w-3.5 h-3.5 text-orange-500" />
          Inspiration Templates
        </span>
        <div className="space-y-2">
          {quickPromptTemplates.map((item, idx) => {
            const Icon = item.icon;
            return (
              <button
                key={idx}
                type="button"
                onClick={() => setPrompt(item.text)}
                disabled={isGenerating}
                className="w-full flex items-start gap-2.5 p-2.5 rounded-xl text-left bg-slate-50/70 dark:bg-slate-800/60 hover:bg-indigo-50/70 dark:hover:bg-indigo-950/40 hover:border-indigo-500/40 border border-slate-200/80 dark:border-slate-700/60 transition group cursor-pointer"
              >
                <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white transition mt-0.5">
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-xs text-slate-800 dark:text-slate-200">
                    {item.label}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 mt-0.5">
                    {item.text}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
