"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Sidebar, TabType } from "@/components/Sidebar";
import { OverviewTab } from "@/components/OverviewTab";
import { CampaignStudioTab } from "@/components/CampaignStudioTab";
import { GrowthEngineTab } from "@/components/GrowthEngineTab";
import { LiveActivityTab } from "@/components/LiveActivityTab";
import { PersonaMemoryTab } from "@/components/PersonaMemoryTab";
import { LimitsSchedulerTab } from "@/components/LimitsSchedulerTab";
import { ConnectAccountModal } from "@/components/ConnectAccountModal";
import { GlobalSettingsModal } from "@/components/GlobalSettingsModal";
import { api, Profile, Session, RateLimit, SystemHealth } from "@/lib/api";
import {
  Loader2,
  Plus,
  Layers,
  Settings,
  Sun,
  Moon,
  ChevronDown,
  Check,
  User,
  LayoutDashboard,
  Zap,
  Activity,
  Brain,
  Sliders,
  Sparkles,
} from "lucide-react";

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
  const [triggeringSession, setTriggeringSession] = useState(false);
  const [mobileProfileDropdownOpen, setMobileProfileDropdownOpen] = useState(false);

  const handleTriggerSession = async () => {
    if (!selectedProfileId) return;
    setTriggeringSession(true);
    try {
      await api.triggerSession(selectedProfileId);
      await loadProfileSessions(selectedProfileId);
    } catch (err) {
      console.error("Failed to trigger session", err);
    } finally {
      setTriggeringSession(false);
    }
  };

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

  const mobileNavItems: { id: TabType; label: string; icon: React.ElementType; badge?: string }[] = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "campaigns", label: "Studio", icon: Sparkles, badge: "AI" },
    { id: "growth", label: "Growth", icon: Zap, badge: "AI" },
    { id: "activity", label: "Activity", icon: Activity },
    { id: "persona", label: "Persona", icon: Brain },
    { id: "limits", label: "Limits", icon: Sliders },
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans antialiased transition-colors duration-200">
      {/* 1. Global Left Sidebar (Desktop Only) */}
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
        {/* Mobile Top Header */}
        <header className="lg:hidden sticky top-0 z-30 flex items-center justify-between px-4 py-3 bg-white/85 dark:bg-slate-900/85 backdrop-blur-xl border-b border-slate-200 dark:border-slate-800 shadow-sm">
          {/* App Branding */}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-500 via-indigo-500 to-violet-600 flex items-center justify-center shadow-md shadow-indigo-500/20">
              <Layers className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-sm tracking-tight text-slate-900 dark:text-white">
                  XBot Pro
                </span>
                <span className="text-[9px] uppercase tracking-wider font-extrabold px-1 py-0.2 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300">
                  v2.0
                </span>
              </div>
            </div>
          </div>

          {/* Right Action Controls */}
          <div className="flex items-center gap-2">
            {/* Mobile Profile Switcher */}
            {profiles.length > 0 && (
              <div className="relative">
                <button
                  onClick={() => setMobileProfileDropdownOpen(!mobileProfileDropdownOpen)}
                  className="flex items-center gap-1.5 p-1.5 pr-2 rounded-xl border border-slate-200 dark:border-slate-750 bg-slate-100/80 dark:bg-slate-800/80 text-xs font-semibold text-slate-800 dark:text-slate-200 transition active:scale-95"
                >
                  <div className="w-6 h-6 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex-shrink-0 flex items-center justify-center text-[10px]">
                    {selectedProfile?.avatar_url || selectedProfile?.avatar ? (
                      <img
                        src={selectedProfile.avatar_url || selectedProfile.avatar}
                        alt=""
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      selectedProfile?.display_name?.charAt(0).toUpperCase() || <User className="w-3.5 h-3.5 text-slate-400" />
                    )}
                  </div>
                  <span className="max-w-[70px] truncate font-medium text-[11px]">
                    {selectedProfile?.x_handle ? `@${selectedProfile.x_handle.replace(/^@/, "")}` : selectedProfile?.display_name || "Profile"}
                  </span>
                  <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${mobileProfileDropdownOpen ? "rotate-180" : ""}`} />
                </button>

                {/* Mobile Profile Dropdown */}
                {mobileProfileDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-56 p-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl z-50 space-y-1">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 px-2 py-1">
                      Switch Account
                    </div>
                    {profiles.map((p) => {
                      const isSelected = p.id === selectedProfileId;
                      return (
                        <button
                          key={p.id}
                          onClick={() => {
                            setSelectedProfileId(p.id);
                            setSelectedSessionId(undefined);
                            setMobileProfileDropdownOpen(false);
                          }}
                          className={`w-full flex items-center justify-between p-2 rounded-lg text-left text-xs transition ${
                            isSelected
                              ? "bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 font-semibold"
                              : "hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
                          }`}
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <div className="w-6 h-6 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex-shrink-0 flex items-center justify-center text-[10px]">
                              {p.avatar_url || p.avatar ? (
                                <img src={p.avatar_url || p.avatar} alt="" className="w-full h-full object-cover" />
                              ) : (
                                p.display_name.charAt(0).toUpperCase()
                              )}
                            </div>
                            <div className="min-w-0">
                              <p className="truncate text-xs font-semibold">{p.display_name}</p>
                              <p className="truncate text-[10px] text-slate-400">@{p.x_handle.replace(/^@/, "")}</p>
                            </div>
                          </div>
                          {isSelected && <Check className="w-3.5 h-3.5 text-indigo-500 flex-shrink-0 ml-1.5" />}
                        </button>
                      );
                    })}

                    <div className="pt-1 mt-1 border-t border-slate-100 dark:border-slate-800">
                      <button
                        onClick={() => {
                          setMobileProfileDropdownOpen(false);
                          setShowConnectModal(true);
                        }}
                        className="w-full flex items-center gap-2 p-2 rounded-lg text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/30 transition"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Connect New Account</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Dark Mode Toggle */}
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 rounded-xl text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition border border-slate-200 dark:border-slate-800"
              title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
            </button>

            {/* Global Settings */}
            <button
              onClick={() => setShowSettingsModal(true)}
              className="p-2 rounded-xl text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition border border-slate-200 dark:border-slate-800"
              title="Global Settings"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Content Container with mobile bottom padding */}
        <div className="p-4 sm:p-6 md:p-8 pb-28 lg:pb-8 max-w-7xl w-full mx-auto space-y-6">
          {loadingProfiles ? (
            <div className="h-[60vh] flex flex-col items-center justify-center gap-3 text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
              <p className="text-sm font-medium">Loading XBot accounts and state...</p>
            </div>
          ) : profiles.length === 0 ? (
            <div className="h-[60vh] flex flex-col items-center justify-center text-center p-6 sm:p-8 rounded-3xl border-2 border-dashed border-slate-200 dark:border-slate-800 max-w-lg mx-auto space-y-4">
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

              {/* Tab 2: Campaign Studio (AI Creative Director) */}
              {activeTab === "campaigns" && (
                <CampaignStudioTab
                  selectedProfile={selectedProfile}
                />
              )}

              {/* Tab 3: Growth Engine */}
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
                  onTriggerSession={handleTriggerSession}
                  triggeringSession={triggeringSession}
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

        {/* Mobile Bottom Navigation Bar */}
        <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl border-t border-slate-200 dark:border-slate-800 px-2 py-1.5 flex justify-around items-center shadow-lg">
          {mobileNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setMobileProfileDropdownOpen(false);
                }}
                className={`flex-1 flex flex-col items-center justify-center py-1 px-1 rounded-xl transition-all relative ${
                  isActive
                    ? "text-indigo-600 dark:text-indigo-400 font-bold"
                    : "text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 font-medium"
                }`}
              >
                <div className="relative">
                  <Icon className={`w-5 h-5 transition-transform ${isActive ? "scale-110" : ""}`} />
                  {item.badge && (
                    <span className="absolute -top-1 -right-2 text-[8px] font-extrabold px-1 rounded-full bg-indigo-600 text-white">
                      {item.badge}
                    </span>
                  )}
                </div>
                <span className="text-[10px] tracking-tight mt-0.5">{item.label}</span>
                {isActive && (
                  <span className="absolute bottom-0 w-8 h-0.5 bg-indigo-600 dark:bg-indigo-400 rounded-full" />
                )}
              </button>
            );
          })}
        </nav>
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
