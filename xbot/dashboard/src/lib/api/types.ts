
export interface Profile {
  id: string;
  profile_slug: string;
  x_handle: string;
  display_name: string;
  status: 'active' | 'paused' | 'locked' | 'suspended';
  persona_summary: any;
  config: any;
  proxy_url_encrypted?: string;
  created_at: string;
  followers_count?: number;
  following_count?: number;
  posts_count?: number;
  impressions_24h?: number;
  engagements_24h?: number;
  engagement_rate?: number;
  likes_count?: number;
  retweets_count?: number;
  recent_tweets?: Array<{
    body: string;
    views: number;
    likes: number;
    retweets: number;
    replies: number;
  }>;
  avatar_url?: string;
  avatar?: string;
}

export interface ProfileAuthStatus {
  has_session_file: boolean;
  has_auth_token: boolean;
  has_ct0: boolean;
  is_configured: boolean;
  status: 'authenticated' | 'partial' | 'missing' | 'expired';
  cookie_count: number;
  updated_at: string | null;
  avatar_url?: string | null;
  followers_count?: number;
  following_count?: number;
}

export interface Session {
  id: string;
  profile_id: string;
  started_at: string;
  ended_at: string | null;
  status: 'running' | 'completed' | 'failed' | 'aborted';
  actions_planned: number;
  actions_completed: number;
  actions_failed: number;
  summary: any;
  plan?: any;
  error_log?: string | null;
}

export interface Action {
  id: string;
  session_id: string;
  profile_id: string;
  action_type: 'post' | 'reply' | 'like' | 'retweet' | 'quote' | 'follow' | 'browse' | 'search';
  target_url: string | null;
  content: string | null;
  status: 'pending' | 'executing' | 'completed' | 'failed' | 'skipped';
  duration_ms: number;
  executed_at: string | null;
  error: string | null;
}

export interface ActivityItem {
  id: string;
  action_type: string;
  status: string;
  target_url?: string | null;
  target_author?: string | null;
  target_tweet_id?: string | null;
  content?: string | null;
  result?: any;
  error?: string | null;
  duration_ms: number;
  executed_at?: string | null;
  time_ago: string;
  session_id?: string | null;
}

export interface ActivitySummaryCounts {
  total: number;
  completed: number;
  skipped: number;
  failed: number;
  replies: number;
  likes: number;
  posts: number;
  quotes: number;
  follows: number;
  unfollows: number;
}

export interface ActivityListResponse {
  items: ActivityItem[];
  total: number;
  limit: number;
  offset: number;
  time_range: string;
  summary_counts: ActivitySummaryCounts;
}

export interface ActivityParams {
  time_range?: string;
  action_type?: string;
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface Content {
  id: string;
  profile_id: string;
  content_type: string;
  body: string;
  status: 'draft' | 'posting' | 'posted' | 'failed';
  tweet_id: string | null;
  performance: any;
  posted_at: string | null;
  created_at: string;
}

export interface AnalyticsSnapshot {
  id: string;
  profile_id: string;
  snapshot_date: string;
  followers: number;
  following: number;
  total_tweets: number;
  impressions_24h: number;
  engagements_24h: number;
  engagement_rate: number;
  top_tweets: any;
  captured_at: string;
}

export interface RateLimit {
  id: string;
  profile_id: string;
  profile_slug: string;
  action_type: string;
  count_today: number;
  count_this_hour: number;
  window_start: string | null;
  last_action_at: string | null;
  cooldown_until: string | null;
}

export interface SystemHealth {
  status: 'healthy' | 'unhealthy';
  service: string;
  redis_connected: boolean;
  system_paused: boolean;
  database_url: string;
}

export interface SystemConfig {
  DATABASE_URL: string;
  REDIS_URL: string;
  LITELLM_BASE_URL: string;
  LITELLM_API_KEY?: string;
  LITELLM_PRIMARY_MODEL: string;
  LITELLM_FAST_MODEL: string;
  MODEL_POST_CREATION: string;
  MODEL_REPLY_ANALYSIS: string;
  MODEL_HOOK_OPTIMIZER?: string;
  MODEL_POLL_GENERATOR?: string;
  MODEL_TREND_ANALYSIS: string;
  MODEL_LIKE_RETWEET: string;
  MODEL_FOLLOW: string;
  MODEL_REFLECTION?: string;
  MODEL_PLANNER?: string;
  MISTRAL_API_KEY?: string;
  GEMINI_API_KEY?: string;
  DEEPSEEK_API_KEY?: string;
  OPENROUTER_API_KEY?: string;
  NVIDIA_API_KEY?: string;
  NVIDIA_BASE_URL?: string;
  NVIDIA_DEFAULT_IMAGE_MODEL?: string;
  CHATGPT_BRIDGE_ENABLED?: boolean;
  CHATGPT_BRIDGE_HEADLESS?: boolean;
  CHATGPT_BRIDGE_STATE_DIR?: string;
  IMAGE_GENERATION_PROVIDER?: string;
  API_PORT: number;
  PROMPT_POST_CREATION: string;
  PROMPT_REPLY_ANALYSIS: string;
  PROMPT_TREND_ANALYSIS: string;
  PROMPT_LIKE_RETWEET: string;
  PROMPT_FOLLOW: string;
  CONTEXT_POST_CREATION: string;
  CONTEXT_REPLY_ANALYSIS: string;
  CONTEXT_TREND_ANALYSIS: string;
  CONTEXT_LIKE_RETWEET: string;
  CONTEXT_FOLLOW: string;
}
