"use client";

import React, { useEffect } from "react";
import { useAppStore } from "@/store/useAppStore";
import { DesktopSidebar } from "@/components/layout/DesktopSidebar";
import { MobileHeader } from "@/components/layout/MobileHeader";
import { MobileNavigation } from "@/components/layout/MobileNavigation";
import { OverviewTab } from "@/features/overview/OverviewTab";
import { CampaignStudioTab } from "@/features/campaign-studio/CampaignStudioTab";
import { GrowthEngineTab } from "@/features/growth-engine/GrowthEngineTab";
import { LiveActivityTab } from "@/features/live-activity/LiveActivityTab";
import { PersonaMemoryTab } from "@/features/persona/PersonaMemoryTab";
import { LimitsSchedulerTab } from "@/features/limits-scheduler/LimitsSchedulerTab";
import { ConnectAccountModal } from "@/features/settings/ConnectAccountModal";
import { GlobalSettingsModal } from "@/features/settings/GlobalSettingsModal";
import { BottomConsole } from "@/components/layout/BottomConsole";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { Loader2 } from "lucide-react";

export default function DashboardPage() {
  const {
    profiles,
    selectedProfileId,
    activeTab,
    sessions,
    rateLimits,
    loadingProfiles,
    showConnectModal,
    showSettingsModal,
    setModals,
    loadInitialData,
    triggerSession,
    loadProfileSessions
  } = useAppStore();

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        setModals({ settings: false, connect: false });
        useAppStore.getState().setCommandPaletteOpen(!useAppStore.getState().isCommandPaletteOpen);
      }
      if ((e.metaKey || e.ctrlKey) && (e.key === "\\" || e.key === "|" || e.code === "Backslash")) {
        e.preventDefault();
        useAppStore.getState().setConsoleOpen(!useAppStore.getState().isConsoleOpen);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [setModals]);

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 dark:bg-slate-950 font-sans antialiased transition-colors duration-200">
      <DesktopSidebar />

      <main className="flex-1 flex flex-col h-screen overflow-y-auto relative pb-16 lg:pb-0">
        <MobileHeader />
        
        <div className="flex-1 p-4 lg:p-6 pb-24 lg:pb-6 relative z-10 w-full max-w-7xl mx-auto">
          {loadingProfiles ? (
            <div className="w-full h-full flex flex-col items-center justify-center space-y-4">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
              <p className="text-sm font-medium text-slate-500">Connecting to Backend...</p>
            </div>
          ) : !selectedProfile ? (
            <div className="w-full h-full flex flex-col items-center justify-center space-y-4 text-center">
              <div className="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-4">
                <Loader2 className="w-8 h-8 text-slate-400" />
              </div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-50">No Profiles Connected</h2>
              <p className="text-sm text-slate-500 max-w-sm">
                Connect an X account to begin using the workspace.
              </p>
              <button
                onClick={() => setModals({ connect: true })}
                className="mt-4 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md transition"
              >
                Connect Account
              </button>
            </div>
          ) : (
            <>
              {activeTab === "overview" && (
                <OverviewTab
                  profile={selectedProfile}
                  sessions={sessions}
                  rateLimits={rateLimits}
                  onRefresh={() => {
                    loadInitialData();
                  }}
                  onNavigateToTab={(tab) => useAppStore.getState().setActiveTab(tab)}
                  onSelectSession={(sId) => useAppStore.getState().setSelectedSessionId(sId)}
                />
              )}

              {activeTab === "campaigns" && (
                <CampaignStudioTab
                  selectedProfile={selectedProfile}
                />
              )}

              {activeTab === "growth" && (
                <GrowthEngineTab
                  profileId={selectedProfile.id}
                  selectedProfile={selectedProfile}
                />
              )}

              {activeTab === "activity" && (
                <LiveActivityTab
                  profileId={selectedProfile.id}
                  selectedProfile={selectedProfile}
                  initialSessionId={useAppStore.getState().selectedSessionId}
                  onTriggerSession={triggerSession}
                  triggeringSession={false} // Will integrate loading state later if needed
                />
              )}

              {activeTab === "persona" && (
                <PersonaMemoryTab
                  profileId={selectedProfile.id}
                  selectedProfile={selectedProfile}
                  onRefresh={loadInitialData}
                />
              )}

              {activeTab === "limits" && (
                <LimitsSchedulerTab
                  profileId={selectedProfile.id}
                  selectedProfile={selectedProfile}
                  onRefresh={loadInitialData}
                />
              )}
            </>
          )}
        </div>
      </main>

      {/* Modals */}
      {showConnectModal && (
        <ConnectAccountModal
          isOpen={showConnectModal}
          onClose={() => setModals({ connect: false })}
          profile={selectedProfile || null}
          onSuccess={() => {
            setModals({ connect: false });
            loadInitialData();
          }}
        />
      )}

      {showSettingsModal && (
        <GlobalSettingsModal
          isOpen={showSettingsModal}
          onClose={() => setModals({ settings: false })}
          onSaved={() => loadInitialData()}
        />
      )}

      <BottomConsole />
      <CommandPalette />
      <MobileNavigation />
    </div>
  );
}
