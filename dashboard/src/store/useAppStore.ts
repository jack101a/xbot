import { create } from 'zustand';
import { api, Profile, SystemHealth, RateLimit, Session } from '@/lib/api';
import { getInitialNavState, syncUrlToBrowser } from './navigationSync';

export type TabType = "overview" | "campaigns" | "growth" | "activity" | "persona" | "limits" | "pruner" | "ai-logs";

interface AppState {
  // Data State
  profiles: Profile[];
  selectedProfileId: string | null;
  systemHealth: SystemHealth | null;
  rateLimits: RateLimit[];
  loadingProfiles: boolean;
  sessions: Session[];
  selectedSessionId: string | undefined;

  // UI State
  activeTab: TabType;
  subTabs: Record<string, string>;
  darkMode: boolean;
  showConnectModal: boolean;
  showSettingsModal: boolean;
  mobileMenuOpen: boolean;
  isConsoleOpen: boolean;
  isCommandPaletteOpen: boolean;
  sidebarCollapsed: boolean;
  triggeringSession: boolean;
  activityStream: { id: string; timestamp: number; message: string; type: "info" | "success" | "error" }[];

  // Actions
  setActiveTab: (tab: TabType, subTab?: string, pushHistory?: boolean) => void;
  setSubTab: (tab: TabType, subTab: string, pushHistory?: boolean) => void;
  setSelectedProfileId: (id: string | null) => void;
  setSelectedSessionId: (id: string | undefined) => void;
  setDarkMode: (mode: boolean) => void;
  setModals: (modals: Partial<{ connect: boolean; settings: boolean; mobileMenu: boolean }>) => void;
  setConsoleOpen: (isOpen: boolean) => void;
  setCommandPaletteOpen: (isOpen: boolean) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebarCollapsed: () => void;
  appendActivityLog: (message: string, type?: "info" | "success" | "error") => void;
  
  // Async Actions
  loadInitialData: (showLoading?: boolean) => Promise<void>;
  loadProfileSessions: (profileId: string) => Promise<void>;
  triggerSession: () => Promise<void>;
}

const initialNav = getInitialNavState();

