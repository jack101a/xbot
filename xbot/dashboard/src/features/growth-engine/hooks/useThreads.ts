import { useState } from "react";
import { api } from "@/lib/api";

export function useThreads(profileId: string) {
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


  return {
    threadTopic, setThreadTopic,
    threadArchetype, setThreadArchetype,
    threadNumTweets, setThreadNumTweets,
    threadDeepResearch, setThreadDeepResearch,
    threadGenerating, setThreadGenerating,
    threadResult, setThreadResult,
    publishingThread, setPublishingThread,
    threadPublishMsg, setThreadPublishMsg,
    handleGenerateThread,
    handleUpdateThreadTweet,
    handlePublishLiveThread
  };
}
