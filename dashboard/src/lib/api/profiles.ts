
import { request, API_BASE_URL } from './client';
import { Profile, ProfileAuthStatus, Session, Content, AnalyticsSnapshot } from './types';

export const profilesApi = {
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
    const content = await profilesApi.getProfileContent(id);
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

  // Content & Draft Approvals
  getContentDetail: (id: string) => request<Content>(`/api/content/${id}`),
  updateContentStatus: (profileId: string, contentId: string, status: string) => request<any>(`/api/content/${contentId}/status`, { method: 'PUT', body: JSON.stringify({ status }) }),
  getDrafts: (profileId: string) => request<any[]>(`/api/profiles/${profileId}/drafts`),
  approveDraft: (profileId: string, contentId: string) => request<{ status: string; message: string }>(`/api/profiles/${profileId}/drafts/${contentId}/approve`, { method: 'POST', timeoutMs: 120000 }),
  approveAllDrafts: (profileId: string) => request<{ status: string; message: string; count: number }>(`/api/profiles/${profileId}/drafts/approve-all`, { method: 'POST', timeoutMs: 180000 }),
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

  // Post Pruner & Cleanup Studio
  runPostPruner: (
    profileId: string,
    criteria: {
      min_views: number;
      min_likes: number;
      min_comments: number;
      min_age_hours: number;
      max_posts_to_delete: number;
      match_mode: 'all' | 'any';
      dry_run?: boolean;
    }
  ) =>
    request<{
      status: string;
      dry_run?: boolean;
      profile_id: string;
      username: string;
      scanned_count: number;
      deleted_count: number;
      candidate_count?: number;
      criteria: any;
      deleted_posts: Array<{
        tweet_id: string;
        tweet_url: string;
        text: string;
        reason: string;
        metrics: { views: number; likes: number; comments: number; retweets?: number; age_hours?: number };
      }>;
      candidate_posts?: Array<{
        tweet_id: string;
        tweet_url: string;
        text: string;
        reason: string;
        metrics: { views: number; likes: number; comments: number; retweets?: number; age_hours?: number };
      }>;
      skipped_summary?: {
        too_recent?: number;
        pinned?: number;
        reply?: number;
        retweet?: number;
        passed_metrics?: number;
      };
      evaluated_posts?: Array<{
        tweet_id: string;
        tweet_url: string;
        text: string;
        status: string;
        reason: string;
        metrics: { views: number; likes: number; comments: number; retweets?: number; age_hours?: number };
      }>;
    }>(`/api/profiles/${profileId}/pruner/run`, {
      method: 'POST',
      body: JSON.stringify(criteria),
      timeoutMs: 300000,
    }),

  previewPostPruner: (
    profileId: string,
    criteria: {
      min_views: number;
      min_likes: number;
      min_comments: number;
      min_age_hours: number;
      max_posts_to_delete: number;
      match_mode: 'all' | 'any';
    }
  ) =>
    request<{
      status: string;
      dry_run: boolean;
      profile_id: string;
      username: string;
      scanned_count: number;
      deleted_count: number;
      candidate_count: number;
      criteria: any;
      deleted_posts: any[];
      candidate_posts: Array<{
        tweet_id: string;
        tweet_url: string;
        text: string;
        reason: string;
        metrics: { views: number; likes: number; comments: number; retweets?: number; age_hours?: number };
      }>;
      skipped_summary: {
        too_recent?: number;
        pinned?: number;
        reply?: number;
        retweet?: number;
        passed_metrics?: number;
      };
      evaluated_posts: Array<{
        tweet_id: string;
        tweet_url: string;
        text: string;
        status: string;
        reason: string;
        metrics: { views: number; likes: number; comments: number; retweets?: number; age_hours?: number };
      }>;
    }>(`/api/profiles/${profileId}/pruner/preview`, {
      method: 'POST',
      body: JSON.stringify(criteria),
      timeoutMs: 300000,
    }),

  deleteSpecificTweets: (
    profileId: string,
    tweetIds: string[]
  ) =>
    request<{
      status: string;
      profile_id: string;
      deleted_count: number;
      results: Array<{
        tweet_id: string;
        tweet_url: string;
        status: string;
        error?: string;
      }>;
    }>(`/api/profiles/${profileId}/pruner/delete-specific`, {
      method: 'POST',
      body: JSON.stringify({ tweet_ids: tweetIds }),
      timeoutMs: 180000,
    }),

  getPostPrunerHistory: (profileId: string, limit = 30) =>
    request<{
      profile_id: string;
      total_count: number;
      history: Array<{
        id: string;
        target_url: string;
        content: string;
        status: string;
        executed_at: string;
        result: any;
      }>;
    }>(`/api/profiles/${profileId}/pruner/history?limit=${limit}`),
};
