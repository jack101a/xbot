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
}
