import React, { useEffect } from "react";
import {
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Lightbulb,
  RefreshCw,
  Search,
  Flame,
  BarChart2,
  MessageSquare,
  TrendingUp,
  Clock,
  Image as ImageIcon,
  Check,
} from "lucide-react";
import { Profile } from "@/lib/api";
import { TrendRadarItem } from "../types";

interface CampaignConfigurationProps {
  selectedProfile: Profile | null;
  errorMessage: string | null;
  publishSuccessMessage: string | null;
  prompt: string;
  setPrompt: (prompt: string) => void;
  durationHours: number;
  setDurationHours: (hours: number) => void;
  intervalMinutes: number;
  setIntervalMinutes: (mins: number) => void;
  sourceType: "on_demand" | "trend_radar";
  setSourceType: (type: "on_demand" | "trend_radar") => void;
  mediaPreference: "x_official" | "ai_generated";
  setMediaPreference: (pref: "x_official" | "ai_generated") => void;
  isGenerating: boolean;
  handleStartCampaign: () => void;
  liveTrends: TrendRadarItem[];
  loadingTrends: boolean;
  fetchLiveTrends: () => void;
  handleSelectTrend: (trend: TrendRadarItem) => void;
}

const quickPromptTemplates = [
  {
    icon: Flame,
    label: "Box Office & Entertainment Surge",
    text: "Nolan's the Odyssey about to cross and become universal studios highest grossing box office movie with official stills and trailer reactions",
  },
  {
    icon: BarChart2,
    label: "Tech Event & Keynote Leaks",
    text: "breakdown of upcoming hardware announcements, benchmarks, pricing leaks, and public community polls",
  },
  {
    icon: MessageSquare,
    label: "Viral Pop Culture Controversy",
    text: "build a multi-perspective thread analyzing current trending public debate with authentic quote media and sentiment poll",
  },
  {
    icon: Sparkles,
    label: "Autonomous AI & Open Source",
    text: "deep-dive thread comparing new open-weights reasoning architecture with official benchmark screenshots and a poll",
  },
];

