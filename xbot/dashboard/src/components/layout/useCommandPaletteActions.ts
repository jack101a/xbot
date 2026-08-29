"use client";

import { useMemo } from "react";
import { useAppStore } from "@/store/useAppStore";
import {
  LayoutDashboard,
  Sparkles,
  Zap,
  Activity,
  Brain,
  Sliders,
  Sun,
  Moon,
  Settings,
  Plus,
  Terminal,
  User,
} from "lucide-react";

export interface CommandPaletteAction {
  id: string;
  label: string;
  category: "Navigation" | "Workspaces" | "Actions";
  icon: React.ElementType;
  action: () => void;
}

export function useCommandPaletteActions() {
  const {
    setActiveTab,
    setConsoleOpen,
    isConsoleOpen,
    darkMode,
    setDarkMode,
    setModals,
    profiles,
    setSelectedProfileId,
  } = useAppStore();

  const actions: CommandPaletteAction[] = useMemo(() => {
    const list: CommandPaletteAction[] = [
      {
        id: "nav-overview",
        label: "Go to Dashboard",
        category: "Navigation",
        icon: LayoutDashboard,
        action: () => setActiveTab("overview"),
      },
      {
        id: "nav-campaigns",
        label: "Go to Content Studio",
        category: "Navigation",
        icon: Sparkles,
        action: () => setActiveTab("campaigns"),
      },
      {
        id: "nav-growth",
        label: "Go to Growth Engine",
        category: "Navigation",
        icon: Zap,
        action: () => setActiveTab("growth"),
      },
      {
        id: "nav-activity",
        label: "Go to Live Activity",
        category: "Navigation",
        icon: Activity,
        action: () => setActiveTab("activity"),
      },
      {
        id: "nav-persona",
        label: "Go to Persona & Knowledge",
        category: "Navigation",
        icon: Brain,
        action: () => setActiveTab("persona"),
      },
      {
        id: "nav-limits",
        label: "Go to System & Safety",
        category: "Navigation",
        icon: Sliders,
        action: () => setActiveTab("limits"),
      },
      {
        id: "action-console",
        label: isConsoleOpen ? "Close Activity Console" : "Open Activity Console",
        category: "Actions",
        icon: Terminal,
        action: () => setConsoleOpen(!isConsoleOpen),
      },
      {
        id: "action-theme",
        label: darkMode ? "Switch to Light Mode" : "Switch to Dark Mode",
        category: "Actions",
        icon: darkMode ? Sun : Moon,
        action: () => setDarkMode(!darkMode),
      },
      {
        id: "action-settings",
        label: "Open Settings",
        category: "Actions",
        icon: Settings,
        action: () => setModals({ settings: true }),
      },
      {
        id: "action-connect",
        label: "Connect New Account",
        category: "Actions",
        icon: Plus,
        action: () => setModals({ connect: true }),
      },
    ];

    profiles.forEach((p) => {
      list.push({
        id: `profile-${p.id}`,
        label: `Switch to workspace: ${p.display_name} (@${(p.x_handle || "").replace(/^@/, "")})`,
        category: "Workspaces",
        icon: User,
        action: () => setSelectedProfileId(p.id),
      });
    });

    return list;
  }, [
    setActiveTab,
    isConsoleOpen,
    setConsoleOpen,
    darkMode,
    setDarkMode,
    setModals,
    profiles,
    setSelectedProfileId,
  ]);

  return { actions };
}
