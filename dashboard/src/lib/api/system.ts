
import { request } from './client';
import { SystemHealth, RateLimit, SystemConfig } from './types';

export const systemApi = {
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
  },
  getChatGPTStatus: () =>
    request<{
      status: string;
      has_cookie_file: boolean;
      cookie_count: number;
      has_valid_session_token: boolean;
      message: string;
    }>('/api/system/chatgpt/status'),
  importChatGPTCookies: (cookies: string) =>
    request<{
      status: string;
      cookie_count: number;
      has_valid_session_token: boolean;
      message: string;
    }>('/api/system/chatgpt/cookies', {
      method: 'POST',
      body: JSON.stringify({ cookies }),
    }),
  testChatGPTLiveSession: () =>
    request<{
      status: string;
      authenticated: boolean;
      latency_ms: number;
      user?: { email?: string; name?: string; image?: string; expires?: string };
      message: string;
    }>('/api/system/chatgpt/test', {
      method: 'POST',
    }),
  getAIPromptLogs: (params?: { limit?: number; offset?: number; provider?: string; q?: string }) => {
    const qp = new URLSearchParams();
    if (params?.limit) qp.set('limit', String(params.limit));
    if (params?.offset) qp.set('offset', String(params.offset));
    if (params?.provider) qp.set('provider', params.provider);
    if (params?.q) qp.set('q', params.q);
    const queryStr = qp.toString() ? `?${qp.toString()}` : '';
    return request<import('./types').AIPromptLogsResponse>(`/api/system/ai-logs${queryStr}`);
  },
  clearAIPromptLogs: () =>
    request<{ status: string; message: string }>('/api/system/ai-logs', {
      method: 'DELETE',
    }),
};