export const useAppStore = create<AppState>((set, get) => ({
  profiles: [],
  selectedProfileId: initialNav.profileId || null,
  systemHealth: null,
  rateLimits: [],
  loadingProfiles: true,
  sessions: [],
  selectedSessionId: initialNav.sessionId || undefined,
  triggeringSession: false,
  
  activeTab: initialNav.tab || 'overview',
  subTabs: {
    growth: initialNav.tab === 'growth' && initialNav.subTab ? initialNav.subTab : 'f4f',
    persona: initialNav.tab === 'persona' && initialNav.subTab ? initialNav.subTab : 'identity',
    activity: initialNav.tab === 'activity' && initialNav.subTab ? initialNav.subTab : 'timeline',
  },
  darkMode: true,
  showConnectModal: initialNav.modal === 'connect',
  showSettingsModal: initialNav.modal === 'settings',
  mobileMenuOpen: initialNav.modal === 'menu',
  isConsoleOpen: false,
  isCommandPaletteOpen: false,
  sidebarCollapsed: false,
  activityStream: [],

  setActiveTab: (tab, subTab, pushHistory = true) => {
    const currentSub = subTab || get().subTabs[tab];
    set((state) => ({
      activeTab: tab,
      mobileMenuOpen: false,
      subTabs: currentSub ? { ...state.subTabs, [tab]: currentSub } : state.subTabs,
    }));
    syncUrlToBrowser({
      tab,
      subTab: currentSub,
      profileId: get().selectedProfileId,
      sessionId: get().selectedSessionId,
      modal: null,
    }, pushHistory);
  },

  setSubTab: (tab, subTab, pushHistory = true) => {
    set((state) => ({
      subTabs: { ...state.subTabs, [tab]: subTab },
    }));
    syncUrlToBrowser({
      tab: get().activeTab === tab ? tab : get().activeTab,
      subTab,
      profileId: get().selectedProfileId,
      sessionId: get().selectedSessionId,
    }, pushHistory);
  },

  setSelectedProfileId: (id) => {
    set({ selectedProfileId: id, selectedSessionId: undefined });
    syncUrlToBrowser({
      profileId: id,
      sessionId: undefined,
    }, false);
    if (id) {
      get().loadProfileSessions(id);
    }
  },

  setSelectedSessionId: (id) => {
    set({ selectedSessionId: id });
    syncUrlToBrowser({
      sessionId: id,
    }, false);
  },

  setDarkMode: (mode) => {
    set({ darkMode: mode });
    if (typeof window !== 'undefined') {
      if (mode) document.documentElement.classList.add('dark');
      else document.documentElement.classList.remove('dark');
    }
  },

  setModals: ({ connect, settings, mobileMenu }) => set((state) => {
    const nextConnect = connect ?? state.showConnectModal;
    const nextSettings = settings ?? state.showSettingsModal;
    const nextMenu = mobileMenu ?? state.mobileMenuOpen;

    let activeModal: "connect" | "settings" | "menu" | null = null;
    if (nextConnect) activeModal = "connect";
    else if (nextSettings) activeModal = "settings";
    else if (nextMenu) activeModal = "menu";

    const opening = activeModal !== null && !state.showConnectModal && !state.showSettingsModal && !state.mobileMenuOpen;
    syncUrlToBrowser({ modal: activeModal }, opening);

    return {
      showConnectModal: nextConnect,
      showSettingsModal: nextSettings,
      mobileMenuOpen: nextMenu,
    };
  }),

  setConsoleOpen: (isOpen) => set({ isConsoleOpen: isOpen }),
  setCommandPaletteOpen: (isOpen) => set({ isCommandPaletteOpen: isOpen }),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  toggleSidebarCollapsed: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  appendActivityLog: (message, type = "info") => set((state) => {
    const newLog = { id: Math.random().toString(36).substring(2, 11), timestamp: Date.now(), message, type };
    return { activityStream: [newLog, ...state.activityStream].slice(0, 100) };
  }),

  loadInitialData: async (showLoading = false) => {
    if (showLoading || get().profiles.length === 0) {
      set({ loadingProfiles: true });
    }
    try {
      const [profiles, health, limits] = await Promise.all([
        api.listProfiles().catch((err) => {
          console.error("Failed to list profiles", err);
          return [];
        }),
        api.getHealth().catch((err) => {
          console.error("Failed to get health", err);
          return null;
        }),
        api.getRateLimits().catch((err) => {
          console.error("Failed to get rate limits", err);
          return [];
        })
      ]);
      
      const currentSelected = get().selectedProfileId;
      const nextSelected = currentSelected && profiles.find(p => p.id === currentSelected) 
        ? currentSelected 
        : (profiles[0]?.id || null);

      set({ 
        profiles: profiles || [], 
        systemHealth: health, 
        rateLimits: limits || [], 
        selectedProfileId: nextSelected,
        loadingProfiles: false 
      });

      if (nextSelected) {
        syncUrlToBrowser({ profileId: nextSelected }, false);
        get().loadProfileSessions(nextSelected);
      }
    } catch (err) {
      console.error("Failed to load dashboard data", err);
      set({ loadingProfiles: false });
    }
  },

  loadProfileSessions: async (profileId: string) => {
    try {
      const sList = await api.getProfileSessions(profileId, 50);
      set({ sessions: sList || [] });
    } catch (err) {
      console.error("Failed to load profile sessions", err);
    }
  },

  triggerSession: async () => {
    const { selectedProfileId } = get();
    if (!selectedProfileId) return;
    set({ triggeringSession: true });
    try {
      await api.triggerSession(selectedProfileId);
      await get().loadProfileSessions(selectedProfileId);
    } catch (err) {
      console.error("Failed to trigger session", err);
    } finally {
      set({ triggeringSession: false });
    }
  }
}));
