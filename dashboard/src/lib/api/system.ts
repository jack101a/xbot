
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
      online?: boolean;
      authenticated?: boolean;
      bridge_url?: string;
      latency_ms?: number;
      plan_type?: string;
      left_percent?: number;
      used_percent?: number;
      reset_at_str?: string;
      email?: string;
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
  testChatGPTLiveSession: (bridgeUrl?: string) =>
    request<{
      status: string;
      authenticated: boolean;
      bridge_url?: string;
      latency_ms: number;
      user?: { email?: string; plan?: string; left_percent?: number };
      quota?: any;
      message: string;
    }>('/api/system/chatgpt/test', {
      method: 'POST',
      body: JSON.stringify(bridgeUrl ? { bridge_url: bridgeUrl } : {}),
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