export function CampaignConfiguration({
  selectedProfile,
  errorMessage,
  publishSuccessMessage,
  prompt,
  setPrompt,
  durationHours,
  setDurationHours,
  intervalMinutes,
  setIntervalMinutes,
  sourceType,
  setSourceType,
  mediaPreference,
  setMediaPreference,
  isGenerating,
  handleStartCampaign,
  liveTrends,
  loadingTrends,
  fetchLiveTrends,
  handleSelectTrend,
}: CampaignConfigurationProps) {
  useEffect(() => {
    if (sourceType === "trend_radar" && liveTrends.length === 0 && !loadingTrends) {
      fetchLiveTrends();
    }
  }, [sourceType, liveTrends.length, loadingTrends, fetchLiveTrends]);

  return (
    <div className="w-full lg:w-[420px] flex-shrink-0 flex flex-col gap-4 overflow-y-auto h-full pr-1">
      {/* Studio Header Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                AI Campaign Studio
              </h1>
              <span className="text-[10px] uppercase font-bold text-sky-600 dark:text-sky-400 tracking-wider">
                Unified Trend & Growth Engine
              </span>
            </div>
          </div>
          {selectedProfile && (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <div className="w-5 h-5 rounded-full bg-sky-600 flex items-center justify-center font-bold text-[10px] text-white">
                {selectedProfile.display_name?.charAt(0) || "P"}
              </div>
              <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                @{selectedProfile.x_handle}
              </span>
            </div>
          )}
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
          Autonomous campaign orchestrator. Decomposes directives, scans live X trends, scrapes original studio media, and runs multi-day campaigns.
        </p>

        {/* Source Mode Tabs */}
        <div className="grid grid-cols-2 gap-1 p-1 bg-slate-100 dark:bg-slate-950/70 rounded-xl border border-slate-200/80 dark:border-slate-800">
          <button
            type="button"
            onClick={() => setSourceType("on_demand")}
            className={`py-1.5 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
              sourceType === "on_demand"
                ? "bg-white dark:bg-slate-800 text-sky-600 dark:text-sky-400 shadow-sm"
                : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
            }`}
          >
            <Lightbulb className="w-3.5 h-3.5" />
            <span>Custom Directive</span>
          </button>
          <button
            type="button"
            onClick={() => setSourceType("trend_radar")}
            className={`py-1.5 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 ${
              sourceType === "trend_radar"
                ? "bg-white dark:bg-slate-800 text-sky-600 dark:text-sky-400 shadow-sm"
                : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Live Trend Radar</span>
            {liveTrends.length > 0 && (
              <span className="ml-0.5 px-1.5 py-0.2 rounded-full text-[9px] bg-sky-100 dark:bg-sky-950 text-sky-700 dark:text-sky-300">
                {liveTrends.length}
              </span>
            )}
          </button>
        </div>
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

      {/* Main Mode Area */}
      {sourceType === "trend_radar" ? (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-sky-500" />
              Live Curated Trends
            </span>
            <button
              type="button"
              onClick={() => fetchLiveTrends()}
              disabled={loadingTrends}
              className="text-xs text-sky-600 dark:text-sky-400 hover:underline flex items-center gap-1 disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${loadingTrends ? "animate-spin" : ""}`} />
              <span>Scan Radar</span>
            </button>
          </div>

          {loadingTrends && liveTrends.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-400 flex flex-col items-center justify-center gap-2">
              <RefreshCw className="w-5 h-5 animate-spin text-sky-500" />
              <span>Scanning live feeds & evaluating persona alignment...</span>
            </div>
          ) : liveTrends.length === 0 ? (
            <div className="p-5 text-center text-xs text-slate-400 rounded-xl border border-dashed border-slate-200 dark:border-slate-800 space-y-2">
              <p>No active trends detected right now.</p>
              <button
                type="button"
                onClick={() => fetchLiveTrends()}
                className="px-3 py-1.5 rounded-lg bg-sky-600 text-white font-bold text-xs hover:bg-sky-700 transition inline-flex items-center gap-1"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Fetch Feeds</span>
              </button>
            </div>
          ) : (
            <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
              {liveTrends.map((trend, idx) => {
                const isSelected = prompt === trend.title;
                return (
                  <div
                    key={idx}
                    onClick={() => handleSelectTrend(trend)}
                    className={`p-3 rounded-xl border text-left cursor-pointer transition space-y-1.5 ${
                      isSelected
                        ? "border-sky-500 bg-sky-50/50 dark:bg-sky-950/40 shadow-sm"
                        : "border-slate-200/80 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-950/30 hover:border-sky-400"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 truncate">
                        {trend.category || "Hot Topic"}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-100 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-400 flex-shrink-0">
                        {trend.alignment_score}% match
                      </span>
                    </div>
                    <div className="font-semibold text-xs text-slate-800 dark:text-slate-100 line-clamp-2">
                      {trend.title}
                    </div>
                    {trend.recommended_angle && (
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1 italic">
                        Angle: {trend.recommended_angle}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : null}

      {/* Directive Text Area */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
            Target Topic / Campaign Directive
          </label>
          <span className="text-[11px] text-slate-400 font-mono">
            {prompt.length} chars
          </span>
        </div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={isGenerating}
          rows={3}
          placeholder="e.g. Nolan's the Odyssey box office surge, casting reactions, and trailer analysis with authentic official stills..."
          className="w-full p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-950/70 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 text-xs leading-relaxed resize-none transition"
        />
      </div>

      {/* Campaign Horizon & Multi-Day Controls */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-sky-500" />
            Campaign Horizon & Cadence
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
            {durationHours === 0 ? "Instant Sprint" : `${durationHours}h Continuous`}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setDurationHours(0)}
            className={`p-2.5 rounded-xl border text-left transition ${
              durationHours === 0
                ? "border-sky-500 bg-sky-50/50 dark:bg-sky-950/40 text-sky-700 dark:text-sky-300 font-bold"
                : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 text-slate-600 dark:text-slate-400"
            }`}
          >
            <div className="text-xs font-semibold">⚡ Sprint Pack</div>
            <div className="text-[10px] opacity-80 mt-0.5">Instant 6-asset batch</div>
          </button>

          <button
            type="button"
            onClick={() => setDurationHours(durationHours > 0 ? durationHours : 48)}
            className={`p-2.5 rounded-xl border text-left transition ${
              durationHours > 0
                ? "border-sky-500 bg-sky-50/50 dark:bg-sky-950/40 text-sky-700 dark:text-sky-300 font-bold"
                : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 text-slate-600 dark:text-slate-400"
            }`}
          >
            <div className="text-xs font-semibold">🔁 Multi-Day Continuous</div>
            <div className="text-[10px] opacity-80 mt-0.5">Autonomous schedule</div>
          </button>
        </div>

        {durationHours > 0 && (
          <div className="grid grid-cols-2 gap-2 pt-1">
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase">
                Duration
              </label>
              <select
                value={durationHours}
                onChange={(e) => setDurationHours(Number(e.target.value))}
                className="w-full px-2.5 py-1.5 rounded-lg text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-sky-500 font-medium"
              >
                <option value={12}>12 Hours</option>
                <option value={24}>24 Hours (1 Day)</option>
                <option value={48}>48 Hours (2 Days)</option>
                <option value={72}>72 Hours (3 Days)</option>
                <option value={168}>168 Hours (7 Days)</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase">
                Drop Interval
              </label>
              <select
                value={intervalMinutes}
                onChange={(e) => setIntervalMinutes(Number(e.target.value))}
                className="w-full px-2.5 py-1.5 rounded-lg text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-sky-500 font-medium"
              >
                <option value={15}>Every 15 mins</option>
                <option value={30}>Every 30 mins</option>
                <option value={60}>Every 1 hour</option>
                <option value={120}>Every 2 hours</option>
                <option value={240}>Every 4 hours</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Media Sourcing Preference */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <ImageIcon className="w-3.5 h-3.5 text-emerald-500" />
            Media Asset Sourcing
          </span>
          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded">
            {mediaPreference === "x_official" ? "Authentic First" : "AI Art"}
          </span>
        </div>

        <div className="space-y-2">
          <div
            onClick={() => setMediaPreference("x_official")}
            className={`p-2.5 rounded-xl border text-left cursor-pointer transition flex items-start gap-2.5 ${
              mediaPreference === "x_official"
                ? "border-emerald-500 bg-emerald-50/40 dark:bg-emerald-950/30"
                : "border-slate-200 dark:border-slate-700 hover:border-slate-300"
            }`}
          >
            <div className={`w-4 h-4 rounded-full border flex items-center justify-center mt-0.5 flex-shrink-0 ${
              mediaPreference === "x_official"
                ? "border-emerald-500 bg-emerald-500 text-white"
                : "border-slate-400"
            }`}>
              {mediaPreference === "x_official" && <Check className="w-2.5 h-2.5" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                <span>Authentic X & Official Media First</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 uppercase font-bold">
                  Recommended
                </span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">
                Scrapes original high-resolution stills from verified studio handles and top X posts (pbs.twimg.com original quality).
              </p>
            </div>
          </div>

          <div
            onClick={() => setMediaPreference("ai_generated")}
            className={`p-2.5 rounded-xl border text-left cursor-pointer transition flex items-start gap-2.5 ${
              mediaPreference === "ai_generated"
                ? "border-sky-500 bg-sky-50/40 dark:bg-sky-950/30"
                : "border-slate-200 dark:border-slate-700 hover:border-slate-300"
            }`}
          >
            <div className={`w-4 h-4 rounded-full border flex items-center justify-center mt-0.5 flex-shrink-0 ${
              mediaPreference === "ai_generated"
                ? "border-sky-500 bg-sky-500 text-white"
                : "border-slate-400"
            }`}>
              {mediaPreference === "ai_generated" && <Check className="w-2.5 h-2.5" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-bold text-slate-800 dark:text-slate-200">
                AI Generated Visuals Fallback
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">
                Uses AI visual generators when authentic studio stills are not required or unavailable.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Action Launch Button */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl space-y-3">
        <button
          onClick={handleStartCampaign}
          disabled={isGenerating || !prompt.trim()}
          className={`w-full py-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 text-white shadow-md transition ${
            isGenerating
              ? "bg-slate-600 cursor-not-allowed opacity-75"
              : "bg-sky-600 hover:bg-sky-700 shadow-sky-600/20 active:scale-[0.99]"
          }`}
        >
          {isGenerating ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Researching X & Assembling Campaign...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>
                {durationHours > 0
                  ? `Launch ${durationHours}h Continuous Campaign`
                  : "Research & Generate Campaign"}
              </span>
            </>
          )}
        </button>

        <div className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1.5 justify-center">
          <Search className="w-3 h-3 text-sky-500 flex-shrink-0" />
          <span>Real-time X query search + authentic media extraction</span>
        </div>
      </div>

      {/* Quick Templates */}
      {sourceType === "on_demand" && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <Flame className="w-3.5 h-3.5 text-amber-500" />
            Viral Template Directives
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
                  className="w-full flex items-start gap-2.5 p-2.5 rounded-xl text-left bg-slate-50/70 dark:bg-slate-800/60 hover:bg-sky-50/70 dark:hover:bg-sky-950/40 hover:border-sky-500/40 border border-slate-200/80 dark:border-slate-700/60 transition group cursor-pointer"
                >
                  <div className="p-1.5 rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400 group-hover:bg-sky-600 group-hover:text-white transition mt-0.5">
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
      )}
    </div>
  );
}
