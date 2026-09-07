"use client";

import React from "react";
import { useSniper } from "../hooks/useSniper";
import { usePersona } from "../hooks/usePersona";
import { TargetKolRegistry } from "./TargetKolRegistry";
import { SniperSimulator } from "./SniperSimulator";

export function SniperTab({ profileId }: { profileId: string }) {
  const {
    sniperTweetText,
    setSniperTweetText,
    sniperAuthor,
    setSniperAuthor,
    sniperAngle,
    setSniperAngle,
    sniperTargetUrl,
    setSniperTargetUrl,
    sniperGenerating,
    sniperResult,
    publishingReply,
    replyPublishMsg,
    handleGenerateReply,
    handlePublishLiveReply,
  } = useSniper(profileId);

  const {
    targetKols,
    newKolHandle,
    setNewKolHandle,
    newKolAngle,
    setNewKolAngle,
    newKolPriority,
    setNewKolPriority,
    savingKols,
    handleAddKol,
    handleRemoveKol,
    kolActionMsg,
  } = usePersona(profileId);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6">
      <TargetKolRegistry
        targetKols={targetKols}
        newKolHandle={newKolHandle}
        setNewKolHandle={setNewKolHandle}
        newKolAngle={newKolAngle}
        setNewKolAngle={setNewKolAngle}
        newKolPriority={newKolPriority}
        setNewKolPriority={setNewKolPriority}
        savingKols={savingKols}
        handleAddKol={handleAddKol}
        handleRemoveKol={handleRemoveKol}
        kolActionMsg={kolActionMsg}
      />

      <SniperSimulator
        sniperAuthor={sniperAuthor}
        setSniperAuthor={setSniperAuthor}
        sniperAngle={sniperAngle}
        setSniperAngle={setSniperAngle}
        sniperTweetText={sniperTweetText}
        setSniperTweetText={setSniperTweetText}
        sniperGenerating={sniperGenerating}
        handleGenerateReply={handleGenerateReply}
        sniperResult={sniperResult}
        sniperTargetUrl={sniperTargetUrl}
        setSniperTargetUrl={setSniperTargetUrl}
        publishingReply={publishingReply}
        handlePublishLiveReply={handlePublishLiveReply}
        replyPublishMsg={replyPublishMsg}
      />
    </div>
  );
}
