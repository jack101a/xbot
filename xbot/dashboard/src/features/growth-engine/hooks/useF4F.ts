import { useState, useEffect } from "react";
import { api } from "@/lib/api";
export function useF4F(profileId: string) {
  // Follow-for-Follow & 1,000 Blue Tick Growth State
  const [f4fNiche, setF4fNiche] = useState<string>("all");
  const [f4fBlueTickOnly, setF4fBlueTickOnly] = useState<boolean>(true);
  const [f4fCandidates, setF4fCandidates] = useState<any[]>([]);
  const [f4fGrowthPosts, setF4fGrowthPosts] = useState<any[]>([]);
  const [f4fStats, setF4fStats] = useState<any>(null);
  const [loadingF4F, setLoadingF4F] = useState(false);
  const [scanningF4F, setScanningF4F] = useState(false);
  const [batchFollowingF4F, setBatchFollowingF4F] = useState(false);
  const [harvestingPostId, setHarvestingPostId] = useState<string | null>(null);
  const [followingHandle, setFollowingHandle] = useState<string | null>(null);
  const [f4fMsg, setF4fMsg] = useState<string | null>(null);

  useEffect(() => {
    loadF4FData();
  }, [profileId, f4fNiche, f4fBlueTickOnly]);

  const loadF4FData = async () => {
    setLoadingF4F(true);
    try {
      const [candidates, stats, posts] = await Promise.all([
        api.getF4FCandidates(profileId, f4fNiche, f4fBlueTickOnly),
        api.getF4FStats(profileId),
        api.getActiveGrowthPosts(profileId, f4fNiche),
      ]);
      setF4fCandidates(candidates || []);
      setF4fStats(stats || null);
      setF4fGrowthPosts(posts || []);
    } catch (e) {
      console.error("Could not load F4F data:", e);
    } finally {
      setLoadingF4F(false);
    }
  };

  const handleScanF4F = async () => {
    setScanningF4F(true);
    setF4fMsg(null);
    try {
      const res = await api.scanF4F(profileId, f4fNiche);
      setF4fMsg(res.message || "Harvested new Blue Tick candidates from active community threads!");
      await loadF4FData();
    } catch (err: any) {
      setF4fMsg("Error: " + err.message);
    } finally {
      setScanningF4F(false);
    }
  };

  const handleBatchFollowF4F = async () => {
    setBatchFollowingF4F(true);
    setF4fMsg(null);
    try {
      const res = await api.batchFollowF4F(profileId, 3);
      setF4fMsg(res.message || "Successfully followed top Blue Tick candidates on X!");
      await loadF4FData();
    } catch (err: any) {
      setF4fMsg("Error during batch follow: " + err.message);
    } finally {
      setBatchFollowingF4F(false);
    }
  };

  const handleHarvestGrowthPost = async (postId: string, tweetUrl: string) => {
    setHarvestingPostId(postId);
    setF4fMsg(null);
    try {
      const res = await api.scanF4F(profileId, f4fNiche);
      setF4fMsg(`Harvested active Blue Tick engagers from growth post! (${res.count} candidates queued)`);
      await loadF4FData();
    } catch (err: any) {
      setF4fMsg("Error harvesting post: " + err.message);
    } finally {
      setHarvestingPostId(null);
    }
  };

  const handleFollowCandidate = async (targetHandle: string, isBlueTick: boolean, niche: string) => {
    setFollowingHandle(targetHandle);
    setF4fMsg(null);
    try {
      const res = await api.followF4FCandidate(profileId, targetHandle, isBlueTick, niche);
      setF4fMsg(res.message || `Followed @${targetHandle} on X!`);
      setF4fCandidates((prev) =>
        prev.map((c) => (c.handle === targetHandle ? { ...c, status: "followed" } : c))
      );
      const newStats = await api.getF4FStats(profileId);
      setF4fStats(newStats);
    } catch (err: any) {
      setF4fMsg("Error: " + err.message);
    } finally {
      setFollowingHandle(null);
    }
  };
  

  return {
    f4fNiche, setF4fNiche,
    f4fBlueTickOnly, setF4fBlueTickOnly,
    f4fCandidates, setF4fCandidates,
    f4fGrowthPosts, setF4fGrowthPosts,
    f4fStats, setF4fStats,
    loadingF4F, setLoadingF4F,
    scanningF4F, setScanningF4F,
    batchFollowingF4F, setBatchFollowingF4F,
    harvestingPostId, setHarvestingPostId,
    followingHandle, setFollowingHandle,
    f4fMsg, setF4fMsg,
    handleScanF4F,
    handleBatchFollowF4F,
    handleHarvestGrowthPost,
    handleFollowCandidate
  };
}
