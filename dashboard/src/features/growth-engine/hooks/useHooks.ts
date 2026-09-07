import { useState } from "react";
import { api } from "@/lib/api";
import { HookCandidate } from "../types";

export function useHooks(profileId: string) {
  // Hook Optimizer Interactive State
  const [hookDraftText, setHookDraftText] = useState("Without deterministic state machines and sliding-window rate limiters, browser bots get banned in hours. Rigorous sandboxes beat model scale.");
  const [hookTopic, setHookTopic] = useState("Deterministic State in Autonomous AI Agents");
  const [hookOptimizing, setHookOptimizing] = useState(false);
  const [hookCandidates, setHookCandidates] = useState<HookCandidate[]>([]);
  const [winningHook, setWinningHook] = useState<HookCandidate | null>(null);
  const [optimizedPostResult, setOptimizedPostResult] = useState<string | null>(null);
  const [publishingPost, setPublishingPost] = useState(false);
  const [postPublishMsg, setPostPublishMsg] = useState<string | null>(null);

  // 2. Run Hook Optimizer via Real AI
  const handleOptimizeHooks = async () => {
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
  const handlePublishHookPost = async () => {
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


  return {
    hookDraftText, setHookDraftText,
    hookTopic, setHookTopic,
    hookOptimizing, setHookOptimizing,
    hookCandidates, setHookCandidates,
    winningHook, setWinningHook,
    optimizedPostResult, setOptimizedPostResult,
    publishingPost, setPublishingPost,
    postPublishMsg, setPostPublishMsg,
    handleOptimizeHooks,
    handlePublishHookPost
  };
}
