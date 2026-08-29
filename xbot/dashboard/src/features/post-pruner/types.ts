export interface PrunerCriteria {
  min_views: number;
  min_likes: number;
  min_comments: number;
  min_age_hours: number;
  max_posts_to_delete: number;
  match_mode: 'all' | 'any';
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
  };
}

export interface PrunerHistoryItem {
  id: string;
  target_url: string;
  content: string;
  status: string;
  executed_at: string;
  result: any;
}
