import { Profile } from "@/lib/api";

export interface CampaignStudioTabProps {
  selectedProfile: Profile | null;
}

export interface Deliverable {
  content_id: string;
  type: string;
  topic: string;
  text?: string;
  thread_tweets?: string[];
  question?: string;
  options?: string[];
  media_paths?: string[];
  extracted_link?: string;
  status?: string;
}

export interface CampaignPlan {
  campaign_title: string;
  theme: string;
  deliverables?: any[];
}

export interface CampaignStatus {
  status: string;
  progress_percent?: number;
  current_step?: string;
  plan?: CampaignPlan;
  deliverables?: Deliverable[];
  error?: string;
  duration_hours?: number;
  media_preference?: string;
}

export interface TrendRadarItem {
  title: string;
  summary?: string;
  url?: string;
  alignment_score: number;
  category?: string;
  recommended_angle?: string;
}

export interface ActiveCampaignSummary {
  id: string;
  topic: string;
  status: string;
  campaign_type: string;
  source_type: string;
  media_preference: string;
  duration_hours: number;
  interval_minutes: number;
  started_at: string | null;
  expires_at: string | null;
  seconds_remaining: number;
  hours_remaining: number;
  actions_executed_count: number;
  deliverables_count: number;
  next_run_at: string | null;
}
