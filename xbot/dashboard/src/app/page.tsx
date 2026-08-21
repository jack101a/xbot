"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Sidebar, TabType } from "@/components/Sidebar";
import { OverviewTab } from "@/components/OverviewTab";
import { GrowthEngineTab } from "@/components/GrowthEngineTab";
import { LiveActivityTab } from "@/components/LiveActivityTab";
import { PersonaMemoryTab } from "@/components/PersonaMemoryTab";
import { LimitsSchedulerTab } from "@/components/LimitsSchedulerTab";
import { ConnectAccountModal } from "@/components/ConnectAccountModal";
import { GlobalSettingsModal } from "@/components/GlobalSettingsModal";
import { api, Profile, Session, RateLimit, SystemHealth } from "@/lib/api";
import { Loader2, Plus } from "lucide-react";

export default function DashboardPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [selectedSessionId, setSelectedSessionId] = useState<string | undefined>(undefined);

  const [sessions, setSessions] = useState<Session[]>([]);
  const [rateLimits, setRateLimits] = useState<RateLimit[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);

  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [darkMode, setDarkMode] = useState(true);

  // Initialize theme from document or state
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [darkMode]);

  // Load profiles and system health
  const loadProfiles = useCallback(async () => {
    try {
      const [pList, health, limits] = await Promise.all([
        api.listProfiles(),
        api.getHealth().catch(() => null),
        api.getRateLimits().catch(() => [])
      ]);

      setProfiles(pList || []);
      setSystemHealth(health);
      setRateLimits(limits || []);

      if (pList && pList.length > 0) {
        setSelectedProfileId((current) => {
          if (current && pList.some((p) => p.id === current)) return current;
          return pList[0].id;
        });
      } else {
        setSelectedProfileId(null);
      }
    } catch (err) {
      console.error("Failed to load initial dashboard data", err);
    } finally {
      setLoadingProfiles(false);
    }
  }, []);

  // Load sessions for active profile
  const loadProfileSessions = useCallback(async (profileId: string) => {
    try {
      const sList = await api.getProfileSessions(profileId, 50);
      setSessions(sList || []);
    } catch (err) {
      console.error("Failed to load profile sessions", err);
    }
  }, []);

  useEffect(() => {
    loadProfiles();
  }, [loadProfiles]);

  useEffect(() => {
    if (selectedProfileId) {
      loadProfileSessions(selectedProfileId);
    } else {
      setSessions([]);
    }
  }, [selectedProfileId, loadProfileSessions]);

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans antialiased transition-colors duration-200">
      {/* 1. Global Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        profiles={profiles}
        selectedProfileId={selectedProfileId}
        onSelectProfile={(id) => {
          setSelectedProfileId(id);
          setSelectedSessionId(undefined);
        }}
        onAddProfile={() => setShowConnectModal(true)}
        systemHealth={systemHealth}
        onOpenSettings={() => setShowSettingsModal(true)}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode(!darkMode)}
      />

      {/* 2. Main Content Canvas */}
      <main className="flex-1 flex flex-col h-screen overflow-y-auto bg-slate-50/50 dark:bg-slate-950/50 relative">
        <div className="p-6 md:p-8 max-w-7xl w-full mx-auto space-y-6">
          {loadingProfiles ? (
            <div className="h-[70vh] flex flex-col items-center justify-center gap-3 text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
              <p className="text-sm font-medium">Loading XBot accounts and state...</p>
            </div>
          ) : profiles.length === 0 ? (
            <div className="h-[70vh] flex flex-col items-center justify-center text-center p-8 rounded-3xl border-2 border-dashed border-slate-200 dark:border-slate-800 max-w-lg mx-auto space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-950 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-inner">
                <Plus className="w-8 h-8" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">No Profiles Connected</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm">
                  Connect your first X account using cookies or browser login to begin autonomous persona growth.
                </p>
              </div>
              <button
                onClick={() => setShowConnectModal(true)}
                className="px-5 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-600/25 transition"
              >
                Connect X Account
              </button>
            </div>
          ) : !selectedProfile ? (
            <div className="py-20 text-center text-sm text-slate-400">Please select an active profile.</div>
          ) : (
            <>
              {/* Tab 1: Overview */}
              {activeTab === "overview" && (
                <OverviewTab
                  profile={selectedProfile}
                  sessions={sessions}
                  rateLimits={rateLimits}
                  onRefresh={() => {
                    loadProfiles();
                    if (selectedProfileId) loadProfileSessions(selectedProfileId);
                  }}
                  onNavigateToTab={(tab) => setActiveTab(tab as TabType)}
                  onSelectSession={(sId) => setSelectedSessionId(sId)}
                />
              )}

              {/* Tab 2: Growth Engine */}
              {activeTab === "growth" && (
                <GrowthEngineTab
                  profileId={selectedProfile.id}
                  selectedProfile={selectedProfile}
                />
              )}

              {/* Tab 3: Live Activity */}
              {activeTab === "activity" && (
                <LiveActivityTab
                  profileId={selectedProfile.id}
                  selectedProfile={selectedProfile}
                  initialSessionId={selectedSessionId}
                />
              )}

              {/* Tab 4: Persona & Memory */}
              {activeTab === "persona" && (
                <PersonaMemoryTab
                  profileId={selectedProfile.id}
                  selectedProfile={selectedProfile}
                  onRefresh={loadProfiles}
                />
              )}

              {/* Tab 5: Limits & Safety */}
              {activeTab === "limits" && (
                <LimitsSchedulerTab
                  profileId={selectedProfile.id}
                  selectedProfile={selectedProfile}
                  onRefresh={loadProfiles}
                />
              )}
            </>
          )}
        </div>
      </main>

      {/* 3. Connect Account Modal */}
      {showConnectModal && (
        <ConnectAccountModal
          isOpen={showConnectModal}
          onClose={() => setShowConnectModal(false)}
          profile={selectedProfile || null}
          onSuccess={() => {
            loadProfiles();
            setShowConnectModal(false);
          }}
        />
      )}

      {/* 4. Global Settings Modal */}
      {showSettingsModal && (
        <GlobalSettingsModal
          isOpen={showSettingsModal}
          onClose={() => setShowSettingsModal(false)}
          onSaved={loadProfiles}
        />
      )}
    </div>
  );
}
