// Client-side API wrapper for XBot backend API services

const DEFAULT_API_BASE_URL = typeof window !== 'undefined'
  ? (window.location.port === '8200' || !window.location.port ? '' : `${window.location.protocol}//${window.location.hostname}:8200`)
  : 'http://localhost:8200';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;

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
  LITELLM_PRIMARY_MODEL: string;
  LITELLM_FAST_MODEL: string;
  LITELLM_API_KEY?: string;
  MODEL_POST_CREATION: string;
  MODEL_REPLY_ANALYSIS: string;
  MODEL_TREND_ANALYSIS: string;
  MODEL_LIKE_RETWEET: string;
  MODEL_FOLLOW: string;
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
  triggerAutoreplyMentions: (id: string) => request<{ status: string; message: string }>(`/api/profiles/${id}/autoreply-mentions`, { method: 'POST' }),
  getProfileDiary: (id: string, limit = 15) => request<any[]>(`/api/profiles/${id}/diary?limit=${limit}`),
  getProfileMemories: (id: string, limit = 50) => request<any[]>(`/api/profiles/${id}/memories?limit=${limit}`),
  getProfileRelationships: (id: string) => request<any>(`/api/profiles/${id}/relationships`),
  getProfileStrategy: (id: string) => request<any>(`/api/profiles/${id}/strategy`),
  updateProfileStrategy: (id: string, strategy: any) => request<{ status: string; message: string; strategy: any }>(`/api/profiles/${id}/strategy`, { method: 'PUT', body: JSON.stringify(strategy) }),
  getProfileConfig: (id: string) => request<any>(`/api/profiles/${id}/config`),
  updateProfileConfig: (id: string, config: any) => request<{ status: string; message: string; config: any }>(`/api/profiles/${id}/config`, { method: 'PUT', body: JSON.stringify(config) }),

  // Sessions
  getSessionDetail: (id: string) => request<Session>(`/api/sessions/${id}`),
  getSessionActions: (id: string) => request<Action[]>(`/api/sessions/${id}/actions`),

  // Content
  getContentDetail: (id: string) => request<Content>(`/api/content/${id}`),
  updateContentStatus: (profileId: string, contentId: string, status: string) => request<any>(`/api/content/${contentId}/status`, { method: 'PUT', body: JSON.stringify({ status }) }),

  // System
  getHealth: () => request<SystemHealth>('/api/health'),
  getRateLimits: () => request<RateLimit[]>('/api/rate-limits'),
  pauseSystem: () => request<{ status: string; message: string }>('/api/system/pause', { method: 'POST' }),
  resumeSystem: () => request<{ status: string; message: string }>('/api/system/resume', { method: 'POST' }),
  getConfig: () => request<SystemConfig>('/api/system/config'),
  updateConfig: (config: Partial<SystemConfig>) => request<any>('/api/system/config', { method: 'PUT', body: JSON.stringify(config) }),
  
  // Tools
  getAdvancedMetrics: (username: string) => request<any>('/api/tools/analytics', {
    method: 'POST',
    body: JSON.stringify({ username })
  }),
  getSystemModels: (provider: string) => request<{ models: string[] }>(`/api/system/models?provider=${provider}`)
};
