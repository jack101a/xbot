# UI/UX Command Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the XBot Pro dashboard into a high-density, IDE-style "Command Center" with split panes, persistent bottom console, and a global command palette.

**Architecture:** We will extend the existing Zustand store for the new UI states, build the Command Palette and Bottom Console components, inject them into the root layout (`page.tsx`), and refactor the 3 massive feature tabs (`Overview`, `GrowthEngine`, `CampaignStudio`) into split-pane architectures.

**Tech Stack:** React, Next.js, Zustand, Tailwind CSS v4, Lucide React.

**Spec:** docs/superpowers/specs/2026-08-28-ui-ux-command-center-design.md

## Global Constraints

- Strict preservation of `api.ts` and all existing backend interactions.
- Zero glassmorphism (`backdrop-blur`).
- Use slate monochromatic scale (`bg-slate-950`, `bg-slate-900`, `border-slate-800`).
- High density typography (`text-xs` to `text-sm`).

---

### Task 1: Extend State Management

**Files:**
- Modify: `dashboard/src/store/useAppStore.ts`

**Interfaces:**
- Produces: `isConsoleOpen`, `isCommandPaletteOpen`, `activityStream` in `AppState`.
- Produces: `setConsoleOpen`, `setCommandPaletteOpen`, `appendActivityLog` actions.

- [ ] **Step 1: Add state definitions**
Add the new boolean flags and activity stream array to `AppState` interface, along with their setter actions.

```typescript
  isConsoleOpen: boolean;
  isCommandPaletteOpen: boolean;
  activityStream: { id: string; timestamp: number; message: string; type: "info" | "success" | "error" }[];
  
  setConsoleOpen: (isOpen: boolean) => void;
  setCommandPaletteOpen: (isOpen: boolean) => void;
  appendActivityLog: (message: string, type?: "info" | "success" | "error") => void;
```

- [ ] **Step 2: Implement actions in create store**
Initialize them in the store creation and implement the setters. For `appendActivityLog`, push to the array and cap at 100 items.

```typescript
  isConsoleOpen: false,
  isCommandPaletteOpen: false,
  activityStream: [],

  setConsoleOpen: (isOpen) => set({ isConsoleOpen: isOpen }),
  setCommandPaletteOpen: (isOpen) => set({ isCommandPaletteOpen: isOpen }),
  appendActivityLog: (message, type = "info") => set((state) => {
    const newLog = { id: Math.random().toString(36).substr(2, 9), timestamp: Date.now(), message, type };
    return { activityStream: [newLog, ...state.activityStream].slice(0, 100) };
  }),
```

- [ ] **Step 3: Test compilation**
Run `npm run build` in `dashboard/` to ensure TypeScript is satisfied.

### Task 2: Build Bottom Console

**Files:**
- Create: `dashboard/src/components/layout/BottomConsole.tsx`

**Interfaces:**
- Consumes: `useAppStore` (`isConsoleOpen`, `setConsoleOpen`, `activityStream`)

- [ ] **Step 1: Create BottomConsole component**
Create a new file `dashboard/src/components/layout/BottomConsole.tsx`. It should read from `useAppStore`. If `!isConsoleOpen`, return null (or a collapsed handle). If open, display a fixed bottom panel (`fixed bottom-0 left-0 right-0 h-48 bg-slate-950 border-t border-slate-800 z-40`).

