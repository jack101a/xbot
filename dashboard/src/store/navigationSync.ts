import { TabType } from './useAppStore';

export interface NavState {
  tab: TabType;
  subTab?: string;
  profileId?: string | null;
  sessionId?: string;
  modal?: "connect" | "settings" | "menu" | null;
}

const VALID_TABS: TabType[] = [
  "overview",
  "campaigns",
  "growth",
  "activity",
  "persona",
  "limits",
  "pruner",
  "ai-logs",
];

const DEFAULT_SUBTABS: Record<string, string> = {
  growth: "f4f",
  persona: "identity",
  activity: "timeline",
};

const STORAGE_KEYS = {
  activeTab: "xbot_active_tab",
  subTabPrefix: "xbot_subtab_",
  profileId: "xbot_selected_profile_id",
  sessionId: "xbot_selected_session_id",
};

/**
 * Parses the current URL search parameters or falls back to localStorage
 */
export function getInitialNavState(): NavState {
  if (typeof window === "undefined") {
    return { tab: "overview" };
  }

  try {
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get("tab") as TabType | null;
    const subTabParam = urlParams.get("subtab");
    const profileParam = urlParams.get("profile");
    const sessionParam = urlParams.get("session");
    const modalParam = urlParams.get("modal") as "connect" | "settings" | "menu" | null;

    // 1. If tab is in URL, trust URL first
    if (tabParam && VALID_TABS.includes(tabParam)) {
      const activeSubTab = subTabParam || DEFAULT_SUBTABS[tabParam];
      return {
        tab: tabParam,
        subTab: activeSubTab,
        profileId: profileParam || localStorage.getItem(STORAGE_KEYS.profileId) || null,
        sessionId: sessionParam || undefined,
        modal: modalParam || null,
      };
    }

    // 2. Fall back to localStorage if available
    const savedTab = localStorage.getItem(STORAGE_KEYS.activeTab) as TabType | null;
    if (savedTab && VALID_TABS.includes(savedTab)) {
      const savedSubTab = localStorage.getItem(STORAGE_KEYS.subTabPrefix + savedTab) || DEFAULT_SUBTABS[savedTab];
      const savedProfileId = localStorage.getItem(STORAGE_KEYS.profileId);
      const savedSessionId = localStorage.getItem(STORAGE_KEYS.sessionId);

      // Replace URL quietly so the address bar reflects the restored state
      syncUrlToBrowser(
        {
          tab: savedTab,
          subTab: savedSubTab,
          profileId: savedProfileId,
          sessionId: savedSessionId || undefined,
          modal: null,
        },
        false
      );

      return {
        tab: savedTab,
        subTab: savedSubTab,
        profileId: savedProfileId || null,
        sessionId: savedSessionId || undefined,
        modal: null,
      };
    }
  } catch (err) {
    console.warn("Failed to parse navigation state:", err);
  }

  return { tab: "overview", subTab: DEFAULT_SUBTABS.growth };
}

/**
 * Syncs the given navigation state to the browser's URL and localStorage
 */
export function syncUrlToBrowser(
  state: {
    tab?: TabType;
    subTab?: string;
    profileId?: string | null;
    sessionId?: string;
    modal?: "connect" | "settings" | "menu" | null;
  },
  pushHistory = true
) {
  if (typeof window === "undefined") return;

  try {
    const url = new URL(window.location.href);
    const currentParams = url.searchParams;

    if (state.tab) {
      currentParams.set("tab", state.tab);
      localStorage.setItem(STORAGE_KEYS.activeTab, state.tab);
    }

    if (state.subTab) {
      currentParams.set("subtab", state.subTab);
      if (state.tab) {
        localStorage.setItem(STORAGE_KEYS.subTabPrefix + state.tab, state.subTab);
      }
    } else if (state.tab && !currentParams.has("subtab")) {
      const defaultSub = DEFAULT_SUBTABS[state.tab];
      if (defaultSub) {
        currentParams.set("subtab", defaultSub);
      }
    }

    if (state.profileId !== undefined) {
      if (state.profileId) {
        currentParams.set("profile", state.profileId);
        localStorage.setItem(STORAGE_KEYS.profileId, state.profileId);
      } else {
        currentParams.delete("profile");
        localStorage.removeItem(STORAGE_KEYS.profileId);
      }
    }

    if (state.sessionId !== undefined) {
      if (state.sessionId) {
        currentParams.set("session", state.sessionId);
        localStorage.setItem(STORAGE_KEYS.sessionId, state.sessionId);
      } else {
        currentParams.delete("session");
        localStorage.removeItem(STORAGE_KEYS.sessionId);
      }
    }

    if (state.modal !== undefined) {
      if (state.modal) {
        currentParams.set("modal", state.modal);
      } else {
        currentParams.delete("modal");
      }
    }

    const newQuery = currentParams.toString();
    const newRelativePathQuery = window.location.pathname + (newQuery ? `?${newQuery}` : "") + window.location.hash;
    const currentRelativePathQuery = window.location.pathname + window.location.search + window.location.hash;

    if (currentRelativePathQuery !== newRelativePathQuery) {
      if (pushHistory) {
        window.history.pushState(
          {
            tab: state.tab,
            subTab: state.subTab,
            profileId: state.profileId,
            sessionId: state.sessionId,
            modal: state.modal,
          },
          "",
          newRelativePathQuery
        );
      } else {
        window.history.replaceState(
          {
            tab: state.tab,
            subTab: state.subTab,
            profileId: state.profileId,
            sessionId: state.sessionId,
            modal: state.modal,
          },
          "",
          newRelativePathQuery
        );
      }
    }
  } catch (err) {
    console.warn("Failed to sync navigation URL:", err);
  }
}

/**
 * Initializes a listener for popstate (browser back/forward button clicks & mobile swipe gestures)
 */
export function initPopStateListener(onNavigate: (state: NavState) => void): () => void {
  if (typeof window === "undefined") return () => {};

  const handlePopState = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get("tab") as TabType | null;
    const subTabParam = urlParams.get("subtab");
    const profileParam = urlParams.get("profile");
    const sessionParam = urlParams.get("session");
    const modalParam = urlParams.get("modal") as "connect" | "settings" | "menu" | null;

    const tab = tabParam && VALID_TABS.includes(tabParam) ? tabParam : "overview";
    const subTab = subTabParam || DEFAULT_SUBTABS[tab] || undefined;

    onNavigate({
      tab,
      subTab,
      profileId: profileParam || null,
      sessionId: sessionParam || undefined,
      modal: modalParam || null,
    });
  };

  window.addEventListener("popstate", handlePopState);
  return () => {
    window.removeEventListener("popstate", handlePopState);
  };
}
