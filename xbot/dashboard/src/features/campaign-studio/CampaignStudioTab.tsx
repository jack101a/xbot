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
  const [publishingItemIds, setPublishingItemIds] = useState<string[]>([]);
  const [publishedStatus, setPublishedStatus] = useState<Record<string, string>>({});
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
    setPublishedStatus({});

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

  const handlePublishSingleDeliverable = async (contentId: string, mode: "instant" | "schedule") => {
    if (!contentId) return;
    setPublishingItemIds((prev) => [...prev, contentId]);
    setErrorMessage(null);
    setPublishSuccessMessage(null);

    try {
      if (campaignId) {
        await api.publishCampaign(campaignId, {
          content_ids: [contentId],
          mode: mode,
          interval_minutes: scheduleInterval,
        });
      } else if (selectedProfile) {
        await api.approveDraft(selectedProfile.id, contentId);
      }
      setPublishedStatus((prev) => ({
        ...prev,
        [contentId]: mode === "instant" ? "Queued for Live X" : "Scheduled",
      }));
      setPublishSuccessMessage(
        `🚀 Successfully ${mode === "instant" ? "queued deliverable for immediate publishing" : "scheduled deliverable"}!`
      );
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to publish deliverable.");
    } finally {
      setPublishingItemIds((prev) => prev.filter((id) => id !== contentId));
    }
  };

  const handlePublishDeliverables = async (mode: "instant" | "schedule") => {
    let targetIds = selectedDeliverableIds;
    if (targetIds.length === 0 && campaignStatus?.deliverables?.length) {
      targetIds = campaignStatus.deliverables.map((d: any) => d.content_id).filter(Boolean);
      setSelectedDeliverableIds(targetIds);
    }

    if (targetIds.length === 0) {
      setErrorMessage("Please select at least one deliverable to publish or schedule.");
      return;
    }

    setIsPublishing(true);
    setPublishSuccessMessage(null);
    setErrorMessage(null);

    try {
      let itemsCount = targetIds.length;
      if (campaignId) {
        const res = await api.publishCampaign(campaignId, {
          content_ids: targetIds,
          mode: mode,
          interval_minutes: scheduleInterval,
        });
        itemsCount = res.items_updated || itemsCount;
      } else if (selectedProfile) {
        for (const cid of targetIds) {
          await api.approveDraft(selectedProfile.id, cid);
        }
      }

      const newStatuses: Record<string, string> = {};
      for (const cid of targetIds) {
        newStatuses[cid] = mode === "instant" ? "Queued for Live X" : "Scheduled";
      }
      setPublishedStatus((prev) => ({ ...prev, ...newStatuses }));

      if (mode === "instant") {
        setPublishSuccessMessage(`🚀 Successfully queued ${itemsCount} deliverable(s) for immediate publishing to live X!`);
      } else {
        setPublishSuccessMessage(`⏱️ Successfully scheduled ${itemsCount} deliverable(s) spaced ${scheduleInterval} minutes apart!`);
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
    <div className="flex flex-col lg:flex-row gap-4 lg:h-[calc(100vh-120px)] items-start">
      {/* Left Pane (Configuration) */}
      <div className="w-full lg:w-[400px] flex-shrink-0 flex flex-col gap-4 overflow-y-auto h-full pr-1">
        {/* Header / Persona info */}
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

        {/* Error Alert */}
        {errorMessage && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 flex items-start gap-2.5 text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Success Alert */}
        {publishSuccessMessage && (
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 flex items-start gap-2.5 text-xs">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{publishSuccessMessage}</span>
          </div>
        )}

        {/* Creator Directive / Prompt Card */}
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

          {/* Action Button */}
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

        {/* Quick Inspiration Templates */}
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

      {/* Right Pane (Results & Publishing) */}
      <div className="flex-1 w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 overflow-y-auto h-full flex flex-col">
        {/* Pipeline Progress Stepper */}
        {(isGenerating || campaignStatus) && (
          <div className="bg-slate-900 border border-indigo-500/30 p-4 rounded-xl space-y-3 shadow-sm mb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-ping" />
                <span className="text-xs font-bold text-slate-200">
                  {campaignStatus?.status === "ready"
                    ? "Campaign Ready for Publishing"
                    : "Live Campaign Pipeline in Progress"}
                </span>
              </div>
              <span className="text-[11px] font-mono font-bold text-indigo-400 bg-indigo-950/80 px-2 py-0.5 rounded-full border border-indigo-800/60">
                {campaignStatus?.progress_percent || 0}%
              </span>
            </div>

            {/* Progress Bar */}
            <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 transition-all duration-500 ease-out"
                style={{ width: `${campaignStatus?.progress_percent || 5}%` }}
              />
            </div>

            {/* Current Step Message */}
            <div className="text-[11px] text-slate-300 font-mono flex items-center gap-2 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
              <Search className="w-3.5 h-3.5 text-sky-400 animate-pulse flex-shrink-0" />
              <span className="truncate">
                {campaignStatus?.current_step || "Initializing research..."}
              </span>
            </div>

            {/* Plan Highlights */}
            {campaignStatus?.plan && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2 border-t border-slate-800">
                <div className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/50">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Campaign Title</div>
                  <div className="text-xs font-semibold text-slate-200 truncate mt-0.5">
                    {campaignStatus.plan.campaign_title}
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/50">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Theme</div>
                  <div className="text-xs font-semibold text-slate-200 truncate mt-0.5">
                    {campaignStatus.plan.theme}
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/50">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Deliverables</div>
                  <div className="text-xs font-semibold text-indigo-300 mt-0.5">
                    {campaignStatus.plan.deliverables?.length || 0} Assets Planned
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Generated Deliverables Board */}
        {campaignStatus?.deliverables && campaignStatus.deliverables.length > 0 ? (
          <div className="space-y-4 flex-1 flex flex-col">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-indigo-500" />
                  Generated Deliverables ({campaignStatus.deliverables.length})
                </h2>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Select items to publish instantly or schedule with custom spacing.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={selectAllDeliverables}
                  className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/40 transition cursor-pointer"
                >
                  Select All
                </button>
                <button
                  onClick={deselectAllDeliverables}
                  className="text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/40 transition cursor-pointer"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* Deliverables Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              {campaignStatus.deliverables.map((item: any, idx: number) => {
                const isSelected = selectedDeliverableIds.includes(item.content_id);
                const isThread = item.type === "thread";
                const isPoll = item.type === "poll";
                const isVisual = item.type === "visual";

                return (
                  <div
                    key={idx}
                    onClick={() => toggleSelectDeliverable(item.content_id)}
                    className={`p-4 rounded-xl border transition cursor-pointer relative flex flex-col justify-between ${
                      isSelected
                        ? "border-indigo-500 bg-indigo-50/40 dark:bg-indigo-950/20 shadow-md shadow-indigo-500/5"
                        : "border-slate-200 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/60 hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    <div>
                      {/* Card Header */}
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div
                            className={`w-4 h-4 rounded flex items-center justify-center transition ${
                              isSelected ? "text-indigo-600 dark:text-indigo-400" : "text-slate-400"
                            }`}
                          >
                            {isSelected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                          </div>
                          <span
                            className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                              isThread
                                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
                                : isPoll
                                ? "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/30"
                                : isVisual
                                ? "bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/30"
                                : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                            }`}
                          >
                            {item.type}
                          </span>
                        </div>

                        <span className="text-[11px] text-slate-400 font-mono">
                          #{idx + 1}
                        </span>
                      </div>

                      {/* Topic Title */}
                      <h3 className="text-xs font-bold text-slate-900 dark:text-slate-200 mb-2 line-clamp-1">
                        {item.topic}
                      </h3>

                      {/* Content Preview Body */}
                      {isThread && item.thread_tweets ? (
                        <div className="space-y-2 pl-2.5 border-l-2 border-amber-500/40 my-2">
                          {item.thread_tweets.map((tw: string, tIdx: number) => (
                            <div key={tIdx} className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-sans">
                              {tw}
                            </div>
                          ))}
                        </div>
                      ) : isPoll ? (
                        <div className="space-y-2 my-2 p-2.5 rounded-lg bg-slate-100/70 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800">
                          <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">{item.question || item.text}</div>
                          <div className="space-y-1 pt-1">
                            {(item.options || ["Option 1", "Option 2"]).map((opt: string, optIdx: number) => (
                              <div
                                key={optIdx}
                                className="p-1.5 rounded-md bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/60 text-xs text-slate-700 dark:text-slate-300 flex items-center justify-between"
                              >
                                <span>{opt}</span>
                                <span className="text-[10px] text-slate-400 font-mono">Option {optIdx + 1}</span>
                              </div>
                            ))}
                          </div>
                          <div className="text-[10px] text-slate-500 pt-0.5">
                            📊 7-Day Interactive Community Poll
                          </div>
                        </div>
                      ) : (
                        <div className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap font-sans my-2">
                          {item.text}
                        </div>
                      )}

                      {/* Media Preview Tag */}
                      {item.media_paths && item.media_paths.length > 0 && (
                        <div className="flex items-center gap-1.5 mt-2.5 pt-2 border-t border-slate-200 dark:border-slate-800/60 text-[11px] text-indigo-600 dark:text-indigo-400 font-medium">
                          <ImageIcon className="w-3.5 h-3.5" />
                          <span>{item.media_paths.length} Scraped Viral Media Asset(s) Attached</span>
                        </div>
                      )}

                      {/* 1st-Reply Link Badge */}
                      {item.extracted_link && (
                        <div className="flex items-center gap-1.5 mt-2 text-[11px] text-sky-600 dark:text-sky-400 font-mono">
                          <ExternalLink className="w-3 h-3" />
                          <span className="truncate">1st-Reply: {item.extracted_link}</span>
                        </div>
                      )}
                    </div>

                    {/* Per-Card Quick Publish / Schedule Actions */}
                    <div className="flex items-center justify-between gap-2 mt-3 pt-2.5 border-t border-slate-200 dark:border-slate-800/80">
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePublishSingleDeliverable(item.content_id, "instant");
                          }}
                          disabled={publishingItemIds.includes(item.content_id)}
                          className="px-2 py-1 rounded-md bg-sky-500/10 hover:bg-sky-500/20 text-sky-600 dark:text-sky-400 border border-sky-500/30 text-[10px] font-bold flex items-center gap-1 transition disabled:opacity-50"
                        >
                          <Send className="w-3 h-3" />
                          {publishingItemIds.includes(item.content_id) ? "Queuing..." : "Publish Now"}
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePublishSingleDeliverable(item.content_id, "schedule");
                          }}
                          disabled={publishingItemIds.includes(item.content_id)}
                          className="px-2 py-1 rounded-md bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30 text-[10px] font-bold flex items-center gap-1 transition disabled:opacity-50"
                        >
                          <Calendar className="w-3 h-3" />
                          Schedule
                        </button>
                      </div>

                      {publishedStatus[item.content_id] ? (
                        <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/30">
                          <CheckCircle2 className="w-3 h-3" />
                          {publishedStatus[item.content_id]}
                        </span>
                      ) : item.status === "approved" || item.status === "queued" ? (
                        <span className="text-[10px] font-bold text-sky-600 dark:text-sky-400 flex items-center gap-1 bg-sky-500/10 px-2 py-0.5 rounded-full border border-sky-500/30">
                          <CheckCircle2 className="w-3 h-3" />
                          Queued
                        </span>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Sticky Campaign Publish Bar */}
            <div className="sticky bottom-0 z-20 mt-4 bg-white/95 dark:bg-slate-900/95 backdrop-blur border border-indigo-500/40 p-3 rounded-xl shadow-lg flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                  {selectedDeliverableIds.length} of {campaignStatus.deliverables.length} Selected
                </span>
                <div className="h-4 w-px bg-slate-300 dark:bg-slate-700 hidden sm:block" />
                <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                  <span>Spacing:</span>
                  <select
                    value={scheduleInterval}
                    onChange={(e) => setScheduleInterval(Number(e.target.value))}
                    className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value={30}>30 mins</option>
                    <option value={60}>60 mins (Recommended)</option>
                    <option value={120}>2 hours</option>
                    <option value={240}>4 hours</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                <button
                  onClick={() => handlePublishDeliverables("instant")}
                  disabled={isPublishing || selectedDeliverableIds.length === 0}
                  className="flex-1 sm:flex-initial px-3.5 py-1.5 rounded-lg text-xs font-bold bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 flex items-center justify-center gap-1.5 transition disabled:opacity-50 cursor-pointer"
                >
                  <Send className="w-3.5 h-3.5 text-sky-500" />
                  Publish Selected Now
                </button>

                <button
                  onClick={() => handlePublishDeliverables("schedule")}
                  disabled={isPublishing || selectedDeliverableIds.length === 0}
                  className="flex-1 sm:flex-initial px-4 py-1.5 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-500/20 flex items-center justify-center gap-1.5 transition disabled:opacity-50 cursor-pointer"
                >
                  <Calendar className="w-3.5 h-3.5" />
                  Auto-Schedule ({scheduleInterval}m)
                </button>
              </div>
            </div>
          </div>
        ) : !isGenerating ? (
          /* Empty State Placeholder */
          <div className="flex-1 flex flex-col items-center justify-center text-center p-6 my-auto">
            <div className="w-14 h-14 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-100 dark:border-indigo-900/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400 mb-3 shadow-sm">
              <Layers className="w-7 h-7" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-1">
              No Campaign Generated Yet
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mb-6 leading-relaxed">
              Enter your campaign directive or select an inspiration template on the left panel, then click &apos;Research &amp; Generate Campaign&apos;.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-md w-full text-left">
              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 flex items-start gap-2">
                <Search className="w-3.5 h-3.5 text-sky-500 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">Live X Intelligence</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400">Scrapes real-time trending context & media</div>
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 flex items-start gap-2">
                <Sparkles className="w-3.5 h-3.5 text-indigo-500 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">Multi-Asset Generation</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400">Creates threads, polls, and media posts</div>
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 flex items-start gap-2">
                <Calendar className="w-3.5 h-3.5 text-purple-500 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">Smart Scheduling</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400">Auto-space deliverables across optimal slots</div>
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 flex items-start gap-2">
                <Send className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">One-Click Dispatch</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400">Publish immediately or queue for approval</div>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