```tsx
"use client";

import React from "react";
import { useAppStore } from "@/store/useAppStore";
import { X, Terminal } from "lucide-react";

export function BottomConsole() {
  const { isConsoleOpen, setConsoleOpen, activityStream } = useAppStore();

  if (!isConsoleOpen) return null;

  return (
    <div className="fixed bottom-0 left-0 lg:left-72 right-0 h-48 bg-slate-950 border-t border-slate-800 z-40 flex flex-col shadow-2xl">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-900">
        <div className="flex items-center gap-2 text-slate-300">
          <Terminal className="w-4 h-4" />
          <span className="text-xs font-mono font-semibold uppercase tracking-wider">Live Activity Console</span>
        </div>
        <button onClick={() => setConsoleOpen(false)} className="text-slate-500 hover:text-slate-300">
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 font-mono text-[10px] sm:text-xs space-y-1">
        {activityStream.length === 0 ? (
          <div className="text-slate-600 italic px-2">No recent activity...</div>
        ) : (
          activityStream.map((log) => (
            <div key={log.id} className={`px-2 py-1 flex items-start gap-3 rounded ${
              log.type === 'error' ? 'text-red-400 bg-red-950/30' : 
              log.type === 'success' ? 'text-emerald-400 bg-emerald-950/30' : 
              'text-slate-300 hover:bg-slate-900'
            }`}>
              <span className="text-slate-600 shrink-0">{new Date(log.timestamp).toLocaleTimeString()}</span>
              <span className="break-all">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add trigger in DesktopSidebar**
Modify `dashboard/src/components/layout/DesktopSidebar.tsx` to add a button in the bottom section to toggle the console.

```tsx
// Find the bottom settings div and add a Terminal button next to Settings
          <button
            onClick={() => setConsoleOpen(!isConsoleOpen)}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 transition border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Console</span>
          </button>
```
Remember to add `Terminal` to the `lucide-react` imports and `isConsoleOpen, setConsoleOpen` to `useAppStore` destructuring.

### Task 3: Build Command Palette & Global Shortcuts

**Files:**
- Create: `dashboard/src/components/layout/CommandPalette.tsx`
- Modify: `dashboard/src/app/page.tsx`

**Interfaces:**
- Consumes: `useAppStore`

- [ ] **Step 1: Create CommandPalette component**
A modal centered on screen with an input field and a list of actions (Navigate to Dashboard, Studio, Growth, Toggle Dark Mode, Run Session).

```tsx
"use client";

import React, { useEffect, useState } from "react";
import { useAppStore } from "@/store/useAppStore";
import { Search, Terminal } from "lucide-react";

