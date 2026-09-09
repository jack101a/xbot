---
name: XBot Dashboard Slate-Indigo
description: Design specification and tokens for the XBot Pro dashboard and component system.
colors:
  background-light: "#f8fafc"
  background-dark: "#020617"
  surface-light: "#ffffff"
  surface-dark: "#0f172a"
  border-light: "#e2e8f0"
  border-dark: "#1e293b"
  primary: "#4f46e5"
  primary-hover: "#4338ca"
  accent-cyan: "#06b6d4"
  accent-emerald: "#10b981"
  accent-rose: "#f43f5e"
  accent-amber: "#f59e0b"
typography:
  font-sans: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
  font-heading: "Outfit, Inter, sans-serif"
---

# XBot Dashboard Design System

## Overview
A sleek, high-signal modern operations dashboard built on Tailwind CSS v4. Features high-density metric surfaces, dynamic dark/light theme tokens, and clean card modularity.

## Colors
- **Neutral Surface**: Slate palette (`#f8fafc` light, `#020617` dark)
- **Primary Brand**: Indigo (`#4f46e5`) for active states, CTA triggers, and primary tags
- **Alert / Danger**: Rose (`#f43f5e`) for taboos and forbidden anti-topics
- **Success**: Emerald (`#10b981`) for verified status and healthy states
- **Warning**: Amber (`#f59e0b`) for warnings and cautions

## Layout & Components
- **Card Containers**: `rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm`
- **Interactive Badges**: `rounded-full text-xs font-semibold px-3 py-1.5`
- **Form Controls**: `rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800`
