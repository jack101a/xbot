import React from "react";
import { Profile, Session, RateLimit } from "@/lib/api";
import { useOverviewState } from "./hooks/useOverviewState";
import { useQuickComposer } from "./hooks/useQuickComposer";
import { SystemHealthBanner } from "./components/SystemHealthBanner";
import { ProfileHeroCard } from "./components/ProfileHeroCard";
import { QuickLiveComposer } from "./components/QuickLiveComposer";
import { PendingApprovals } from "./components/PendingApprovals";
import { MonetizationTracker } from "./components/MonetizationTracker";
import { ProfileSummaryCards } from "./components/ProfileSummaryCards";
import { ActionLimits } from "./components/ActionLimits";
import { RecentActivitiesFeed } from "./components/RecentActivitiesFeed";
import { LivePostsLog } from "./components/LivePostsLog";

export interface OverviewTabProps {
  profile: Profile;
  sessions: Session[];
  rateLimits: RateLimit[];
  onRefresh: () => void;
  onNavigateToTab: (tab: "growth" | "activity" | "persona" | "limits") => void;
  onSelectSession?: (sessionId: string) => void;
}

export function OverviewTab({
  profile,
  sessions,
  rateLimits,
  onRefresh,
  onNavigateToTab,
  onSelectSession
}: OverviewTabProps) {
  const overviewState = useOverviewState(profile, onRefresh);
  const composerState = useQuickComposer(profile, onRefresh);

  return (
    <div className="space-y-4">
      {/* Alert Banner */}
      <SystemHealthBanner
        actionMsg={overviewState.actionMsg}
        onDismiss={() => overviewState.setActionMsg(null)}
      />

      {/* Main High-Density Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Top Row Left (spans 2): Hero Profile Card */}
        <div className="lg:col-span-2">
          <ProfileHeroCard
            profile={profile}
            syncing={overviewState.syncing}
            triggering={overviewState.triggering}
            onSyncFromX={overviewState.handleSyncFromX}
            onTogglePause={overviewState.handleTogglePause}
            onRunSession={overviewState.handleRunSession}
          />
        </div>

        {/* Top Row Right (spans 1): Quick Live Composer */}
        <div className="lg:col-span-1">
          <QuickLiveComposer profile={profile} {...composerState} fileInputRef={composerState.fileInputRef as React.RefObject<HTMLInputElement>} />
        </div>

        {/* Pending Post & Poll Approvals */}
        <PendingApprovals
          drafts={overviewState.drafts}
          approvingId={overviewState.approvingId}
          onApproveAll={overviewState.handleApproveAllDrafts}
          onDismissAll={overviewState.handleDismissAllDrafts}
          onApproveDraft={overviewState.handleApproveDraft}
          onDismissDraft={overviewState.handleDismissDraft}
        />

        {/* Monetization Milestones & 28-Day Deep Analytics (spans 3) */}
        <div className="lg:col-span-3">
          <MonetizationTracker
            deepAnalytics={overviewState.deepAnalytics}
            syncingAnalytics={overviewState.syncingAnalytics}
            onSyncLiveAnalytics={overviewState.handleSyncLiveAnalytics}
          />
        </div>

        {/* 6 Real-Time Metric Stat Cards (spans 3) */}
        <div className="lg:col-span-3">
          <ProfileSummaryCards
            profile={profile}
            deepAnalytics={overviewState.deepAnalytics}
            sessions={sessions}
          />
        </div>

        {/* 24h Action Limits & Recent Sessions (spans 3) */}
        <div className="lg:col-span-3">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <ActionLimits
              profile={profile}
              rateLimits={rateLimits}
              onNavigateToTab={onNavigateToTab}
            />
            <RecentActivitiesFeed
              sessions={sessions}
              onNavigateToTab={onNavigateToTab}
              onSelectSession={onSelectSession}
              onRunSession={overviewState.handleRunSession}
            />
          </div>
        </div>

        {/* Live Account Posts & Activity Log (spans 3) */}
        <LivePostsLog profile={profile} />
      </div>
    </div>
  );
}
