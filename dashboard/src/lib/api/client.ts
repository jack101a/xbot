
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

export interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

export async function request<T>(path: string, options?: RequestOptions): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const controller = new AbortController();
  const timeoutMs = options?.timeoutMs ?? 180000;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

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
