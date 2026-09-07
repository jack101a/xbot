"use client";

import React, { useEffect } from "react";
import { useAppStore, TabType } from "@/store/useAppStore";
import { initPopStateListener } from "@/store/navigationSync";
import { DesktopSidebar } from "@/components/layout/DesktopSidebar";
import { DesktopTopBar } from "@/components/layout/DesktopTopBar";
import { MobileHeader } from "@/components/layout/MobileHeader";
import { MobileNavigation } from "@/components/layout/MobileNavigation";
import { OverviewTab } from "@/features/overview/OverviewTab";
import { CampaignStudioTab } from "@/features/campaign-studio/CampaignStudioTab";
import { GrowthEngineTab } from "@/features/growth-engine/GrowthEngineTab";
import { LiveActivityTab } from "@/features/live-activity/LiveActivityTab";
import { PersonaMemoryTab } from "@/features/persona/PersonaMemoryTab";
import { LimitsSchedulerTab } from "@/features/limits-scheduler/LimitsSchedulerTab";
import { PostPrunerTab } from "@/features/post-pruner/PostPrunerTab";
import { AILogsTab } from "@/features/ai-logs/AILogsTab";
import { ConnectAccountModal } from "@/features/settings/ConnectAccountModal";
import { GlobalSettingsModal } from "@/features/settings/GlobalSettingsModal";
import { BottomConsole } from "@/components/layout/BottomConsole";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { Loader2 } from "lucide-react";

export default function DashboardPage() {
  const {
    profiles,
    selectedProfileId,
    selectedSessionId,
    activeTab,
    subTabs,
    sessions,
    rateLimits,
    loadingProfiles,
    triggeringSession,
    showConnectModal,
    showSettingsModal,
    setModals,
    setSubTab,
    loadInitialData,
    triggerSession,
  } = useAppStore();

  // Initial load of backend data
  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Listen for browser Back/Forward navigation and mobile swipe-back gestures
  useEffect(() => {
    const cleanup = initPopStateListener((nav) => {
      useAppStore.setState((state) => ({
        activeTab: nav.tab,
        subTabs: nav.subTab ? { ...state.subTabs, [nav.tab]: nav.subTab } : state.subTabs,
        selectedProfileId: nav.profileId !== undefined ? nav.profileId : state.selectedProfileId,
        selectedSessionId: nav.sessionId,
        showConnectModal: nav.modal === "connect",
        showSettingsModal: nav.modal === "settings",
        mobileMenuOpen: nav.modal === "menu",
      }));
    });
    return cleanup;
  }, []);

  // Keyboard shortcuts (Desktop)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isModifier = e.metaKey || e.ctrlKey;

      if (isModifier && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        setModals({ settings: false, connect: false });
        useAppStore.getState().setCommandPaletteOpen(!useAppStore.getState().isCommandPaletteOpen);
        return;
      }

      if (isModifier && (e.key === "\\" || e.key === "|" || e.code === "Backslash")) {
        e.preventDefault();
        useAppStore.getState().setConsoleOpen(!useAppStore.getState().isConsoleOpen);
        return;
      }

      if (isModifier && ["1", "2", "3", "4", "5", "6", "7"].includes(e.key)) {
        e.preventDefault();
        const tabMap: Record<string, TabType> = {
          "1": "overview",
          "2": "campaigns",
          "3": "growth",
          "4": "activity",
          "5": "persona",
          "6": "limits",
          "7": "pruner",
        };
        const targetTab = tabMap[e.key];
        if (targetTab) {
          useAppStore.getState().setActiveTab(targetTab);
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [setModals]);

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId);

  return (
    <div className="flex h-[100dvh] w-screen overflow-hidden bg-slate-50 dark:bg-slate-950 font-sans antialiased transition-colors duration-200">
      <DesktopSidebar />

      <main className="flex-1 flex flex-col h-[100dvh] overflow-y-auto relative touch-scroll pb-20 lg:pb-0">
        <MobileHeader />
        <DesktopTopBar />
        
        <div className="flex-1 p-3.5 sm:p-5 lg:p-6 pb-28 lg:pb-8 relative z-10 w-full max-w-7xl mx-auto">
          {loadingProfiles ? (
            <div className="w-full h-full min-h-[50vh] flex flex-col items-center justify-center space-y-4">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
              <p className="text-sm font-medium text-slate-500">Connecting to Backend...</p>
            </div>
          ) : !selectedProfile ? (
            <div className="w-full h-full min-h-[50vh] flex flex-col items-center justify-center space-y-4 text-center px-4">
              <div className="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-2 shadow-xs">
                <Loader2 className="w-8 h-8 text-slate-400" />
              </div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-50">No Profiles Connected</h2>
              <p className="text-sm text-slate-500 max-w-sm">
                Connect an X account to begin using the workspace.
              </p>
              <button
                onClick={() => setModals({ connect: true })}
                className="mt-4 px-6 py-3 min-h-[48px] bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition active:scale-95 shadow-xs"
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
                  activeSubTab={subTabs.growth as any}
                  onSubTabChange={(st) => setSubTab("growth", st)}
                />
              )}

              {activeTab === "activity" && (
                <LiveActivityTab
                  profileId={selectedProfile.id}
                  selectedProfile={selectedProfile}
                  initialSessionId={selectedSessionId}
                  activeView={subTabs.activity as any}
                  onViewChange={(v) => setSubTab("activity", v)}
                  onTriggerSession={triggerSession}
                  triggeringSession={triggeringSession}
                />
              )}

              {activeTab === "persona" && (
                <PersonaMemoryTab
                  profileId={selectedProfile.id}
                  selectedProfile={selectedProfile}
                  activeSubTab={subTabs.persona}
                  onSubTabChange={(st) => setSubTab("persona", st)}
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

              {activeTab === "pruner" && (
                <PostPrunerTab />
              )}

              {activeTab === "ai-logs" && (
                <AILogsTab />
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
