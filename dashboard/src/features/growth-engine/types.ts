export interface TargetKOL {
  handle: string;
  category: string;
  priority: "high" | "medium" | "low";
  preferred_angle: "contrarian" | "framework" | "witty" | "data" | "insight";
}

export interface HookCandidate {
  archetype: string;
  hook_text: string;
  score: number;
  reasoning: string;
}

export type SubTabType = "f4f" | "sniper" | "hooks" | "threads" | "polls" | "trends";

export interface F4FStats {
  total_followed_all_time: number;
  blue_tick_ratio_pct: number;
  reciprocity_rate_pct: number;
  active_grace_period_count: number;
}
