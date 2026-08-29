import { Profile } from "@/lib/api";

export interface PersonaMemoryTabProps {
  profileId: string;
  selectedProfile: Profile;
  onRefresh: () => void;
}

export interface PersonaState {
  display_name?: string;
  identity?: {
    background?: string;
  };
  personality?: {
    communication_style?: string;
  };
  writing_style?: {
    tone?: string;
  };
  goals?: {
    short_term?: string[];
    content_pillars?: string[];
  };
  interests?: {
    primary?: string[];
    will_not_discuss?: string[];
  };
}

export interface LearnedState {
  reflection_count?: number;
  last_reflected_at?: string;
  characteristics?: {
    behavioral_adaptations?: string[];
  };
  interests?: {
    emerging_topics?: string[];
  };
}

export interface DiaryEntry {
  date: string;
  content: string;
}

export interface MsgState {
  type: "success" | "error";
  text: string;
}
