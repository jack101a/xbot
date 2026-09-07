import { useState, useEffect } from "react";
import { api, Profile } from "@/lib/api";

export function useOverviewState(profile: Profile, onRefresh: () => void) {
  const [triggering, setTriggering] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [actionMsg, setActionMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [drafts, setDrafts] = useState<any[]>([]);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [deepAnalytics, setDeepAnalytics] = useState<any | null>(null);
  const [syncingAnalytics, setSyncingAnalytics] = useState(false);

  useEffect(() => {
    loadDrafts();
    loadDeepAnalytics();
  }, [profile.id]);

  const loadDrafts = async () => {
    try {
      const res = await api.getDrafts(profile.id);
      setDrafts(res || []);
    } catch (e) {
      console.error("Could not load drafts:", e);
    }
  };

  const loadDeepAnalytics = async () => {
    try {
      const res = await api.getDeepAnalytics(profile.id);
      setDeepAnalytics(res);
    } catch (e) {
      console.error("Could not load deep analytics:", e);
    }
  };

  const handleSyncLiveAnalytics = async () => {
    setSyncingAnalytics(true);
    setActionMsg(null);
    try {
      const res = await api.syncLiveAnalytics(profile.id);
      setActionMsg({ type: "success", text: res.message || "Live metrics synced successfully!" });
      loadDeepAnalytics();
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to sync live analytics." });
    } finally {
      setSyncingAnalytics(false);
    }
  };

  const handleApproveDraft = async (draftId: string) => {
    setApprovingId(draftId);
    try {
      await api.approveDraft(profile.id, draftId);
      setActionMsg({ type: "success", text: "Draft approved and published live to X!" });
      loadDrafts();
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to publish draft." });
    } finally {
      setApprovingId(null);
    }
  };

  const handleDismissDraft = async (draftId: string) => {
    try {
      await api.dismissDraft(profile.id, draftId);
      setActionMsg({ type: "success", text: "Draft dismissed." });
      loadDrafts();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to dismiss draft." });
    }
  };

  const handleApproveAllDrafts = async () => {
    try {
      const res = await api.approveAllDrafts(profile.id);
      setActionMsg({ type: "success", text: res.message || "All drafts approved for autonomous publishing!" });
      loadDrafts();
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to approve drafts." });
    }
  };

  const handleDismissAllDrafts = async () => {
    if (!confirm(`Are you sure you want to discard all ${drafts.length} pending draft posts?`)) return;
    try {
      const res = await api.dismissAllDrafts(profile.id);
      setActionMsg({ type: "success", text: res.message || "All pending drafts discarded." });
      loadDrafts();
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to discard all drafts." });
    }
  };

  const handleRunSession = async () => {
    setTriggering(true);
    setActionMsg(null);
    try {
      await api.triggerProfileSession(profile.id);
      setActionMsg({ type: "success", text: "Autonomous session queued! Check Live Activity tab to watch in real-time." });
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to trigger session." });
    } finally {
      setTriggering(false);
    }
  };

  const handleSyncFromX = async () => {
    setSyncing(true);
    setActionMsg(null);
    try {
      await api.syncProfileFromX(profile.id);
      setActionMsg({ type: "success", text: "Profile stats and recent tweets synchronized from X!" });
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to sync profile from X." });
    } finally {
      setSyncing(false);
    }
  };

  const handleTogglePause = async () => {
    setActionMsg(null);
    try {
      if (profile.status === "active") {
        await api.pauseProfile(profile.id);
        setActionMsg({ type: "success", text: "Profile automation paused." });
      } else {
        await api.resumeProfile(profile.id);
        setActionMsg({ type: "success", text: "Profile automation resumed." });
      }
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to update status." });
    }
  };

  return {
    triggering,
    syncing,
    actionMsg,
    setActionMsg,
    drafts,
    approvingId,
    deepAnalytics,
    syncingAnalytics,
    handleSyncLiveAnalytics,
    handleApproveDraft,
    handleDismissDraft,
    handleApproveAllDrafts,
    handleDismissAllDrafts,
    handleRunSession,
    handleSyncFromX,
    handleTogglePause
  };
}
