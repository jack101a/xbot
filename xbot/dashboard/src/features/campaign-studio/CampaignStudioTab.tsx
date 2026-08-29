"use client";

import React from "react";
import { CampaignStudioTabProps } from "./types";
import { useCampaignState } from "./hooks/useCampaignState";
import { CampaignConfiguration } from "./components/CampaignConfiguration";
import { CampaignProgress } from "./components/CampaignProgress";
import { DeliverablesBoard } from "./components/DeliverablesBoard";
import { EmptyState } from "./components/EmptyState";

export function CampaignStudioTab({ selectedProfile }: CampaignStudioTabProps) {
  const {
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
  } = useCampaignState(selectedProfile);

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:h-[calc(100vh-120px)] items-start">
      <CampaignConfiguration
        selectedProfile={selectedProfile}
        errorMessage={errorMessage}
        publishSuccessMessage={publishSuccessMessage}
        prompt={prompt}
        setPrompt={setPrompt}
        isGenerating={isGenerating}
        handleStartCampaign={handleStartCampaign}
      />

      <div className="flex-1 w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 overflow-y-auto h-full flex flex-col">
        <CampaignProgress
          campaignStatus={campaignStatus}
          isGenerating={isGenerating}
        />

        {campaignStatus?.deliverables && campaignStatus.deliverables.length > 0 ? (
          <DeliverablesBoard
            campaignStatus={campaignStatus}
            selectedDeliverableIds={selectedDeliverableIds}
            toggleSelectDeliverable={toggleSelectDeliverable}
            selectAllDeliverables={selectAllDeliverables}
            deselectAllDeliverables={deselectAllDeliverables}
            scheduleInterval={scheduleInterval}
            setScheduleInterval={setScheduleInterval}
            isPublishing={isPublishing}
            handlePublishDeliverables={handlePublishDeliverables}
            handlePublishSingleDeliverable={handlePublishSingleDeliverable}
            publishingItemIds={publishingItemIds}
            publishedStatus={publishedStatus}
          />
        ) : !isGenerating ? (
          <EmptyState />
        ) : null}
      </div>
    </div>
  );
}
