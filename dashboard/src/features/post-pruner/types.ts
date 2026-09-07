export interface PrunerCriteria {
  min_views: number;
  min_likes: number;
  min_comments: number;
  min_age_hours: number;
  max_posts_to_delete: number;
  match_mode: 'all' | 'any';
  dry_run?: boolean;
}

export interface DeletedPostItem {
  tweet_id: string;
  tweet_url: string;
  text: string;
  reason: string;
  metrics: {
    views: number;
    likes: number;
    comments: number;
    retweets?: number;
    age_hours?: number;
  };
}

export interface EvaluatedPostItem {
  tweet_id: string;
  tweet_url: string;
  text: string;
  status: string;
  reason: string;
  metrics: {
    views: number;
    likes: number;
    comments: number;
    retweets?: number;
    age_hours?: number;
  };
}

export interface PrunerRunResult {
  status: string;
  dry_run?: boolean;
  profile_id: string;
  username: string;
  scanned_count: number;
  deleted_count: number;
  candidate_count?: number;
  criteria: PrunerCriteria;
  deleted_posts: DeletedPostItem[];
  candidate_posts?: DeletedPostItem[];
  skipped_summary?: {
    too_recent?: number;
    pinned?: number;
    reply?: number;
    retweet?: number;
    passed_metrics?: number;
  };
  evaluated_posts?: EvaluatedPostItem[];
}

export interface PrunerHistoryItem {
  id: string;
  target_url: string;
  content: string;
  status: string;
  executed_at: string;
  result: any;
}

