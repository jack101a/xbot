"use client";

import React, { useEffect, useState, useRef } from "react";
import { useAppStore } from "@/store/useAppStore";
import {
  Search,
  Terminal,
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
  User,
} from "lucide-react";

interface ActionItem {
  id: string;
  label: string;
  category: "Navigation" | "Workspaces" | "Actions";
  icon: React.ElementType;
  action: () => void;
}

export function CommandPalette() {
  const {
    isCommandPaletteOpen,
    setCommandPaletteOpen,
    setActiveTab,
    setConsoleOpen,
    isConsoleOpen,
    darkMode,
    setDarkMode,
    setModals,
    profiles,
    setSelectedProfileId,
  } = useAppStore();

  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isCommandPaletteOpen) {
      setSearch("");
      setSelectedIndex(0);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  }, [isCommandPaletteOpen]);

  if (!isCommandPaletteOpen) return null;

  const actions: ActionItem[] = [
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
    actions.push({
      id: `profile-${p.id}`,
      label: `Switch to workspace: ${p.display_name} (@${(p.x_handle || "").replace(/^@/, "")})`,
      category: "Workspaces",
      icon: User,
      action: () => setSelectedProfileId(p.id),
    });
  });

  const filtered = actions.filter((a) =>
    a.label.toLowerCase().includes(search.toLowerCase())
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      setCommandPaletteOpen(false);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (filtered.length > 0 ? (prev + 1) % filtered.length : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) =>
        filtered.length > 0 ? (prev - 1 + filtered.length) % filtered.length : 0
      );
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].action();
        setCommandPaletteOpen(false);
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4 sm:px-6">
      <div
        className="fixed inset-0 bg-slate-950/60 transition-opacity"
        onClick={() => setCommandPaletteOpen(false)}
      />
      <div
        className="relative w-full max-w-xl bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden z-10 flex flex-col max-h-[70vh] animate-in fade-in zoom-in-95 duration-100"
        onKeyDown={handleKeyDown}
      >
        <div className="flex items-center px-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
          <Search className="w-5 h-5 text-slate-400 shrink-0" />
          <input
            ref={inputRef}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="Type a command or search actions..."
            className="w-full bg-transparent border-0 focus:ring-0 text-sm px-3.5 py-4 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none"
          />
          <kbd className="hidden sm:inline-block text-[10px] uppercase font-mono font-medium px-2 py-1 rounded bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
            ESC
          </kbd>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filtered.map((action, i) => {
            const Icon = action.icon;
            const isSelected = i === selectedIndex;
            return (
              <button
                key={action.id}
                onClick={() => {
                  action.action();
                  setCommandPaletteOpen(false);
                }}
                onMouseEnter={() => setSelectedIndex(i)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm transition text-left ${
                  isSelected
                    ? "bg-blue-600 text-white font-medium shadow-sm"
                    : "text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60"
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Icon
                    className={`w-4 h-4 shrink-0 ${
                      isSelected
                        ? "text-white"
                        : "text-slate-400 dark:text-slate-500"
                    }`}
                  />
                  <span className="truncate">{action.label}</span>
                </div>
                <span
                  className={`text-[10px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded ml-2 shrink-0 ${
                    isSelected
                      ? "bg-blue-700 text-blue-100"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500"
                  }`}
                >
                  {action.category}
                </span>
              </button>
            );
          })}

          {filtered.length === 0 && (
            <div className="py-8 text-sm text-slate-400 dark:text-slate-500 text-center">
              No matching commands or actions
            </div>
          )}
        </div>

        <div className="px-4 py-2 bg-slate-50 dark:bg-slate-950/60 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="font-mono bg-slate-200 dark:bg-slate-800 px-1.5 py-0.5 rounded text-[10px]">↑↓</kbd> to navigate
            </span>
            <span>
              <kbd className="font-mono bg-slate-200 dark:bg-slate-800 px-1.5 py-0.5 rounded text-[10px]">↵</kbd> to select
            </span>
          </div>
          <span>
            <kbd className="font-mono bg-slate-200 dark:bg-slate-800 px-1.5 py-0.5 rounded text-[10px]">ESC</kbd> to close
          </span>
        </div>
      </div>
    </div>
  );
}
