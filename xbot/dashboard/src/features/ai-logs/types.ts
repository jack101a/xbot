import { AIPromptLogItem } from '@/lib/api';

export interface AILogFilterState {
  searchQuery: string;
  providerFilter: string;
  autoRefresh: boolean;
}

export type { AIPromptLogItem };
