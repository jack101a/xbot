// Client-side API wrapper for XBot backend API services

const DEFAULT_API_BASE_URL = typeof window !== 'undefined'
  ? (window.location.port === '8200' || !window.location.port ? '' : `${window.location.protocol}//${window.location.hostname}:8200`)
  : 'http://localhost:8200';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;

export function getWebSocketUrl(path: string): string {
  if (typeof window === 'undefined') {
    return `ws://localhost:8200${path.startsWith('/') ? path : '/' + path}`;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.port === '8200' || !window.location.port
    ? window.location.host
    : `${window.location.hostname}:8200`;
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${protocol}//${host}${cleanPath}`;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    clearTimeout(timeoutId);

    if (response.status === 204) {
      return {} as T;
    }

    if (!response.ok) {
      const errorBody = await response.text();
      let errorMessage = `API Error: ${response.status} ${response.statusText}`;
      try {
        const parsed = JSON.parse(errorBody);
        if (parsed.detail) {
          errorMessage = typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail);
        }
      } catch {
        if (errorBody) errorMessage = errorBody;
      }
      throw new Error(errorMessage);
    }

    return response.json() as Promise<T>;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err?.name === 'AbortError') {
      throw new Error(`Connection timed out fetching ${path}. Make sure backend on port 8200 is running and reachable.`);
    }
    if (err?.message && (err.message.includes('Failed to fetch') || err.message.includes('fetch failed'))) {
      throw new Error(`Failed to connect to backend at ${API_BASE_URL || window.location.origin}. Ensure the backend is running and port 8200 is accessible.`);
    }
    throw err;
  }
}

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

