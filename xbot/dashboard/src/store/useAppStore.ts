import { create } from 'zustand';
import { api, Profile, SystemHealth, RateLimit, Session } from '@/lib/api';

export type TabType = "overview" | "campaigns" | "growth" | "activity" | "persona" | "limits";

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
  darkMode: boolean;
  showConnectModal: boolean;
  showSettingsModal: boolean;
  mobileMenuOpen: boolean;
  isConsoleOpen: boolean;
  isCommandPaletteOpen: boolean;
  activityStream: { id: string; timestamp: number; message: string; type: "info" | "success" | "error" }[];

  // Actions
  setActiveTab: (tab: TabType) => void;
  setSelectedProfileId: (id: string | null) => void;
  setSelectedSessionId: (id: string | undefined) => void;
  setDarkMode: (mode: boolean) => void;
  setModals: (modals: Partial<{ connect: boolean; settings: boolean; mobileMenu: boolean }>) => void;
  setConsoleOpen: (isOpen: boolean) => void;
  setCommandPaletteOpen: (isOpen: boolean) => void;
  appendActivityLog: (message: string, type?: "info" | "success" | "error") => void;
  
  // Async Actions
  loadInitialData: () => Promise<void>;
  loadProfileSessions: (profileId: string) => Promise<void>;
  triggerSession: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  profiles: [],
  selectedProfileId: null,
  systemHealth: null,
  rateLimits: [],
  loadingProfiles: true,
  sessions: [],
  selectedSessionId: undefined,
  
  activeTab: 'overview',
  darkMode: true,
  showConnectModal: false,
  showSettingsModal: false,
  mobileMenuOpen: false,
  isConsoleOpen: false,
  isCommandPaletteOpen: false,
  activityStream: [],

  setActiveTab: (tab) => set({ activeTab: tab, mobileMenuOpen: false }),
  setSelectedProfileId: (id) => {
    set({ selectedProfileId: id, selectedSessionId: undefined });
    if (id) {
      get().loadProfileSessions(id);
    }
  },
  setSelectedSessionId: (id) => set({ selectedSessionId: id }),
  setDarkMode: (mode) => {
    set({ darkMode: mode });
    if (typeof window !== 'undefined') {
      if (mode) document.documentElement.classList.add('dark');
      else document.documentElement.classList.remove('dark');
    }
  },
  setModals: ({ connect, settings, mobileMenu }) => set((state) => ({
    showConnectModal: connect ?? state.showConnectModal,
    showSettingsModal: settings ?? state.showSettingsModal,
    mobileMenuOpen: mobileMenu ?? state.mobileMenuOpen,
  })),
  setConsoleOpen: (isOpen) => set({ isConsoleOpen: isOpen }),
  setCommandPaletteOpen: (isOpen) => set({ isCommandPaletteOpen: isOpen }),
  appendActivityLog: (message, type = "info") => set((state) => {
    const newLog = { id: Math.random().toString(36).substring(2, 11), timestamp: Date.now(), message, type };
    return { activityStream: [newLog, ...state.activityStream].slice(0, 100) };
  }),

  loadInitialData: async () => {
    set({ loadingProfiles: true });
    try {
      const [profiles, health, limits] = await Promise.all([
        api.listProfiles(),
        api.getHealth().catch(() => null),
        api.getRateLimits().catch(() => [])
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
    try {
      await api.triggerSession(selectedProfileId);
      await get().loadProfileSessions(selectedProfileId);
    } catch (err) {
      console.error("Failed to trigger session", err);
    }
  }
}));
