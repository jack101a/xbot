import { useState } from "react";
import { api } from "@/lib/api";

export function useTrends(profileId: string) {
  // Trend Radar State
  const [trendsList, setTrendsList] = useState<any[]>([]);
  const [trendDrafts, setTrendDrafts] = useState<any[]>([]);
  const [loadingTrends, setLoadingTrends] = useState(false);
  const [publishingTrendTake, setPublishingTrendTake] = useState<number | null>(null);
  const [trendMsg, setTrendMsg] = useState<string | null>(null);

  // 5. Scan Trend Radar via Real AI
  const handleScanTrends = async () => {
    setLoadingTrends(true);
    setTrendMsg(null);
    try {
      const res = await api.scanTrendRadar({
        profile_id: profileId,
        limit: 5,
      });
      setTrendsList(res.trends || []);
      setTrendDrafts(res.draft_posts || []);
    } catch (err: any) {
      alert("Failed to scan trends: " + err.message);
    } finally {
      setLoadingTrends(false);
    }
  };

  // 5b. Publish Trend Take to Live X
  const handlePublishTrendTake = async (idx: number, postText: string) => {
    setPublishingTrendTake(idx);
    setTrendMsg(null);
    try {
      const res = await api.publishLivePost(profileId, postText);
      setTrendMsg(res.message || "Trend take published to X timeline!");
    } catch (err: any) {
      setTrendMsg("Error: " + err.message);
    } finally {
      setPublishingTrendTake(null);
    }
  };


  return {
    trendsList, setTrendsList,
    trendDrafts, setTrendDrafts,
    loadingTrends, setLoadingTrends,
    publishingTrendTake, setPublishingTrendTake,
    trendMsg, setTrendMsg,
    handleScanTrends,
    handlePublishTrendTake
  };
}
