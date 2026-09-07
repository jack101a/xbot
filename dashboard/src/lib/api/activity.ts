
import { request } from './client';
import { ActivityParams, ActivityListResponse, Session, Action } from './types';

export const activityApi = {
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
  getSessionDetail: (id: string) => request<Session>(`/api/sessions/${id}`),
  getSessionActions: (id: string) => request<Action[]>(`/api/sessions/${id}/actions`),
};