export function CommandPalette() {
  const { isCommandPaletteOpen, setCommandPaletteOpen, setActiveTab, setConsoleOpen, profiles, setSelectedProfileId } = useAppStore();
  const [search, setSearch] = useState("");

  if (!isCommandPaletteOpen) return null;

  const actions = [
    { label: "Go to Dashboard", action: () => setActiveTab("overview") },
    { label: "Go to Studio", action: () => setActiveTab("campaigns") },
    { label: "Go to Growth Engine", action: () => setActiveTab("growth") },
    { label: "Toggle Console", action: () => setConsoleOpen(true) }
  ];
  
  profiles.forEach(p => {
    actions.push({ label: `Switch to profile: ${p.display_name}`, action: () => setSelectedProfileId(p.id) });
  });

  const filtered = actions.filter(a => a.label.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm" onClick={() => setCommandPaletteOpen(false)} />
      <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        <div className="flex items-center px-4 border-b border-slate-200 dark:border-slate-800">
          <Search className="w-5 h-5 text-slate-400" />
          <input
            autoFocus
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Type a command or search..."
            className="w-full bg-transparent border-0 focus:ring-0 text-sm px-4 py-4 text-slate-900 dark:text-slate-100 placeholder-slate-400"
          />
        </div>
        <div className="max-h-[60vh] overflow-y-auto p-2">
          {filtered.map((action, i) => (
            <button
              key={i}
              onClick={() => { action.action(); setCommandPaletteOpen(false); }}
              className="w-full text-left px-4 py-2.5 rounded-lg text-sm text-slate-700 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-600 dark:hover:text-blue-400 transition"
            >
              {action.label}
            </button>
          ))}
          {filtered.length === 0 && <div className="p-4 text-sm text-slate-500 text-center">No results found</div>}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add keyboard listeners and mount components in page.tsx**
In `dashboard/src/app/page.tsx`, add a `useEffect` to listen for `cmd+k` (or `ctrl+k`) to toggle palette, and `cmd+\` (or `ctrl+\`) to toggle console.
Import and render `<BottomConsole />` and `<CommandPalette />` before the closing `</div>`.

```tsx
// Inside DashboardPage component
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setModals({ settings: false, connect: false }); // close others
        useAppStore.getState().setCommandPaletteOpen(!useAppStore.getState().isCommandPaletteOpen);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === '\\') {
        e.preventDefault();
        useAppStore.getState().setConsoleOpen(!useAppStore.getState().isConsoleOpen);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
```

### Task 4: Refactor Growth Engine (Split-Pane)

**Files:**
- Modify: `dashboard/src/features/growth-engine/GrowthEngineTab.tsx`

**Interfaces:**
- Remains isolated within the component.

- [ ] **Step 1: Rewrite layout shell**
Currently, `GrowthEngineTab` uses a horizontal scrolling top-nav for its subTabs (`f4f`, `sniper`, `hooks`, etc.). We will change the outer shell to a split view: `flex flex-col lg:flex-row gap-4 h-[calc(100vh-120px)]`.
The left pane is a fixed-width list (`w-full lg:w-64 flex-shrink-0`), and the right pane is the active content (`flex-1 overflow-y-auto`).

- [ ] **Step 2: Move subTabs to vertical sidebar**
Convert the horizontal scroll buttons into a vertical list.

```tsx
// Replace the top navigation container with:
<div className="flex flex-col lg:flex-row gap-4 lg:h-[calc(100vh-120px)] items-start">
  {/* Left Nav Pane */}
  <div className="w-full lg:w-64 flex-shrink-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-2 flex lg:flex-col gap-1 overflow-x-auto lg:overflow-visible">
    {/* map subTabs here using vertical flex classes on large screens */}
  </div>
  
  {/* Right Content Pane */}
  <div className="flex-1 w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 lg:p-6 overflow-y-auto h-full">
    {/* existing switch cases for active subTab content */}
  </div>
</div>
```

- [ ] **Step 3: Check build**
Run `npm run build` to ensure no syntax errors.

### Task 5: Refactor Campaign Studio (Split-Pane)

**Files:**
- Modify: `dashboard/src/features/campaign-studio/CampaignStudioTab.tsx`

**Interfaces:**
- Remains isolated.

- [ ] **Step 1: Rewrite layout shell**
Convert CampaignStudio to a master-detail split. Left pane: Prompt input, quick templates, settings. Right pane: The generated campaign outline/status and publishing controls.

```tsx
// Inside CampaignStudioTab return:
<div className="flex flex-col lg:flex-row gap-4 lg:h-[calc(100vh-120px)] items-start">
  {/* Left Pane (Configuration) */}
  <div className="w-full lg:w-[400px] flex-shrink-0 flex flex-col gap-4 overflow-y-auto h-full pr-1">
    {/* Prompt textarea and quick templates go here */}
  </div>

  {/* Right Pane (Results & Publishing) */}
  <div className="flex-1 w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 overflow-y-auto h-full">
    {/* Campaign status, select deliverables, and publish mode go here */}
  </div>
</div>
```

- [ ] **Step 2: Check build**
Ensure it compiles cleanly.

### Task 6: Refactor Overview Tab (Grid Density)

**Files:**
- Modify: `dashboard/src/features/overview/OverviewTab.tsx`

**Interfaces:**
- Remains isolated.

- [ ] **Step 1: Increase Grid Density**
Currently, things are stacked vertically with `space-y-6`. Convert to a CSS Grid where Quick Composer and Profile Hero sit at the top, and Drafts sit alongside stats.

```tsx
<div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">
  {/* Top Row: Hero spans 2, Quick Composer spans 1 */}
  <div className="lg:col-span-2">
    {/* Hero Profile Card */}
  </div>
  <div className="lg:col-span-1">
    {/* Quick Live Composer */}
  </div>

  {/* Middle Row: Pending Drafts spans 3 if they exist, or just 2 with Analytics next to it */}
  <div className="lg:col-span-3">
    {/* Pending Drafts */}
  </div>
  
  {/* Bottom Row: Analytics */}
</div>
```
Ensure all cards use standard `p-4` (removed `sm:p-6` large padding for higher density).

- [ ] **Step 2: Final Compilation Check**
Run `npm run build` to verify the entire plan was implemented successfully without breaking existing code.
