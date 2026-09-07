---
version: 1.0.0
name: XBot Pro Modern Design System
description: Clean, high-density telemetry and automation control system for XBot Pro.
colors:
  background-dark: "#0b0f19"
  background-card-dark: "#111827"
  border-dark: "#1f2937"
  text-primary-dark: "#f9fafb"
  text-secondary-dark: "#9ca3af"
  primary: "#0284c7"
  primary-hover: "#0369a1"
  success: "#10b981"
  warning: "#f59e0b"
  danger: "#ef4444"
typography:
  headline:
    fontFamily: Inter, sans-serif
    fontSize: 20px
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: Inter, sans-serif
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: 6px
  md: 10px
  lg: 16px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
---

# XBot Pro Design Specification

## Overview
XBot Pro is an autonomous social media intelligence and execution console. The visual language uses dark slate backdrops with sharp cyan/sky blue accents for focus, vibrant emerald for live/active states, and amber for timers/countdown indicators.

## Colors
- Primary Accent: Sky Blue (`#0284c7`)
- Success / Live Status: Emerald (`#10b981`)
- Expiration / Alert: Amber (`#f59e0b`)
- Background Surface: Deep Slate (`#0b0f19` / `#111827`)

## Components
- **InstantTrendCard**: High-contrast card with live pulsing emerald indicator, 48h countdown clock, and one-click red stop button.
- **TopicLauncherModal**: Intuitive modal with topic input, duration picker (12h/24h/48h), and quote-ratio indicator.
