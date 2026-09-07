
import { request } from './client';

export const campaignsApi = {
  generateCampaign: (data: {
    profile_id: string;
    prompt: string;
    duration_hours?: number;
    interval_minutes?: number;
    source_type?: 'on_demand' | 'trend_radar';
    media_preference?: 'x_official' | 'ai_generated';
  }) =>
    request<{ campaign_id: string; status: string; message: string; duration_hours?: number; media_preference?: string }>('/api/campaigns/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getLiveTrends: (profileId?: string, limit: number = 6) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (profileId) params.set('profile_id', profileId);
    return request<{
      status: string;
      trends: Array<{
        title: string;
        summary?: string;
        url?: string;
        alignment_score: number;
        category?: string;
        recommended_angle?: string;
      }>;
      profile_slug: string;
    }>(`/api/campaigns/trends/live?${params.toString()}`);
  },
  getActiveCampaigns: () =>
    request<Array<{
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
    }>>('/api/campaigns/active'),
  stopCampaign: (campaignId: string) =>
    request<{ status: string; message: string; campaign_id: string }>(`/api/campaigns/${campaignId}/stop`, {
      method: 'POST',
    }),
  getCampaignStatus: (campaignId: string) =>
    request<{
      campaign_id: string;
      status: 'initializing' | 'decomposing' | 'researching' | 'synthesizing' | 'ready' | 'failed';
      current_step: string;
      progress_percent: number;
      plan?: {
        campaign_title: string;
        theme: string;
        overall_strategy: string;
        deliverables: Array<{
          id: string;
          type: string;
          topic: string;
          search_query: string;
          target_media_count: number;
          instructions: string;
        }>;
      };
      deliverables: Array<{
        content_id: string;
        deliverable_id: string;
        type: 'thread' | 'poll' | 'visual' | 'post';
        topic: string;
        text?: string;
        thread_tweets?: string[];
        question?: string;
        options?: string[];
        duration_days?: number;
        media_paths?: string[];
        status: string;
        extracted_link?: string;
      }>;
      error?: string;
    }>(`/api/campaigns/${campaignId}/status`),
  publishCampaign: (campaignId: string, data: { content_ids: string[]; mode: 'instant' | 'schedule'; interval_minutes?: number }) =>
    request<{ status: string; campaign_id: string; mode: string; items_updated: number }>(`/api/campaigns/${campaignId}/publish`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  // Growth Engine Tools (AI Intelligence)
  generateSniperReply: (data: { profile_id?: string; profile_slug?: string; tweet_text: string; author?: string; angle?: string; likes?: number }) => 
    request<{ status: string; reply_text: string; angle_used: string; confidence: number; reasoning: string; profile_slug: string }>('/api/tools/sniper-reply', { method: 'POST', body: JSON.stringify(data) }),
  generateThread: (data: { profile_id?: string; profile_slug?: string; topic: string; num_tweets?: number; archetype?: string; deep_research?: boolean }) =>
    request<{
      topic: string;
      hook_score: number;
      archetype: string;
      tweets: string[];
      items: Array<{ position: number; item_type: string; text: string; media_url?: string }>;
      research_report?: any;
      downloaded_media?: Array<{
        local_path: string;
        source_url: string;
        caption: string;
        author_handle: string;
      }>;
    }>('/api/tools/generate-thread', { method: 'POST', body: JSON.stringify(data) }),
  researchTopic: (data: { profile_id?: string; profile_slug?: string; topic: string; max_tweets?: number }) =>
    request<{ status: string; report: any; profile_slug: string }>('/api/tools/research-topic', { method: 'POST', body: JSON.stringify(data) }),
  optimizeHooks: (data: { profile_id?: string; profile_slug?: string; draft_content: string; topic?: string }) => 
    request<{ status: string; candidates: Array<{ archetype: string; hook_text: string; score: number; reasoning: string }>; winning_hook: { archetype: string; hook_text: string; score: number; reasoning: string }; optimized_content: string; profile_slug: string }>('/api/tools/optimize-hook', { method: 'POST', body: JSON.stringify(data) }),
  generatePoll: (data: { profile_id?: string; profile_slug?: string; topic?: string }) => 
    request<{ status: string; question: string; options: string[]; duration_days: number; context_hook?: string; reasoning?: string; profile_slug: string }>('/api/tools/generate-poll', { method: 'POST', body: JSON.stringify(data) }),
  scanTrendRadar: (data: { profile_id?: string; profile_slug?: string; limit?: number; rss_urls?: string[] }) => 
    request<{ status: string; trends: Array<{ title: string; summary: string; url: string; alignment_score: number; category: string; recommended_angle: string }>; draft_posts: Array<{ trend_title: string; post_text: string; angle: string; rationale: string }>; profile_slug: string }>('/api/tools/trend-radar', { method: 'POST', body: JSON.stringify(data) }),
};
