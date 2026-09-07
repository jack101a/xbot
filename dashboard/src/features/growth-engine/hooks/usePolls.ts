import { useState } from "react";
import { api } from "@/lib/api";

export function usePolls(profileId: string) {
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


  return {
    pollTopic, setPollTopic,
    generatingPoll, setGeneratingPoll,
    generatedPoll, setGeneratedPoll,
    publishingPoll, setPublishingPoll,
    pollSuccessMsg, setPollSuccessMsg,
    handleGeneratePoll,
    handlePublishLivePoll
  };
}
