import { useState, useEffect, useRef } from "react";
import { api, Profile } from "@/lib/api";
import { CampaignStatus } from "../types";

export function useCampaignState(selectedProfile: Profile | null) {
  const [prompt, setPrompt] = useState("");
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

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

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

  return {
    prompt,
    setPrompt,
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
    handleStartCampaign,
    handlePublishSingleDeliverable,
    handlePublishDeliverables,
    toggleSelectDeliverable,
    selectAllDeliverables,
    deselectAllDeliverables,
  };
}
