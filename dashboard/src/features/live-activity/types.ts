export interface LiveEvent {
  id: string;
  session_id: string;
  event: string;
  timestamp: string;
  action_type?: string;
  action_id?: string;
  action_index?: number;
  status?: string;
  content?: string;
  target_url?: string;
  error?: string;
  message?: string;
  actions_count?: number;
  plan?: any;
  profile_slug?: string;
  completed?: number;
  failed?: number;
  reason?: string;
  reasoning?: string;
  priority?: number;
  duration_ms?: number;
}
