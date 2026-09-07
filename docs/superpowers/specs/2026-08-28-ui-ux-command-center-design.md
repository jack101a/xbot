# XBot Pro UI/UX Redesign: The Command Center

## 1. Overview
The XBot Pro dashboard is migrating from a flat, consumer-style UI with monolithic components to a high-density, IDE-style "Command Center" designed specifically for power-users. The core aesthetic removes "AI-glow" and glassmorphism in favor of tight padding, keyboard shortcuts, and parallel split-pane workflows.

**Critical Constraint:** All existing backend API endpoints, business logic, and previously built features MUST be strictly preserved. The `api.ts` file remains untouched.

## 2. Structural Architecture

### 2.1 The Global Shell
- **Left Rail (Navigation):** A persistent 48px vertical strip containing icon-only links to core tools (Dashboard, Studio, Growth, Persona).
- **Top Bar:** Minimal context bar showing the active X Profile, API health status, and a hint for the Command Palette.
- **Main Stage:** A flexible area that utilizes `react-resizable-panels` (or flex equivalents) to divide workspace into context and action areas.
- **Bottom Console:** A persistent terminal-like drawer at the bottom of the screen containing the "Live Activity" stream. This ensures the bot's real-time actions are always visible regardless of the active tab.

### 2.2 Feature Refactoring (Split-Pane Migration)
Monolithic files will be broken down and mapped into the IDE structure:
- **Overview Tab:** Grid layout. Quick Composer stays prominent; analytics become dense data tables; drafts are actionable list items.
- **Growth Engine:** Migrates to a master-detail split. Left pane lists the 6 sub-tools (F4F, Sniper, Hooks, etc.). Right pane renders the interface for the selected tool.
- **Campaign Studio:** Split screen. Left side for prompt configuration and deliverables selection. Right side for generated draft previews and publishing controls.

### 2.3 Mobile Graceful Degradation
To support the heavy IDE layout on mobile:
- **Responsive Stacking:** Split panes collapse into standard single-column scrollable views.
- **Drawer Overlays:** The persistent bottom "Console" becomes a swipe-up Bottom Sheet. The left navigation rail becomes a standard hamburger menu or a fixed bottom navigation bar (using the existing `MobileNavigation`).
- **Information Density:** Paddings increase slightly on touch devices (`p-4`) to maintain tap target sizes (min 44px for actions).

## 3. Keyboard-First Workflows
- **Global Command Palette (`cmd+k`):** A Spotlight/Raycast style modal that allows the user to:
  - Jump to specific profiles.
  - Jump to specific tools (e.g., "Go to F4F Sniper").
  - Trigger instant API actions (e.g., `api.triggerSession()`, `api.approveAllDrafts()`).
- **Hotkeys:** 
  - `cmd+1` through `cmd+5` for fast tab switching.
  - `cmd+\` to toggle the bottom console.

## 4. State Management
- **Zustand (`useAppStore`):** Expanded to hold UI layout states:
  - `isConsoleOpen: boolean`
  - `isCommandPaletteOpen: boolean`
  - `activityStream: any[]` (buffered from the backend so it survives component unmounts).
- **Props Removal:** Components deep in the tree will read directly from `useAppStore` rather than relying on prop-drilling from `page.tsx`.

## 5. Visual System (Design Tokens)
- **Colors:** Slate monochromatic scales. `bg-slate-950` for deep backgrounds, `bg-slate-900` for panels, `border-slate-800` for all dividers. Primary actions use standard flat `bg-blue-600`.
- **Typography:** Inter font family. High density (`text-xs` to `text-sm`), prioritizing tabular numbers for analytics.
- **Effects:** Zero gradients, zero blur filters, zero heavy drop-shadows. Flat, clean, technical.
