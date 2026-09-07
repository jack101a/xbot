
import { Profile, Session, RateLimit } from "@/lib/api";

export interface OverviewTabProps {
  profile: Profile;
  sessions: Session[];
  rateLimits: RateLimit[];
  onRefresh: () => void;
  onNavigateToTab: (tab: "growth" | "activity" | "persona" | "limits") => void;
  onSelectSession?: (sessionId: string) => void;
}
