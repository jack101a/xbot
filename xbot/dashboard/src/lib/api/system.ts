
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
};
