"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Sparkles,
  Search,
  Image as ImageIcon,
  CheckCircle2,
  AlertCircle,
  Clock,
  Send,
  Calendar,
  Layers,
  Flame,
  BarChart2,
  MessageSquare,
  RefreshCw,
  Eye,
  ExternalLink,
  ChevronRight,
  ListTree,
  SlidersHorizontal,
  Lightbulb,
  CheckSquare,
  Square,
  FileText
} from "lucide-react";
import { api, Profile } from "@/lib/api";

interface CampaignStudioTabProps {
  selectedProfile: Profile | null;
}

export function CampaignStudioTab({ selectedProfile }: CampaignStudioTabProps) {
  const [prompt, setPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [campaignStatus, setCampaignStatus] = useState<any | null>(null);
  const [selectedDeliverableIds, setSelectedDeliverableIds] = useState<string[]>([]);
  const [publishMode, setPublishMode] = useState<"instant" | "schedule">("schedule");
  const [scheduleInterval, setScheduleInterval] = useState<number>(60);
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishSuccessMessage, setPublishSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

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

  // Poll campaign status when generating
  useEffect(() => {
    if (!campaignId || !isGenerating) {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      return;
    }

    const checkStatus = async () => {
      try {
        const res = await api.getCampaignStatus(campaignId);
        setCampaignStatus(res);

        if (res.status === "ready") {
          setIsGenerating(false);
          // Select all content IDs by default
          const allIds = (res.deliverables || []).map((d: any) => d.content_id).filter(Boolean);
          setSelectedDeliverableIds(allIds);
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        } else if (res.status === "failed") {
          setIsGenerating(false);
          setErrorMessage(res.error || "Campaign generation encountered an error.");
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      } catch (err: any) {
        console.error("Failed to poll campaign status:", err);
      }
    };

    pollIntervalRef.current = setInterval(checkStatus, 2500);
    checkStatus();

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [campaignId, isGenerating]);

  const handleStartCampaign = async () => {
    if (!selectedProfile) {
      setErrorMessage("Please select an active profile first.");
      return;
    }
    if (!prompt.trim() || prompt.length < 5) {
      setErrorMessage("Please enter a descriptive prompt (at least 5 characters).");
      return;
    }

    setErrorMessage(null);
    setPublishSuccessMessage(null);
    setIsGenerating(true);
    setCampaignStatus(null);
    setSelectedDeliverableIds([]);

    try {
      const res = await api.generateCampaign({
        profile_id: selectedProfile.id,
        prompt: prompt.trim(),
      });
      setCampaignId(res.campaign_id);
    } catch (err: any) {
      setIsGenerating(false);
      setErrorMessage(err?.message || "Failed to start campaign generation.");
    }
  };

  const handlePublishDeliverables = async (mode: "instant" | "schedule") => {
    if (!campaignId || selectedDeliverableIds.length === 0) return;

    setIsPublishing(true);
    setPublishSuccessMessage(null);
    setErrorMessage(null);

    try {
      const res = await api.publishCampaign(campaignId, {
        content_ids: selectedDeliverableIds,
        mode: mode,
        interval_minutes: scheduleInterval,
      });

      if (mode === "instant") {
        setPublishSuccessMessage(`🚀 Successfully queued ${res.items_updated} deliverable(s) for immediate publishing!`);
      } else {
        setPublishSuccessMessage(`⏱️ Successfully scheduled ${res.items_updated} deliverable(s) spaced ${scheduleInterval} minutes apart!`);
      }
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to publish deliverables.");
    } finally {
      setIsPublishing(false);
    }
  };

  const toggleSelectDeliverable = (contentId: string) => {
    setSelectedDeliverableIds((prev) =>
      prev.includes(contentId) ? prev.filter((id) => id !== contentId) : [...prev, contentId]
    );
  };

  const selectAllDeliverables = () => {
    if (!campaignStatus?.deliverables) return;
    const allIds = campaignStatus.deliverables.map((d: any) => d.content_id).filter(Boolean);
    setSelectedDeliverableIds(allIds);
  };

  const deselectAllDeliverables = () => {
    setSelectedDeliverableIds([]);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8 animate-fadeIn">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-indigo-900/30 via-slate-900/40 to-violet-950/30 border border-indigo-500/20 p-6 rounded-2xl backdrop-blur-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-black tracking-tight text-slate-100">
              AI Director & Campaign Studio
            </h1>
            <span className="text-xs uppercase font-extrabold px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
              Prompt-to-Campaign
            </span>
          </div>
          <p className="text-sm text-slate-400">
            Write what you want in plain English. AI autonomously decomposes your ideas, scrapes live X research & media, and crafts ready-to-publish campaigns.
          </p>
        </div>

        {selectedProfile && (
          <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-slate-800/80 border border-slate-700/60">
            <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center font-bold text-xs text-white">
              {selectedProfile.display_name?.charAt(0) || "P"}
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-200">Active Persona</div>
              <div className="text-xs text-indigo-400">@{selectedProfile.x_handle}</div>
            </div>
          </div>
        )}
      </div>

      {/* Prompt Console Card */}
      <div className="bg-white/70 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-6 rounded-2xl shadow-sm backdrop-blur-xl space-y-4">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-amber-500" />
            Creator Prompt / Campaign Directive
          </label>
          <span className="text-xs text-slate-400">
            {prompt.length} chars
          </span>
        </div>

        <div className="relative">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isGenerating}
            rows={3}
            placeholder="e.g. build a thread on giva jewellery kriti senon rakshabandhan controversy with multiple media, a thread and some polls on apple upcoming launch event, multiple posts on toxic film..."
            className="w-full p-4 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950/70 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm leading-relaxed resize-none transition"
          />
        </div>

        {/* Quick Inspiration Chips */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-xs font-semibold text-slate-400 flex items-center gap-1 mr-1">
            Quick Ideas:
          </span>
          {quickPromptTemplates.map((item, idx) => {
            const Icon = item.icon;
            return (
              <button
                key={idx}
                type="button"
                onClick={() => setPrompt(item.text)}
                disabled={isGenerating}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 hover:text-indigo-600 dark:hover:text-indigo-400 border border-slate-200 dark:border-slate-700 transition"
              >
                <Icon className="w-3.5 h-3.5 text-indigo-500" />
                {item.label}
              </button>
            );
          })}
        </div>

        {/* Action Button */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800/80">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Search className="w-3.5 h-3.5 text-sky-400" />
            Autonomously executes live X search, media downloads, and persona synthesis
          </div>
          <button
            onClick={handleStartCampaign}
            disabled={isGenerating || !prompt.trim()}
            className={`px-6 py-2.5 rounded-xl font-bold text-sm flex items-center gap-2 text-white shadow-lg transition ${
              isGenerating
                ? "bg-slate-600 cursor-not-allowed opacity-75"
                : "bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 shadow-indigo-500/25"
            }`}
          >
            {isGenerating ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Researching & Crafting...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Research & Generate Campaign
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-3 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Success Alert */}
      {publishSuccessMessage && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-3 text-sm">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span>{publishSuccessMessage}</span>
        </div>
      )}

      {/* Live Research Progress Stepper */}
      {(isGenerating || campaignStatus) && (
        <div className="bg-slate-900/90 border border-indigo-500/30 p-6 rounded-2xl space-y-5 shadow-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-indigo-500 animate-ping" />
              <span className="text-sm font-bold text-slate-200">
                {campaignStatus?.status === "ready"
                  ? "Campaign Ready for Publishing"
                  : "Live Campaign Pipeline in Progress"}
              </span>
            </div>
            <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-950/80 px-2.5 py-1 rounded-full border border-indigo-800/60">
              {campaignStatus?.progress_percent || 0}%
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 via-sky-400 to-emerald-400 transition-all duration-500 ease-out"
              style={{ width: `${campaignStatus?.progress_percent || 5}%` }}
            />
          </div>

          {/* Current Step Message */}
          <div className="text-xs text-slate-300 font-mono flex items-center gap-2 bg-slate-950/60 p-3 rounded-xl border border-slate-800">
            <Search className="w-4 h-4 text-sky-400 animate-pulse flex-shrink-0" />
            <span className="truncate">
              {campaignStatus?.current_step || "Initializing research..."}
            </span>
          </div>

          {/* Plan Highlights */}
          {campaignStatus?.plan && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-slate-800/80">
              <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/50">
                <div className="text-[11px] uppercase font-bold text-slate-400">Campaign Title</div>
                <div className="text-xs font-semibold text-slate-200 mt-0.5 truncate">
                  {campaignStatus.plan.campaign_title}
                </div>
              </div>
              <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/50">
                <div className="text-[11px] uppercase font-bold text-slate-400">Theme</div>
                <div className="text-xs font-semibold text-slate-200 mt-0.5 truncate">
                  {campaignStatus.plan.theme}
                </div>
              </div>
              <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/50">
                <div className="text-[11px] uppercase font-bold text-slate-400">Deliverables</div>
                <div className="text-xs font-semibold text-indigo-300 mt-0.5">
                  {campaignStatus.plan.deliverables?.length || 0} Assets Planned
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Generated Deliverables Board */}
      {campaignStatus?.deliverables && campaignStatus.deliverables.length > 0 && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                <Layers className="w-5 h-5 text-indigo-400" />
                Generated Campaign Deliverables ({campaignStatus.deliverables.length})
              </h2>
              <p className="text-xs text-slate-400">
                Select items to publish instantly or auto-schedule with custom spacing.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={selectAllDeliverables}
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 px-2.5 py-1.5 rounded-lg bg-indigo-950/40 border border-indigo-800/40 transition"
              >
                Select All
              </button>
              <button
                onClick={deselectAllDeliverables}
                className="text-xs font-semibold text-slate-400 hover:text-slate-300 px-2.5 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/40 transition"
              >
                Clear
              </button>
            </div>
          </div>

          {/* Deliverables Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {campaignStatus.deliverables.map((item: any, idx: number) => {
              const isSelected = selectedDeliverableIds.includes(item.content_id);
              const isThread = item.type === "thread";
              const isPoll = item.type === "poll";
              const isVisual = item.type === "visual";

              return (
                <div
                  key={idx}
                  onClick={() => toggleSelectDeliverable(item.content_id)}
                  className={`p-5 rounded-2xl border transition cursor-pointer relative backdrop-blur-xl ${
                    isSelected
                      ? "border-indigo-500 bg-indigo-950/20 shadow-lg shadow-indigo-500/10"
                      : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
                  }`}
                >
                  {/* Card Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-5 h-5 rounded flex items-center justify-center transition ${
                          isSelected ? "text-indigo-400" : "text-slate-600"
                        }`}
                      >
                        {isSelected ? <CheckSquare className="w-5 h-5" /> : <Square className="w-5 h-5" />}
                      </div>
                      <span
                        className={`text-[11px] font-extrabold uppercase px-2 py-0.5 rounded-full border ${
                          isThread
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                            : isPoll
                            ? "bg-sky-500/10 text-sky-400 border-sky-500/30"
                            : isVisual
                            ? "bg-violet-500/10 text-violet-400 border-violet-500/30"
                            : "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                        }`}
                      >
                        {item.type}
                      </span>
                    </div>

                    <span className="text-xs text-slate-400 font-mono">
                      #{idx + 1}
                    </span>
                  </div>

                  {/* Topic Title */}
                  <h3 className="text-sm font-bold text-slate-200 mb-3 line-clamp-1">
                    {item.topic}
                  </h3>

                  {/* Content Preview Body */}
                  {isThread && item.thread_tweets ? (
                    <div className="space-y-3 pl-3 border-l-2 border-amber-500/40 my-2">
                      {item.thread_tweets.map((tw: string, tIdx: number) => (
                        <div key={tIdx} className="text-xs text-slate-300 leading-relaxed font-sans">
                          {tw}
                        </div>
                      ))}
                    </div>
                  ) : isPoll ? (
                    <div className="space-y-2 my-2 p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                      <div className="text-xs font-semibold text-slate-200">{item.question || item.text}</div>
                      <div className="space-y-1.5 pt-1">
                        {(item.options || ["Option 1", "Option 2"]).map((opt: string, optIdx: number) => (
                          <div
                            key={optIdx}
                            className="p-2 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs text-slate-300 flex items-center justify-between"
                          >
                            <span>{opt}</span>
                            <span className="text-[10px] text-slate-500 font-mono">Option {optIdx + 1}</span>
                          </div>
                        ))}
                      </div>
                      <div className="text-[10px] text-slate-500 pt-1">
                        📊 7-Day Interactive Community Poll
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap font-sans my-2">
                      {item.text}
                    </div>
                  )}

                  {/* Media Preview Tag */}
                  {item.media_paths && item.media_paths.length > 0 && (
                    <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-slate-800/60 text-xs text-indigo-400 font-medium">
                      <ImageIcon className="w-3.5 h-3.5" />
                      <span>{item.media_paths.length} Scraped Viral Media Asset(s) Attached</span>
                    </div>
                  )}

                  {/* 1st-Reply Link Badge */}
                  {item.extracted_link && (
                    <div className="flex items-center gap-1.5 mt-2 text-xs text-sky-400 font-mono">
                      <ExternalLink className="w-3 h-3" />
                      <span className="truncate">1st-Reply: {item.extracted_link}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Sticky Campaign Publish Bar */}
          <div className="sticky bottom-4 z-20 bg-slate-900/95 border border-indigo-500/40 p-4 rounded-2xl backdrop-blur-2xl shadow-2xl flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="text-xs font-bold text-slate-300">
                {selectedDeliverableIds.length} of {campaignStatus.deliverables.length} Deliverables Selected
              </span>
              <div className="h-4 w-px bg-slate-700 hidden sm:block" />
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <span>Spacing:</span>
                <select
                  value={scheduleInterval}
                  onChange={(e) => setScheduleInterval(Number(e.target.value))}
                  className="bg-slate-800 border border-slate-700 text-slate-200 rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value={30}>30 mins</option>
                  <option value={60}>60 mins (Recommended)</option>
                  <option value={120}>2 hours</option>
                  <option value={240}>4 hours</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto">
              <button
                onClick={() => handlePublishDeliverables("instant")}
                disabled={isPublishing || selectedDeliverableIds.length === 0}
                className="flex-1 md:flex-initial px-4 py-2 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center justify-center gap-1.5 transition disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5 text-sky-400" />
                Publish Selected Now
              </button>

              <button
                onClick={() => handlePublishDeliverables("schedule")}
                disabled={isPublishing || selectedDeliverableIds.length === 0}
                className="flex-1 md:flex-initial px-5 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-1.5 transition disabled:opacity-50"
              >
                <Calendar className="w-3.5 h-3.5" />
                Auto-Schedule ({scheduleInterval}m Spacing)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