export const api = {
  // Profiles
  listProfiles: () => request<Profile[]>('/api/profiles'),
  createProfile: (profile: Partial<Profile>) => request<Profile>('/api/profiles', { method: 'POST', body: JSON.stringify(profile) }),
  getProfile: (id: string) => request<Profile>(`/api/profiles/${id}`),
  updateProfile: (id: string, profile: Partial<Profile>) => request<Profile>(`/api/profiles/${id}`, { method: 'PUT', body: JSON.stringify(profile) }),
  deleteProfile: (id: string) => request<void>(`/api/profiles/${id}`, { method: 'DELETE' }),
  pauseProfile: (id: string) => request<Profile>(`/api/profiles/${id}/pause`, { method: 'POST' }),
  resumeProfile: (id: string) => request<Profile>(`/api/profiles/${id}/resume`, { method: 'POST' }),
  triggerProfileSession: (id: string) => request<{ message: string; profile_id: string; task_id: string }>(`/api/profiles/${id}/trigger`, { method: 'POST' }),
  triggerSession: (id: string) => request<{ message: string; profile_id: string; task_id: string }>(`/api/profiles/${id}/trigger`, { method: 'POST' }),
  launchProfileLoginSession: (id: string) => request<{ status: string; message: string }>(`/api/profiles/${id}/login-session`, { method: 'POST' }),
  getProfileAuthStatus: (id: string) => request<ProfileAuthStatus>(`/api/profiles/${id}/auth-status`),
  importProfileCookies: (id: string, data: { auth_token?: string; ct0?: string; raw_cookies?: string; twid?: string }) => request<{ status: string; message: string; auth_status: ProfileAuthStatus }>(`/api/profiles/${id}/import-cookies`, { method: 'POST', body: JSON.stringify(data) }),
  syncProfileFromX: (id: string) => request<{ status: string; sync_data: any; profile: Profile }>(`/api/profiles/${id}/sync-from-x`, { method: 'POST' }),

  // 1-Click Live Browser Actions on Real X Session
  publishLivePost: (id: string, text: string, mediaPaths?: string[], gifQuery?: string) =>
    request<{ status: string; message: string; post_text: string }>(`/api/profiles/${id}/publish-post`, {
      method: 'POST',
      body: JSON.stringify({ text, media_paths: mediaPaths, gif_query: gifQuery }),
    }),
  uploadMedia: async (id: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE_URL}/api/profiles/${id}/upload-media`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<{ status: string; filename: string; file_path: string; size_bytes: number }>;
  },
  listMedia: (id: string) =>
    request<Array<{ filename: string; file_path: string; size_bytes: number; modified_at: string }>>(`/api/profiles/${id}/media`),
  publishLiveThread: (id: string, tweets: string[]) => request<{ status: string; message: string; total_tweets: number; root_tweet_id?: string }>(`/api/profiles/${id}/publish-thread`, { method: 'POST', body: JSON.stringify({ tweets }) }),
  publishLiveReply: (id: string, tweetUrl: string, replyText: string) => request<{ status: string; message: string; reply_text: string; target_tweet: string }>(`/api/profiles/${id}/publish-reply`, { method: 'POST', body: JSON.stringify({ tweet_url: tweetUrl, reply_text: replyText }) }),
  publishLivePoll: (id: string, question: string, options: string[], durationDays = 1) => request<{ status: string; message: string; question: string; options: string[] }>(`/api/profiles/${id}/publish-poll`, { method: 'POST', body: JSON.stringify({ question, options, duration_days: durationDays }) }),
  followUserLive: (id: string, username: string) => request<{ status: string; message: string; target_user: string }>(`/api/profiles/${id}/follow-user`, { method: 'POST', body: JSON.stringify({ username }) }),
  likeTweetLive: (id: string, tweetUrl: string) => request<{ status: string; message: string; target_tweet: string }>(`/api/profiles/${id}/like-tweet`, { method: 'POST', body: JSON.stringify({ tweet_url: tweetUrl }) }),

  // Profile Sub-resources
  getProfileSessions: (id: string, limit = 50) => request<Session[]>(`/api/profiles/${id}/sessions?limit=${limit}`),
  getProfileContent: (id: string, limit = 50) => request<Content[]>(`/api/profiles/${id}/content?limit=${limit}`),
  getContentQueue: async (id: string) => {
    const content = await api.getProfileContent(id);
    return content.filter(c => c.status === 'draft');
  },
  generateProfileContent: (id: string, prompt: string, maxChars = 280) => request<any>(`/api/profiles/${id}/generate`, { method: 'POST', body: JSON.stringify({ context_prompt: prompt, max_chars: maxChars }) }),
  getProfileAnalytics: (id: string, limit = 30) => request<AnalyticsSnapshot[]>(`/api/profiles/${id}/analytics?limit=${limit}`),
  getProfileMonetization: (id: string) => request<any>(`/api/profiles/${id}/monetization`),
  getProfilePersona: (id: string) => request<any>(`/api/profiles/${id}/persona`),
  getProfileLearnedState: (id: string) => request<any>(`/api/profiles/${id}/learned-state`),
  updateProfileLearnedState: (id: string, state: any) => request<{ status: string; message: string }>(`/api/profiles/${id}/learned-state`, { method: 'PUT', body: JSON.stringify(state) }),
  triggerProfileReflection: (id: string) => request<{ status: string; message: string }>(`/api/profiles/${id}/reflect`, { method: 'POST' }),
  updateProfilePersona: (id: string, persona: any) => request<{ status: string; message: string }>(`/api/profiles/${id}/persona`, { method: 'PUT', body: JSON.stringify(persona) }),
  importProfileCard: (id: string, content_or_path: string, use_ai: boolean = false) => request<{ status: string; message: string; persona: any }>(`/api/profiles/${id}/import-card`, { method: 'POST', body: JSON.stringify({ content_or_path, use_ai }) }),
  getProfileDiary: (id: string, limit = 15) => request<any[]>(`/api/profiles/${id}/diary?limit=${limit}`),
  getProfileMemories: (id: string, limit = 50) => request<any[]>(`/api/profiles/${id}/memories?limit=${limit}`),
  getProfileRelationships: (id: string) => request<any>(`/api/profiles/${id}/relationships`),
  getProfileStrategy: (id: string) => request<any>(`/api/profiles/${id}/strategy`),
  updateProfileStrategy: (id: string, strategy: any) => request<{ status: string; message: string; strategy: any }>(`/api/profiles/${id}/strategy`, { method: 'PUT', body: JSON.stringify(strategy) }),
  getProfileConfig: (id: string) => request<any>(`/api/profiles/${id}/config`),
  updateProfileConfig: (id: string, config: any) => request<{ status: string; message: string; config: any }>(`/api/profiles/${id}/config`, { method: 'PUT', body: JSON.stringify(config) }),

  // Activities Timeline & History
  getActivities: (id: string, params: ActivityParams = {}) => {
    const q = new URLSearchParams();
    if (params.time_range) q.set('time_range', params.time_range);
    if (params.action_type) q.set('action_type', params.action_type);
    if (params.status) q.set('status', params.status);
    if (params.search) q.set('search', params.search);
    if (params.limit) q.set('limit', String(params.limit));
    if (params.offset) q.set('offset', String(params.offset));
    return request<ActivityListResponse>(`/api/profiles/${id}/activities?${q.toString()}`);
  },

  // Sessions
  getSessionDetail: (id: string) => request<Session>(`/api/sessions/${id}`),
  getSessionActions: (id: string) => request<Action[]>(`/api/sessions/${id}/actions`),

  // Content & Draft Approvals
  getContentDetail: (id: string) => request<Content>(`/api/content/${id}`),
  updateContentStatus: (profileId: string, contentId: string, status: string) => request<any>(`/api/content/${contentId}/status`, { method: 'PUT', body: JSON.stringify({ status }) }),
  getDrafts: (profileId: string) => request<any[]>(`/api/profiles/${profileId}/drafts`),
  approveDraft: (profileId: string, contentId: string) => request<{ status: string; message: string }>(`/api/profiles/${profileId}/drafts/${contentId}/approve`, { method: 'POST' }),
  approveAllDrafts: (profileId: string) => request<{ status: string; message: string; count: number }>(`/api/profiles/${profileId}/drafts/approve-all`, { method: 'POST' }),
  dismissDraft: (profileId: string, contentId: string) => request<{ status: string; message: string }>(`/api/profiles/${profileId}/drafts/${contentId}`, { method: 'DELETE' }),
  dismissAllDrafts: (profileId: string) => request<{ status: string; message: string; discarded_count: number }>(`/api/profiles/${profileId}/drafts`, { method: 'DELETE' }),

  // Deep Analytics & Official Creator Studio Milestones
  getDeepAnalytics: (profileId: string) => request<any>(`/api/profiles/${profileId}/deep-analytics`),
  syncLiveAnalytics: (profileId: string) => request<any>(`/api/profiles/${profileId}/sync-analytics`, { method: 'POST' }),

  // Follow-for-Follow & 1,000 Blue Tick Growth Engine
  getF4FCandidates: (profileId: string, niche = 'all', blueTickOnly = true, limit = 25) =>
    request<any[]>(`/api/profiles/${profileId}/f4f/candidates?niche=${niche}&blue_tick_only=${blueTickOnly}&limit=${limit}`),
  scanF4F: (profileId: string, niche = 'all', limit = 20) =>
    request<{ status: string; message: string; count: number }>(`/api/profiles/${profileId}/f4f/scan?niche=${niche}&limit=${limit}`, { method: 'POST' }),
  followF4FCandidate: (profileId: string, targetHandle: string, isBlueTick = true, niche = 'ai') =>
    request<{ status: string; message: string; target_handle: string }>(`/api/profiles/${profileId}/f4f/follow`, {
      method: 'POST',
      body: JSON.stringify({ target_handle: targetHandle, is_blue_tick: isBlueTick, niche }),
    }),
  getF4FStats: (profileId: string) =>
    request<any>(`/api/profiles/${profileId}/f4f/stats`),
  getActiveGrowthPosts: (profileId: string, niche = 'all') =>
    request<any[]>(`/api/profiles/${profileId}/f4f/growth-posts?niche=${niche}`),
  batchFollowF4F: (profileId: string, count = 3) =>
    request<{ status: string; message: string; followed_handles?: string[]; followed_count?: number }>(`/api/profiles/${profileId}/f4f/batch-follow?count=${count}`, { method: 'POST' }),
  triggerGrowthCycle: (profileId: string) =>
    request<{ status: string; message: string; task_id: string }>(`/api/profiles/${profileId}/f4f/trigger-cycle`, { method: 'POST' }),


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


  // System & Models
  getHealth: () => request<SystemHealth>('/api/health'),
  getRateLimits: () => request<RateLimit[]>('/api/rate-limits'),
  pauseSystem: () => request<{ status: string; message: string }>('/api/system/pause', { method: 'POST' }),
  resumeSystem: () => request<{ status: string; message: string }>('/api/system/resume', { method: 'POST' }),
  getConfig: () => request<SystemConfig>('/api/system/config'),
  updateConfig: (config: Partial<SystemConfig>) => request<any>('/api/system/config', { method: 'PUT', body: JSON.stringify(config) }),
  getSystemModels: (provider = 'litellm', baseUrl?: string, apiKey?: string) => {
    let q = `/api/system/models?provider=${provider}`;
    if (baseUrl) q += `&base_url=${encodeURIComponent(baseUrl)}`;
    if (apiKey) q += `&api_key=${encodeURIComponent(apiKey)}`;
    return request<{ models: string[]; raw?: any[] }>(q);
  }
};
