import { Profile } from "@/lib/api";

export interface PersonaMemoryTabProps {
  profileId: string;
  selectedProfile: Profile;
  onRefresh: () => void;
  activeSubTab?: string;
  onSubTabChange?: (subTab: string) => void;
}


export interface EntityStance {
  name: string;
  category: string;
  archetype: "loyalist" | "nemesis" | "nuanced_critic" | "guilty_pleasure" | "enthusiast" | "observer" | string;
  sentiment_split: {
    praise: number;
    analysis: number;
    critique: number;
    [key: string]: number;
  };
  talking_points: string[];
  behavioral_rule: string;
  is_active: boolean;
}

export interface LanguageConfig {
  primary_language: string;
  enable_hinglish: boolean;
  hinglish_mode: "mirror_only" | "mirror_and_punchline" | "full_bilingual" | string;
  slang_register: "urban_buff" | "casual_desi" | "minimal" | string;
  enable_hindi_script: boolean;
}

export interface ExpressivenessConfig {
  emoji_mode: "contextual_tone" | "minimal" | "none" | string;
  max_emojis: number;
  allow_zero_emojis: boolean;
  reply_meme_rate: number;
  thread_media_rate: number;
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
  stances?: EntityStance[];
  language_config?: LanguageConfig;
  expressiveness_config?: ExpressivenessConfig;
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
