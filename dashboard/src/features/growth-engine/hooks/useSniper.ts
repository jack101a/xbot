import { useState } from "react";
import { api } from "@/lib/api";

export function useSniper(profileId: string) {
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

  // 1. Generate Sniper Reply via Real AI
  const handleGenerateReply = async () => {
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


  return {
    sniperTweetText, setSniperTweetText,
    sniperAuthor, setSniperAuthor,
    sniperAngle, setSniperAngle,
    sniperTargetUrl, setSniperTargetUrl,
    sniperGenerating, setSniperGenerating,
    sniperResult, setSniperResult,
    publishingReply, setPublishingReply,
    replyPublishMsg, setReplyPublishMsg,
    handleGenerateReply,
    handlePublishLiveReply
  };
}
