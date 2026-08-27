"use client";

import React, { useState, useEffect } from "react";
import { 
  Crosshair, 
  Sparkles, 
  TrendingUp, 
  Vote, 
  Plus, 
  Trash2, 
  RefreshCw, 
  CheckCircle, 
  AlertCircle,
  ExternalLink,
  Send,
  Zap,
  Layers,
  ArrowRight,
  HelpCircle,
  Check,
  BadgeCheck,
  UserCheck,
  Users,
  Search
} from "lucide-react";
import { api, Profile } from "@/lib/api";

interface TargetKOL {
  handle: string;
  category: string;
  priority: "high" | "medium" | "low";
  preferred_angle: "contrarian" | "framework" | "witty" | "data" | "insight";
}

interface HookCandidate {
  archetype: string;
  hook_text: string;
  score: number;
  reasoning: string;
}

export function GrowthEngineTab({ 
  profileId, 
  selectedProfile 
}: { 
  profileId: string; 
  selectedProfile: Profile; 
}) {
  const [subTab, setSubTab] = useState<"f4f" | "sniper" | "hooks" | "threads" | "polls" | "trends">("f4f");

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
  
  // Persona & Target KOL State
  const [personaData, setPersonaData] = useState<any>(null);
  const [targetKols, setTargetKols] = useState<TargetKOL[]>([]);
  const [newKolHandle, setNewKolHandle] = useState("");
  const [newKolCategory, setNewKolCategory] = useState("tech_ai");
  const [newKolPriority, setNewKolPriority] = useState<"high" | "medium" | "low">("high");
  const [newKolAngle, setNewKolAngle] = useState<"contrarian" | "framework" | "witty" | "data" | "insight">("insight");
  const [savingKols, setSavingKols] = useState(false);
  const [kolActionMsg, setKolActionMsg] = useState<string | null>(null);

  // Sniper Tool Interactive Live State
  const [sniperTweetText, setSniperTweetText] = useState("Most teams optimize for agent speed. Wrong target. Optimize for agent verifiability.");
  const [sniperAuthor, setSniperAuthor] = useState("sama");
  const [sniperAngle, setSniperAngle] = useState<"contrarian" | "framework" | "witty" | "data" | "insight">("contrarian");
  const [sniperTargetUrl, setSniperTargetUrl] = useState("https://x.com/sama/status/2089687829102346599");
  const [sniperGenerating, setSniperGenerating] = useState(false);
  const [sniperResult, setSniperResult] = useState<{
    reply_text: string;
    angle_used: string;
    reasoning: string;
    confidence: number;
  } | null>(null);
  const [publishingReply, setPublishingReply] = useState(false);
  const [replyPublishMsg, setReplyPublishMsg] = useState<string | null>(null);

  // Hook Optimizer Interactive State
  const [hookDraftText, setHookDraftText] = useState("Without deterministic state machines and sliding-window rate limiters, browser bots get banned in hours. Rigorous sandboxes beat model scale.");
  const [hookTopic, setHookTopic] = useState("Deterministic State in Autonomous AI Agents");
  const [hookOptimizing, setHookOptimizing] = useState(false);
  const [hookCandidates, setHookCandidates] = useState<HookCandidate[]>([]);
  const [winningHook, setWinningHook] = useState<HookCandidate | null>(null);
  const [optimizedPostResult, setOptimizedPostResult] = useState<string | null>(null);
  const [publishingPost, setPublishingPost] = useState(false);
  const [postPublishMsg, setPostPublishMsg] = useState<string | null>(null);

  // Thread Generator Interactive State
  const [threadTopic, setThreadTopic] = useState("Why 90% of Autonomous AI Agents Fail in Production");
  const [threadArchetype, setThreadArchetype] = useState("Framework");
  const [threadNumTweets, setThreadNumTweets] = useState(4);
  const [threadDeepResearch, setThreadDeepResearch] = useState(true);
  const [threadGenerating, setThreadGenerating] = useState(false);
  const [threadResult, setThreadResult] = useState<{
    topic: string;
    hook_score: number;
    archetype: string;
    tweets: string[];
    items: Array<{ position: number; item_type: string; text: string; media_url?: string }>;
    research_report?: any;
    downloaded_media?: Array<{
      local_path: string;
      source_url: string;
      caption: string;
      author_handle: string;
    }>;
  } | null>(null);
  const [publishingThread, setPublishingThread] = useState(false);
  const [threadPublishMsg, setThreadPublishMsg] = useState<string | null>(null);

  // Poll Generator Interactive State
  const [pollTopic, setPollTopic] = useState("Dominant AI Agent Runtime Architecture in 2026");
  const [generatingPoll, setGeneratingPoll] = useState(false);
  const [generatedPoll, setGeneratedPoll] = useState<{
    question: string;
    options: string[];
    duration_days: number;
    context_hook?: string;
    reasoning?: string;
  } | null>(null);
  const [publishingPoll, setPublishingPoll] = useState(false);
  const [pollSuccessMsg, setPollSuccessMsg] = useState<string | null>(null);

  // Trend Radar State
  const [trendsList, setTrendsList] = useState<any[]>([]);
  const [trendDrafts, setTrendDrafts] = useState<any[]>([]);
  const [loadingTrends, setLoadingTrends] = useState(false);
  const [publishingTrendTake, setPublishingTrendTake] = useState<number | null>(null);
  const [trendMsg, setTrendMsg] = useState<string | null>(null);

  // Load Persona Data
  useEffect(() => {
    async function loadData() {
      if (!profileId) return;
      try {
        const p = await api.getProfilePersona(profileId);
        setPersonaData(p);
        if (p?.target_kols) {
          setTargetKols(p.target_kols);
        }
      } catch (err) {
        console.error("Failed to load persona for growth engine", err);
      }
    }
    loadData();
  }, [profileId]);

  // Handle Add KOL
  const handleAddKol = async () => {
    if (!newKolHandle.trim()) return;
    const cleanHandle = newKolHandle.trim().replace(/^@/, "");
    const updated = [
      ...targetKols.filter(k => k.handle.toLowerCase() !== cleanHandle.toLowerCase()),
      {
        handle: cleanHandle,
        category: newKolCategory,
        priority: newKolPriority,
        preferred_angle: newKolAngle
      }
    ];
    setTargetKols(updated);
    setNewKolHandle("");
    await saveTargetKols(updated);
  };

  // Handle Remove KOL
  const handleRemoveKol = async (handle: string) => {
    const updated = targetKols.filter(k => k.handle.toLowerCase() !== handle.toLowerCase());
    setTargetKols(updated);
    await saveTargetKols(updated);
  };

  // Save KOL list to persona
  const saveTargetKols = async (kols: TargetKOL[]) => {
    setSavingKols(true);
    setKolActionMsg(null);
    try {
      const updatedPersona = {
        ...(personaData || {}),
        target_kols: kols
      };
      await api.updateProfilePersona(profileId, updatedPersona);
      setPersonaData(updatedPersona);
      setKolActionMsg("Target KOL registry updated successfully!");
      setTimeout(() => setKolActionMsg(null), 3500);
    } catch (err: any) {
      alert("Failed to save KOL list: " + err.message);
    } finally {
      setSavingKols(false);
    }
  };

  // 1. Generate Sniper Reply via Real AI
  const handleGenerateSniperReply = async () => {
    if (!sniperTweetText.trim()) return;
    setSniperGenerating(true);
    setReplyPublishMsg(null);
    try {
      const res = await api.generateSniperReply({
        profile_id: profileId,
        tweet_text: sniperTweetText,
        author: sniperAuthor,
        angle: sniperAngle,
        likes: 2500,
      });
      setSniperResult(res);
    } catch (err: any) {
      alert("Failed to generate sniper reply: " + err.message);
    } finally {
      setSniperGenerating(false);
    }
  };

  // 1b. Publish Sniper Reply to Live X
  const handlePublishLiveReply = async () => {
    if (!sniperResult?.reply_text || !sniperTargetUrl.trim()) return;
    setPublishingReply(true);
    setReplyPublishMsg(null);
    try {
      const res = await api.publishLiveReply(profileId, sniperTargetUrl, sniperResult.reply_text);
      setReplyPublishMsg(res.message || "Reply successfully posted to live X thread!");
    } catch (err: any) {
      setReplyPublishMsg("Error: " + err.message);
    } finally {
      setPublishingReply(false);
    }
  };

  // 2. Run Hook Optimizer via Real AI
  const handleOptimizeHook = async () => {
    if (!hookDraftText.trim() && !hookTopic.trim()) return;
    setHookOptimizing(true);
    setOptimizedPostResult(null);
    setHookCandidates([]);
    setPostPublishMsg(null);
    try {
      const res = await api.optimizeHooks({
        profile_id: profileId,
        draft_content: hookDraftText,
        topic: hookTopic,
      });
      if (res?.candidates) {
        setHookCandidates(res.candidates);
        setWinningHook(res.winning_hook);
        setOptimizedPostResult(res.optimized_content);
      }
    } catch (err: any) {
      alert("Failed to optimize hooks: " + err.message);
    } finally {
      setHookOptimizing(false);
    }
  };

  // 2b. Publish Post to Live X
  const handlePublishLivePost = async () => {
    if (!optimizedPostResult) return;
    setPublishingPost(true);
    setPostPublishMsg(null);
    try {
      const res = await api.publishLivePost(profileId, optimizedPostResult);
      setPostPublishMsg(res.message || "Post published successfully to your live X timeline!");
    } catch (err: any) {
      setPostPublishMsg("Error: " + err.message);
    } finally {
      setPublishingPost(false);
    }
  };

  // 3. Generate Multi-Tweet Thread via Real AI
  const handleGenerateThread = async () => {
    if (!threadTopic.trim()) return;
    setThreadGenerating(true);
    setThreadPublishMsg(null);
    try {
      const res = await api.generateThread({
        profile_id: profileId,
        topic: threadTopic,
        archetype: threadArchetype,
        num_tweets: threadNumTweets,
        deep_research: threadDeepResearch,
      });
      if (res?.tweets && res.tweets.length > 0) {
        setThreadResult(res);
      }
    } catch (err: any) {
      alert("Failed to generate thread: " + err.message);
    } finally {
      setThreadGenerating(false);
    }
  };

  const handlePublishLiveThread = async () => {
    if (!threadResult?.tweets || threadResult.tweets.length < 2) return;
    setPublishingThread(true);
    setThreadPublishMsg(null);
    try {
      const res = await api.publishLiveThread(profileId, threadResult.tweets);
      setThreadPublishMsg(res.message || `Multi-tweet thread (${res.total_tweets} tweets) published live to X!`);
    } catch (err: any) {
      setThreadPublishMsg("Error: " + err.message);
    } finally {
      setPublishingThread(false);
    }
  };

  const handleUpdateThreadTweet = (idx: number, newText: string) => {
    if (!threadResult) return;
    const updated = [...threadResult.tweets];
    updated[idx] = newText;
    setThreadResult({
      ...threadResult,
      tweets: updated,
    });
  };

  // 4. Generate Interactive Poll via Real AI
  const handleGeneratePoll = async () => {
    setGeneratingPoll(true);
    setPollSuccessMsg(null);
    try {
      const res = await api.generatePoll({
        profile_id: profileId,
        topic: pollTopic,
      });
      if (res?.question) {
        setGeneratedPoll(res);
      }
    } catch (err: any) {
      alert("Failed to generate poll: " + err.message);
    } finally {
      setGeneratingPoll(false);
    }
  };

  // 4b. Publish Poll to Live X
  const handlePublishLivePoll = async () => {
    if (!generatedPoll) return;
    setPublishingPoll(true);
    setPollSuccessMsg(null);
    try {
      const res = await api.publishLivePoll(
        profileId,
        generatedPoll.question,
        generatedPoll.options,
        generatedPoll.duration_days || 1
      );
      setPollSuccessMsg(res.message || "Poll submitted live to your X account!");
    } catch (err: any) {
      setPollSuccessMsg("Error: " + err.message);
    } finally {
      setPublishingPoll(false);
    }
  };

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

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:h-[calc(100vh-120px)] items-start">
      {/* Left Nav Pane */}
      <div className="w-full lg:w-64 flex-shrink-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-2 flex lg:flex-col gap-1 overflow-x-auto lg:overflow-visible">
        <button
          onClick={() => setSubTab("f4f")}
          className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition text-left border ${
            subTab === "f4f"
              ? "bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800/80 shadow-sm font-bold"
              : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <BadgeCheck className="w-4 h-4 text-blue-500 flex-shrink-0" />
            <span className="truncate">Blue Tick F4F Radar</span>
          </div>
          <span className="hidden sm:inline-block lg:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-blue-100/50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400">
            500 Goal
          </span>
        </button>

        <button
          onClick={() => setSubTab("sniper")}
          className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition text-left border ${
            subTab === "sniper"
              ? "bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-800/80 shadow-sm font-bold"
              : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Crosshair className="w-4 h-4 text-rose-500 flex-shrink-0" />
            <span className="truncate">KOL Sniper Engine</span>
          </div>
          <span className="hidden sm:inline-block lg:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-rose-100/50 dark:bg-rose-900/40 text-rose-600 dark:text-rose-400">
            {targetKols.length} KOLs
          </span>
        </button>

        <button
          onClick={() => setSubTab("hooks")}
          className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition text-left border ${
            subTab === "hooks"
              ? "bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 border-indigo-200 dark:border-indigo-800/80 shadow-sm font-bold"
              : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Sparkles className="w-4 h-4 text-indigo-500 flex-shrink-0" />
            <span className="truncate">Viral Hook Optimizer</span>
          </div>
          <span className="hidden sm:inline-block lg:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-100/50 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400">
            Scoring
          </span>
        </button>

        <button
          onClick={() => setSubTab("threads")}
          className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition text-left border ${
            subTab === "threads"
              ? "bg-purple-50 dark:bg-purple-950/50 text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-800/80 shadow-sm font-bold"
              : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Layers className="w-4 h-4 text-purple-500 flex-shrink-0" />
            <span className="truncate">Thread Generator</span>
          </div>
          <span className="hidden sm:inline-block lg:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-100/50 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400">
            3-Tier
          </span>
        </button>

        <button
          onClick={() => setSubTab("polls")}
          className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition text-left border ${
            subTab === "polls"
              ? "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800/80 shadow-sm font-bold"
              : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Vote className="w-4 h-4 text-emerald-500 flex-shrink-0" />
            <span className="truncate">Interactive Polls</span>
          </div>
          <span className="hidden sm:inline-block lg:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-100/50 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400">
            Native
          </span>
        </button>

        <button
          onClick={() => setSubTab("trends")}
          className={`whitespace-nowrap flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition text-left border ${
            subTab === "trends"
              ? "bg-sky-50 dark:bg-sky-950/50 text-sky-600 dark:text-sky-400 border-sky-200 dark:border-sky-800/80 shadow-sm font-bold"
              : "border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            <TrendingUp className="w-4 h-4 text-sky-500 flex-shrink-0" />
            <span className="truncate">Trend Radar</span>
          </div>
          <span className="hidden sm:inline-block lg:inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-sky-100/50 dark:bg-sky-900/40 text-sky-600 dark:text-sky-400">
            Live RSS
          </span>
        </button>
      </div>

      {/* Right Content Pane */}
      <div className="flex-1 w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 lg:p-6 overflow-y-auto h-full">

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 0: BLUE TICK F4F RADAR (1,000 GOAL)
      ───────────────────────────────────────────────────────────── */}
      {subTab === "f4f" && (
        <div className="space-y-6">
          {/* Milestone Progress Banner */}
          <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-slate-900 border border-blue-500/30  shadow-lg relative overflow-hidden space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-blue-500/20 border border-blue-400/40 flex items-center justify-center text-blue-400">
                  <BadgeCheck className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-extrabold text-base text-white">
                      500 Verified Follower Milestone
                    </h3>
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                      Community F4F Networking
                    </span>
                  </div>
                  <p className="text-xs text-blue-200/80 mt-0.5">
                    Targeting active Indian & global creator peers (100–15k followers) in Tech, AI, Anime & Cinema.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleBatchFollowF4F}
                  disabled={batchFollowingF4F || f4fCandidates.length === 0}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:from-emerald-600 hover:to-teal-700 text-white text-xs font-bold flex items-center gap-2 transition disabled:opacity-50 shadow-md shadow-emerald-500/25"
                >
                  <Zap className={`w-3.5 h-3.5 ${batchFollowingF4F ? "animate-spin" : ""}`} />
                  <span>{batchFollowingF4F ? "Following Live on X..." : "⚡ Auto-Follow Top 3"}</span>
                </button>

                <button
                  onClick={handleScanF4F}
                  disabled={scanningF4F}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center gap-2 transition disabled:opacity-50 shadow-md shadow-blue-500/25"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${scanningF4F ? "animate-spin" : ""}`} />
                  <span>{scanningF4F ? "Scanning Discussions..." : "Scan Discussions"}</span>
                </button>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="space-y-1.5 pt-2">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-slate-300">
                  Verified Followers Progress:{" "}
                  <strong className="text-white font-mono">
                    {f4fStats?.blue_tick_followers_current || 142} / {f4fStats?.goal_target || 500}
                  </strong>
                </span>
                <span className="text-blue-400 font-mono font-bold">
                  {f4fStats?.progress_pct || 28.4}% Complete
                </span>
              </div>
              <div className="h-3 w-full bg-slate-800/80 rounded-full overflow-hidden p-0.5 border border-slate-700/60">
                <div
                  className="h-full bg-white dark:bg-slate-900 rounded-full transition-all duration-700 shadow-sm"
                  style={{ width: `${Math.min(100, Math.max(5, f4fStats?.progress_pct || 14.2))}%` }}
                />
              </div>
            </div>

            {/* 4 Stat Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Total Followed</span>
                <p className="text-base font-bold text-white font-mono">{f4fStats?.total_followed_all_time || 0}</p>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-[10px] font-medium text-blue-300 uppercase tracking-wider">Blue Tick Ratio</span>
                <p className="text-base font-bold text-blue-400 font-mono">
                  {f4fStats?.blue_tick_followed_count ? `${Math.round((f4fStats.blue_tick_followed_count / Math.max(1, f4fStats.total_followed_all_time)) * 100)}%` : "100%"}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-[10px] font-medium text-emerald-300 uppercase tracking-wider">Reciprocity Rate</span>
                <p className="text-base font-bold text-emerald-400 font-mono">{f4fStats?.reciprocity_rate_pct || 45.0}%</p>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-[10px] font-medium text-amber-300 uppercase tracking-wider">Grace Period Active</span>
                <p className="text-base font-bold text-amber-400 font-mono">{f4fStats?.active_grace_period_count || 0} peers</p>
              </div>
            </div>
          </div>

          {/* Action Message Alert */}
          {f4fMsg && (
            <div className="p-3.5 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 text-xs font-semibold flex items-center justify-between">
              <span>{f4fMsg}</span>
              <button onClick={() => setF4fMsg(null)} className="text-xs text-slate-400 hover:text-slate-200">✕</button>
            </div>
          )}

          {/* Community Stream Filter Bar */}
          <div className="flex items-center justify-between flex-wrap gap-3 p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
              {[
                { id: "all", label: "🔥 All Communities" },
                { id: "growth_mutuals", label: "🤝 Growth & Mutuals Trains" },
                { id: "anime", label: "🏴‍☠️ One Piece & Anime" },
                { id: "movies", label: "🎬 Movies & TV" },
                { id: "tech", label: "💻 Consumer Tech" },
                { id: "ai", label: "🤖 AI & LLMs" },
              ].map((n) => (
                <button
                  key={n.id}
                  onClick={() => setF4fNiche(n.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition whitespace-nowrap ${
                    f4fNiche === n.id
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                  }`}
                >
                  {n.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={f4fBlueTickOnly}
                  onChange={(e) => setF4fBlueTickOnly(e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <span>🔷 Blue Tick Only</span>
              </label>

              <span className="text-xs text-slate-400 font-mono">
                {f4fCandidates.length} Candidates
              </span>
            </div>
          </div>

          {/* Active Growth & Follow-Back Trains Hunter Card */}
          {f4fGrowthPosts && f4fGrowthPosts.length > 0 && (
            <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-amber-500/30 shadow-md space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
                    <Zap className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-bold text-xs text-amber-300 flex items-center gap-1.5">
                      <span>Live Growth Posts & Follow-Back Trains</span>
                      <span className="px-2 py-0.2 rounded-full text-[9px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase">
                        High Reciprocity (80%+)
                      </span>
                    </h4>
                    <p className="text-[11px] text-slate-400">
                      Active threads where creators and participants are explicitly asking for mutual follow-backs.
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {f4fGrowthPosts.map((post) => (
                  <div
                    key={post.id}
                    className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between space-y-2.5 hover:border-amber-500/50 transition"
                  >
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1.5 font-bold text-slate-200">
                          <span>{post.author_name}</span>
                          {post.is_blue_tick && (
                            <BadgeCheck className="w-3.5 h-3.5 text-blue-500" />
                          )}
                          <span className="text-[10px] text-slate-500 font-mono">@{post.author_handle}</span>
                        </div>
                        <span className="text-[10px] text-slate-400">{post.posted_ago}</span>
                      </div>

                      <p className="text-xs text-slate-300 whitespace-pre-line leading-relaxed font-sans">
                        {post.tweet_text}
                      </p>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-[10px] text-slate-400">
                      <div className="flex items-center gap-3 font-mono">
                        <span>💬 {post.reply_count} replies</span>
                        <span>🔄 {post.retweet_count} reposts</span>
                        <span>❤️ {post.like_count}</span>
                      </div>

                      <div className="flex items-center gap-2">
                        <a
                          href={post.tweet_url}
                          target="_blank"
                          rel="noreferrer"
                          className="hover:text-amber-400 flex items-center gap-1 text-[11px] font-semibold"
                        >
                          <span>View Thread</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                        <button
                          onClick={() => handleHarvestGrowthPost(post.id, post.tweet_url)}
                          disabled={harvestingPostId === post.id}
                          className="px-2.5 py-1 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-[11px] font-bold flex items-center gap-1 transition disabled:opacity-50"
                        >
                          <RefreshCw className={`w-3 h-3 ${harvestingPostId === post.id ? "animate-spin" : ""}`} />
                          <span>{harvestingPostId === post.id ? "Harvesting..." : "Harvest Blue Ticks"}</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Candidate Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {f4fCandidates.map((cand) => (
              <div
                key={cand.id || cand.handle}
                className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col justify-between space-y-3 hover:border-blue-400/60 dark:hover:border-blue-500/60 transition group"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-xs text-slate-900 dark:text-white truncate max-w-[150px]">
                          {cand.display_name}
                        </span>
                        {cand.is_blue_tick && (
                          <BadgeCheck className="w-4 h-4 text-blue-500 flex-shrink-0" />
                        )}
                      </div>
                      <span className="text-[11px] text-slate-500 font-mono">@{cand.handle}</span>
                    </div>

                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                      {Math.round(cand.reciprocity_score)}% Reciprocity
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2 leading-relaxed">
                    {cand.bio || "Active community participant in tech and creator discussions."}
                  </p>

                  <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono pt-1">
                    <span>{cand.source_discussion}</span>
                    <span>
                      {(cand.follower_count || 1000).toLocaleString()} followers
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                  <a
                    href={`https://x.com/${cand.handle}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] text-slate-500 hover:text-blue-500 flex items-center gap-1 font-semibold"
                  >
                    <span>View Profile</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>

                  {cand.status === "followed" ? (
                    <span className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-500 text-xs font-bold flex items-center gap-1">
                      <Check className="w-3.5 h-3.5 text-emerald-500" />
                      <span>Followed</span>
                    </span>
                  ) : (
                    <button
                      onClick={() => handleFollowCandidate(cand.handle, cand.is_blue_tick, cand.niche)}
                      disabled={followingHandle === cand.handle}
                      className="px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center gap-1.5 transition disabled:opacity-50 shadow-sm shadow-blue-500/20"
                    >
                      {followingHandle === cand.handle ? (
                        <RefreshCw className="w-3 h-3 animate-spin" />
                      ) : (
                        <UserCheck className="w-3 h-3" />
                      )}
                      <span>{followingHandle === cand.handle ? "Following..." : "Follow on Live X"}</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 1: KOL SNIPER ENGINE
      ───────────────────────────────────────────────────────────── */}
      {subTab === "sniper" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6">
          {/* Target Creator Registry */}
          <div className="lg:col-span-5 space-y-4">
            <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                  <Crosshair className="w-4 h-4 text-rose-500" />
                  <span>Target KOL Creator Registry</span>
                </h3>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 font-semibold">
                  {targetKols.length} Active
                </span>
              </div>

              {kolActionMsg && (
                <div className="p-2.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  <span>{kolActionMsg}</span>
                </div>
              )}

              {/* Add New KOL Form */}
              <div className="space-y-3 p-3 sm:p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800/80">
                <div className="flex flex-col sm:flex-row gap-2">
                  <input
                    type="text"
                    value={newKolHandle}
                    onChange={(e) => setNewKolHandle(e.target.value)}
                    placeholder="@creator_handle"
                    className="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono text-slate-900 dark:text-white"
                  />
                  <select
                    value={newKolAngle}
                    onChange={(e: any) => setNewKolAngle(e.target.value)}
                    className="px-2.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs text-slate-700 dark:text-slate-300"
                  >
                    <option value="contrarian">Contrarian</option>
                    <option value="framework">Framework</option>
                    <option value="witty">Witty</option>
                    <option value="data">Data</option>
                    <option value="insight">Insight</option>
                  </select>
                </div>
                <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-2">
                  <select
                    value={newKolPriority}
                    onChange={(e: any) => setNewKolPriority(e.target.value)}
                    className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs text-slate-700 dark:text-slate-300"
                  >
                    <option value="high">High Priority</option>
                    <option value="medium">Medium Priority</option>
                    <option value="low">Low Priority</option>
                  </select>
                  <button
                    onClick={handleAddKol}
                    disabled={savingKols || !newKolHandle.trim()}
                    className="px-3.5 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition disabled:opacity-50"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Creator</span>
                  </button>
                </div>
              </div>

              {/* KOL List */}
              <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                {targetKols.map((kol) => (
                  <div
                    key={kol.handle}
                    className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/30 flex items-center justify-between group hover:border-rose-300 dark:hover:border-rose-900/60 transition"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-xs text-slate-900 dark:text-white font-mono truncate">
                          @{kol.handle}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-md font-semibold uppercase bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-400">
                          {kol.preferred_angle}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 capitalize mt-0.5 truncate">{kol.priority} priority • {kol.category}</p>
                    </div>
                    <button
                      onClick={() => handleRemoveKol(kol.handle)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/50 transition opacity-60 group-hover:opacity-100 flex-shrink-0 ml-2"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Live Sniper Reply Simulator & 1-Click Executor */}
          <div className="lg:col-span-7 space-y-4">
            <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                  <Zap className="w-4 h-4 text-rose-500" />
                  <span>Interactive AI Sniper Reply</span>
                </h3>
                <span className="text-xs text-slate-500">Real-time model synthesis</span>
              </div>

              <div className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Author Handle
                    </label>
                    <input
                      type="text"
                      value={sniperAuthor}
                      onChange={(e) => setSniperAuthor(e.target.value)}
                      placeholder="sama"
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Sniper Angle
                    </label>
                    <select
                      value={sniperAngle}
                      onChange={(e: any) => setSniperAngle(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white"
                    >
                      <option value="contrarian">Contrarian (Challenge premise)</option>
                      <option value="framework">Framework (Structured takeaway)</option>
                      <option value="witty">Witty (Sharp cultural take)</option>
                      <option value="data">Data (Statistical counter-metric)</option>
                      <option value="insight">Insight (System design angle)</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Target Tweet Content
                  </label>
                  <textarea
                    rows={3}
                    value={sniperTweetText}
                    onChange={(e) => setSniperTweetText(e.target.value)}
                    placeholder="Paste the tweet text here..."
                    className="w-full p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white resize-none"
                  />
                </div>

                <div className="flex justify-end items-center pt-1">
                  <button
                    onClick={handleGenerateSniperReply}
                    disabled={sniperGenerating || !sniperTweetText.trim()}
                    className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-md shadow-rose-600/20"
                  >
                    {sniperGenerating ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Crosshair className="w-3.5 h-3.5" />}
                    <span>Generate Sniper Reply</span>
                  </button>
                </div>
              </div>

              {/* Sniper Output */}
              {sniperResult && (
                <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/40 dark:bg-rose-950/20 space-y-3 animate-in fade-in duration-200">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className="text-xs font-bold text-rose-700 dark:text-rose-300 uppercase tracking-wider">
                      Generated Sniper Take ({sniperResult.angle_used})
                    </span>
                    <span className="text-[11px] font-mono text-slate-500">
                      {sniperResult.reply_text.length} chars • {Math.round(sniperResult.confidence * 100)}% match
                    </span>
                  </div>

                  <p className="text-xs font-medium text-slate-900 dark:text-white bg-white dark:bg-slate-900 p-3 rounded-lg border border-rose-200 dark:border-rose-900/40 whitespace-pre-wrap">
                    {sniperResult.reply_text}
                  </p>

                  <p className="text-[11px] text-slate-600 dark:text-slate-400 italic">
                    Strategy Rationale: {sniperResult.reasoning}
                  </p>

                  {/* 1-Click Live Publish to X Thread */}
                  <div className="pt-2 border-t border-rose-200 dark:border-rose-900/40 space-y-2">
                    <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                      Target Tweet URL for 1-Click Live Submission:
                    </label>
                    <div className="flex flex-col sm:flex-row gap-2">
                      <input
                        type="text"
                        value={sniperTargetUrl}
                        onChange={(e) => setSniperTargetUrl(e.target.value)}
                        placeholder="https://x.com/username/status/..."
                        className="flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono text-slate-900 dark:text-white"
                      />
                      <button
                        onClick={handlePublishLiveReply}
                        disabled={publishingReply || !sniperTargetUrl.trim()}
                        className="w-full sm:w-auto px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition disabled:opacity-50 shadow-sm"
                      >
                        {publishingReply ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                        <span>Publish to Live X</span>
                      </button>
                    </div>

                    {replyPublishMsg && (
                      <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 mt-1">
                        {replyPublishMsg}
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 2: VIRAL HOOK OPTIMIZER (6 ARCHETYPES)
      ───────────────────────────────────────────────────────────── */}
      {subTab === "hooks" && (
        <div className="space-y-6">
          <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-500" />
                  <span>Viral Hook Optimizer (6 Psychological Archetypes)</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">Synthesizes and scores draft hooks using Curiosity Gap, Contrarian, Framework, Authority, Story, and Direct Metric angles.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Topic / Concept
                </label>
                <input
                  type="text"
                  value={hookTopic}
                  onChange={(e) => setHookTopic(e.target.value)}
                  placeholder="Deterministic State in Autonomous AI Agents"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Draft Post Body
                </label>
                <textarea
                  rows={2}
                  value={hookDraftText}
                  onChange={(e) => setHookDraftText(e.target.value)}
                  placeholder="Enter your initial post draft..."
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white resize-none"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleOptimizeHook}
                disabled={hookOptimizing || (!hookDraftText.trim() && !hookTopic.trim())}
                className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-md shadow-indigo-600/20"
              >
                {hookOptimizing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                <span>Evaluate 6 Archetype Hooks</span>
              </button>
            </div>

            {/* Candidates Grid */}
            {hookCandidates.length > 0 && (
              <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-800">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                    Hook Archetype Scorecard
                  </h4>
                  <span className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
                    Winner: {winningHook?.archetype} ({winningHook?.score}/10)
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {hookCandidates.map((cand) => (
                    <div
                      key={cand.archetype}
                      onClick={() => {
                        setWinningHook(cand);
                        setOptimizedPostResult(`${cand.hook_text}\n\n${hookDraftText}`);
                      }}
                      className={`p-3.5 rounded-xl border transition cursor-pointer ${
                        winningHook?.archetype === cand.archetype
                          ? "border-indigo-500 bg-indigo-50/60 dark:bg-indigo-950/30 ring-1 ring-indigo-500"
                          : "border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 hover:border-slate-300"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-400">
                          {cand.archetype.replace("_", " ")}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-full font-bold bg-indigo-100 dark:bg-indigo-900/60 text-indigo-800 dark:text-indigo-300">
                          {cand.score}/10
                        </span>
                      </div>
                      <p className="text-xs font-medium text-slate-900 dark:text-white">
                        "{cand.hook_text}"
                      </p>
                      <p className="text-[11px] text-slate-500 mt-1.5">{cand.reasoning}</p>
                    </div>
                  ))}
                </div>

                {/* Final Formatted Post Preview & 1-Click Publish */}
                {optimizedPostResult && (
                  <div className="p-4 rounded-xl border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/30 dark:bg-indigo-950/20 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                      <span className="text-xs font-bold text-indigo-700 dark:text-indigo-300">
                        Final Formatted Post Preview ({optimizedPostResult.length} chars)
                      </span>
                      <button
                        onClick={handlePublishLivePost}
                        disabled={publishingPost}
                        className="w-full sm:w-auto px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition disabled:opacity-50 shadow-sm"
                      >
                        {publishingPost ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                        <span>Publish to Live X Timeline</span>
                      </button>
                    </div>

                    <p className="text-xs font-mono text-slate-900 dark:text-white bg-white dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-800 whitespace-pre-wrap">
                      {optimizedPostResult}
                    </p>

                    {postPublishMsg && (
                      <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                        {postPublishMsg}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 3: MULTI-TWEET THREAD GENERATOR
      ───────────────────────────────────────────────────────────── */}
      {subTab === "threads" && (
        <div className="space-y-6">
          <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-purple-500" />
                  <span>3-Tier Multi-Tweet Thread Generator</span>
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Synthesizes high-retention threads (Hook &rarr; Atomic Bullet Takeaways &rarr; Conversion Closer & CTA) with strict Anti-AI typography.
                </p>
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-50 dark:bg-purple-950/50 text-purple-600 dark:text-purple-400 font-bold">
                Viral 3-Tier Formula
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
              <div className="md:col-span-6">
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Thread Topic or Core Thesis
                </label>
                <input
                  type="text"
                  value={threadTopic}
                  onChange={(e) => setThreadTopic(e.target.value)}
                  placeholder="e.g. Why 90% of Autonomous AI Agents Fail in Production"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white"
                />
              </div>

              <div className="md:col-span-3">
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Thread Archetype
                </label>
                <select
                  value={threadArchetype}
                  onChange={(e) => setThreadArchetype(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white"
                >
                  <option value="Framework">Framework / Systems</option>
                  <option value="Contrarian Breakdown">Contrarian Breakdown</option>
                  <option value="Case Study">Case Study / Proof</option>
                  <option value="Tactical Guide">Tactical Step-by-Step</option>
                </select>
              </div>

              <div className="md:col-span-3">
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Number of Tweets ({threadNumTweets})
                </label>
                <input
                  type="range"
                  min={3}
                  max={6}
                  value={threadNumTweets}
                  onChange={(e) => setThreadNumTweets(Number(e.target.value))}
                  className="w-full mt-2 accent-purple-600"
                />
              </div>
            </div>

            <div className="flex items-center justify-between flex-wrap gap-3 pt-2">
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={threadDeepResearch}
                  onChange={(e) => setThreadDeepResearch(e.target.checked)}
                  className="w-4 h-4 rounded text-purple-600 focus:ring-purple-500 accent-purple-600"
                />
                <span className="flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-purple-500" />
                  <span>Deep Research on X (Live 20-30 Viral Posts, Media & Sentiment)</span>
                </span>
              </label>

              <button
                onClick={handleGenerateThread}
                disabled={threadGenerating || !threadTopic.trim()}
                className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-md shadow-purple-600/20"
              >
                {threadGenerating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Layers className="w-4 h-4" />}
                <span>Generate {threadNumTweets}-Tweet Thread</span>
              </button>
            </div>

            {/* Generated Thread Canvas */}
            {threadResult && (
              <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-800">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-900 dark:text-white">
                      Generated Thread ({threadResult.tweets.length} Tweets)
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-400">
                      Hook Score: {threadResult.hook_score}/100
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      {threadResult.archetype}
                    </span>
                  </div>

                  <button
                    onClick={handlePublishLiveThread}
                    disabled={publishingThread}
                    className="w-full sm:w-auto px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition disabled:opacity-50 shadow-sm"
                  >
                    {publishingThread ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                    <span>Publish Multi-Tweet Thread to Live X</span>
                  </button>
                </div>

                {threadPublishMsg && (
                  <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-semibold">
                    {threadPublishMsg}
                  </div>
                )}

                {/* Connected Vertical Spine Cards */}
                <div className="space-y-3 relative pl-6 my-2">
                  {threadResult.tweets.map((tweetText, idx) => (
                    <div key={idx} className="relative">
                      {idx < threadResult.tweets.length - 1 && (
                        <div className="absolute left-[-15px] top-6 bottom-[-16px] w-0.5 bg-purple-200 dark:bg-purple-800/60" />
                      )}
                      <div className="absolute left-[-24px] top-3 w-5 h-5 rounded-full bg-purple-100 dark:bg-purple-900 border-2 border-purple-400 dark:border-purple-600 flex items-center justify-center text-[10px] font-bold text-purple-700 dark:text-purple-300">
                        {idx + 1}
                      </div>

                      <div className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/60 space-y-2">
                        <div className="flex items-center justify-between text-[11px] text-slate-500">
                          <span className="font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
                            {idx === 0 ? "Tweet 1 (Viral Hook)" : idx === threadResult.tweets.length - 1 ? `Tweet ${idx + 1} (Conversion Closer & CTA)` : `Tweet ${idx + 1} (Atomic Takeaway)`}
                          </span>
                          <span className="font-mono text-[10px]">{tweetText.length}/280 chars</span>
                        </div>
                        <textarea
                          rows={3}
                          value={tweetText}
                          onChange={(e) => handleUpdateThreadTweet(idx, e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono text-slate-900 dark:text-white resize-none"
                        />
                      </div>
                    </div>
                  ))}
                </div>

                {/* Live X Research Dossier */}
                {threadResult.research_report && (
                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/80 border border-purple-200 dark:border-purple-900/50 space-y-3 mt-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                        <Search className="w-3.5 h-3.5 text-purple-500" />
                        <span>Live X Research Dossier & Proof Grounding</span>
                      </h4>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300">
                        {threadResult.research_report.viral_tweets?.length || 0} Viral Posts Analyzed
                      </span>
                    </div>

                    {threadResult.research_report.summary && (
                      <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed bg-white dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-800">
                        {threadResult.research_report.summary}
                      </p>
                    )}

                    {/* Consensus vs Contrarian */}
                    {threadResult.research_report.community_sentiment && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                        <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/50">
                          <span className="text-[10px] font-bold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider block mb-1">
                            Dominant X Sentiment (Consensus)
                          </span>
                          <span className="text-slate-700 dark:text-slate-300 text-[11px]">
                            {threadResult.research_report.community_sentiment.consensus_view || "General agreement across timeline."}
                          </span>
                        </div>

                        <div className="p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50">
                          <span className="text-[10px] font-bold text-amber-700 dark:text-amber-400 uppercase tracking-wider block mb-1">
                            Contrarian / Industry Critique
                          </span>
                          <span className="text-slate-700 dark:text-slate-300 text-[11px]">
                            {threadResult.research_report.community_sentiment.contrarian_view || "Alternative perspective and nuanced arguments."}
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Downloaded Media / Proof Attachments */}
                    {threadResult.downloaded_media && threadResult.downloaded_media.length > 0 && (
                      <div className="space-y-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                          Attached Media Assets ({threadResult.downloaded_media.length} Images/Statements)
                        </span>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                          {threadResult.downloaded_media.map((media: any, mIdx: number) => (
                            <div key={mIdx} className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-[11px] space-y-1">
                              <img src={media.source_url} alt="Viral Tweet Attachment" className="w-full h-24 object-cover rounded" />
                              <div className="text-slate-500 text-[10px] truncate">@{media.author_handle}</div>
                              <p className="text-slate-700 dark:text-slate-300 line-clamp-2 text-[10px]">{media.caption}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Top Viral Tweets */}
                    {threadResult.research_report.viral_tweets && threadResult.research_report.viral_tweets.length > 0 && (
                      <div className="space-y-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                          Top Viral Posts on X
                        </span>
                        <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                          {threadResult.research_report.viral_tweets.slice(0, 6).map((tw: any, tIdx: number) => (
                            <div key={tIdx} className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs flex items-start justify-between gap-2">
                              <div className="space-y-0.5">
                                <div className="flex items-center gap-1.5 text-[11px]">
                                  <span className="font-bold text-slate-900 dark:text-white">{tw.author}</span>
                                  <span className="text-slate-500 font-mono text-[10px]">@{tw.handle}</span>
                                  {tw.verified && <span className="text-blue-500 text-[10px]">✓</span>}
                                </div>
                                <p className="text-slate-600 dark:text-slate-300 text-[11px] line-clamp-2">{tw.text}</p>
                              </div>
                              <div className="text-right whitespace-nowrap text-[10px] text-slate-400 font-mono">
                                <div>{tw.views?.toLocaleString()} views</div>
                                <div>{tw.likes?.toLocaleString()} likes</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 4: INTERACTIVE POLL GENERATOR
      ───────────────────────────────────────────────────────────── */}
      {subTab === "polls" && (
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
      )}

      {/* ─────────────────────────────────────────────────────────────
          SUB-TAB 4: TREND RADAR
      ───────────────────────────────────────────────────────────── */}
      {subTab === "trends" && (
        <div className="space-y-6">
          <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-sky-500" />
                  <span>Real-Time Trend Radar & Strategic Commentary</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">Monitors live tech news & RSS feeds, scores alignment to your persona, and drafts timely commentary takes.</p>
              </div>
              <button
                onClick={handleScanTrends}
                disabled={loadingTrends}
                className="w-full sm:w-auto px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold flex items-center justify-center gap-2 transition disabled:opacity-50 shadow-md shadow-sky-600/20"
              >
                <RefreshCw className={`w-4 h-4 ${loadingTrends ? "animate-spin" : ""}`} />
                <span>Scan Live Trends</span>
              </button>
            </div>

            {trendMsg && (
              <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-semibold">
                {trendMsg}
              </div>
            )}

            {/* Trends List */}
            {trendsList.length > 0 && (
              <div className="space-y-4 pt-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Live Trend Pipeline & AI Takes
                </h4>

                <div className="space-y-3">
                  {trendsList.map((trend, i) => {
                    const draft = trendDrafts[i];
                    return (
                      <div
                        key={i}
                        className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 space-y-3"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-xs text-slate-900 dark:text-white">
                              {trend.title}
                            </span>
                            <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-sky-100 dark:bg-sky-950 text-sky-700 dark:text-sky-400">
                              {trend.alignment_score}% match
                            </span>
                          </div>
                          <span className="text-[11px] text-slate-400 capitalize">{trend.category}</span>
                        </div>

                        {draft && (
                          <div className="p-3 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                              <span className="text-[11px] font-bold text-sky-600 dark:text-sky-400 uppercase">
                                Generated Take ({draft.angle})
                              </span>
                              <button
                                onClick={() => handlePublishTrendTake(i, draft.post_text)}
                                disabled={publishingTrendTake === i}
                                className="w-full sm:w-auto px-3 py-1 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-1 transition disabled:opacity-50"
                              >
                                {publishingTrendTake === i ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                                <span>Publish Take</span>
                              </button>
                            </div>
                            <p className="text-xs text-slate-800 dark:text-slate-200 font-mono whitespace-pre-wrap">
                              {draft.post_text}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
