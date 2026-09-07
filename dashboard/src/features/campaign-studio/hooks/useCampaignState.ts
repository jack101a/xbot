import { useState, useEffect, useRef, useCallback } from "react";
import { api, Profile } from "@/lib/api";
import { CampaignStatus, TrendRadarItem, ActiveCampaignSummary } from "../types";

export function useCampaignState(selectedProfile: Profile | null) {
  const [prompt, setPrompt] = useState("");
  const [durationHours, setDurationHours] = useState<number>(0); // 0 = sprint, 12, 24, 48, 72, 168 = continuous
  const [intervalMinutes, setIntervalMinutes] = useState<number>(60);
  const [sourceType, setSourceType] = useState<"on_demand" | "trend_radar">("on_demand");
  const [mediaPreference, setMediaPreference] = useState<"x_official" | "ai_generated">("x_official");

  const [isGenerating, setIsGenerating] = useState(false);
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [campaignStatus, setCampaignStatus] = useState<CampaignStatus | null>(null);
  const [selectedDeliverableIds, setSelectedDeliverableIds] = useState<string[]>([]);
  const [scheduleInterval, setScheduleInterval] = useState<number>(60);
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishingItemIds, setPublishingItemIds] = useState<string[]>([]);
  const [publishedStatus, setPublishedStatus] = useState<Record<string, string>>({});
  const [publishSuccessMessage, setPublishSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Live Trend Radar & Active Continuous Campaigns state
  const [liveTrends, setLiveTrends] = useState<TrendRadarItem[]>([]);
  const [loadingTrends, setLoadingTrends] = useState(false);
  const [activeCampaigns, setActiveCampaigns] = useState<ActiveCampaignSummary[]>([]);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchLiveTrends = useCallback(async () => {
    setLoadingTrends(true);
    try {
      const res = await api.getLiveTrends(selectedProfile?.id, 6);
      if (res?.trends) {
        setLiveTrends(res.trends);
      }
    } catch (err) {
      console.error("Failed to load live trends for Campaign Studio:", err);
    } finally {
      setLoadingTrends(false);
    }
  }, [selectedProfile]);

  const fetchActiveCampaigns = useCallback(async () => {
    try {
      const res = await api.getActiveCampaigns();
      if (Array.isArray(res)) {
        setActiveCampaigns(res);
      }
    } catch (err) {
      console.error("Failed to load active campaigns:", err);
    }
  }, []);

  useEffect(() => {
    fetchActiveCampaigns();
    const timer = setInterval(fetchActiveCampaigns, 15000);
    return () => clearInterval(timer);
  }, [fetchActiveCampaigns]);

  const handleSelectTrend = (trend: TrendRadarItem) => {
    setPrompt(trend.title);
    setSourceType("trend_radar");
    setPublishSuccessMessage(`Selected trend: "${trend.title}" (${trend.alignment_score}% match). Ready to build campaign.`);
  };

  const handleStopActiveCampaign = async (id: string) => {
    try {
      await api.stopCampaign(id);
      setPublishSuccessMessage("Campaign stopped.");
      fetchActiveCampaigns();
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to stop campaign.");
    }
  };

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
          const allIds = (res.deliverables || []).map((d: any) => d.content_id).filter(Boolean);
          setSelectedDeliverableIds(allIds);
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          fetchActiveCampaigns();
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
  }, [campaignId, isGenerating, fetchActiveCampaigns]);

  const handleStartCampaign = async () => {
    if (!selectedProfile) {
      setErrorMessage("Please select an active profile first.");
      return;
    }
    if (!prompt.trim() || prompt.length < 3) {
      setErrorMessage("Please enter a descriptive prompt or pick a trend from the radar.");
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
        duration_hours: durationHours,
        interval_minutes: intervalMinutes,
        source_type: sourceType,
        media_preference: mediaPreference,
      });
      setCampaignId(res.campaign_id);
      fetchActiveCampaigns();
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

  return {
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
    campaignStatus,
    selectedDeliverableIds,
    scheduleInterval,
    setScheduleInterval,
    isPublishing,
    publishingItemIds,
    publishedStatus,
    publishSuccessMessage,
    errorMessage,
    liveTrends,
    loadingTrends,
    fetchLiveTrends,
    activeCampaigns,
    fetchActiveCampaigns,
    handleSelectTrend,
    handleStopActiveCampaign,
    handleStartCampaign,
    handlePublishSingleDeliverable,
    handlePublishDeliverables,
    toggleSelectDeliverable,
    selectAllDeliverables,
    deselectAllDeliverables,
  };
}
