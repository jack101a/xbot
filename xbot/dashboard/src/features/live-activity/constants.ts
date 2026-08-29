import React from "react";
import {
  Heart, MessageSquare, Repeat2, UserPlus, UserMinus, Users,
  Eye, Search, TrendingUp, BarChart2, PenLine, CheckCircle2,
  XCircle, Clock, Loader2, AlertTriangle, FileText, HelpCircle
} from "lucide-react";

export const ACTION_META: Record<string, {
  icon: React.ElementType;
  label: string;
  color: string;
  bg: string;
  border: string;
  verb: string;
}> = {
  post:                   { icon: PenLine,       label: "Post",         color: "text-violet-600 dark:text-violet-400", bg: "bg-violet-100 dark:bg-violet-950/50", border: "border-violet-200 dark:border-violet-800", verb: "Published post" },
  poll:                   { icon: HelpCircle,    label: "Poll",         color: "text-purple-600 dark:text-purple-400", bg: "bg-purple-100 dark:bg-purple-950/50", border: "border-purple-200 dark:border-purple-800", verb: "Published interactive poll" },
  reply:                  { icon: MessageSquare, label: "Reply",        color: "text-sky-600 dark:text-sky-400",       bg: "bg-sky-100 dark:bg-sky-950/50",       border: "border-sky-200 dark:border-sky-800",       verb: "Replied to" },
  like:                   { icon: Heart,         label: "Like",         color: "text-rose-500 dark:text-rose-400",     bg: "bg-rose-100 dark:bg-rose-950/50",     border: "border-rose-200 dark:border-rose-800",     verb: "Liked tweet" },
  retweet:                { icon: Repeat2,       label: "Retweet",      color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-100 dark:bg-emerald-950/50", border: "border-emerald-200 dark:border-emerald-800", verb: "Retweeted" },
  quote:                  { icon: FileText,      label: "Quote",        color: "text-amber-600 dark:text-amber-400",   bg: "bg-amber-100 dark:bg-amber-950/50",   border: "border-amber-200 dark:border-amber-800",   verb: "Quoted tweet" },
  follow:                 { icon: UserPlus,      label: "Follow",       color: "text-blue-600 dark:text-blue-400",     bg: "bg-blue-100 dark:bg-blue-950/50",     border: "border-blue-200 dark:border-blue-800",     verb: "Followed user" },
  unfollow:               { icon: UserMinus,     label: "Unfollow",     color: "text-gray-500 dark:text-gray-400",     bg: "bg-gray-100 dark:bg-gray-800",        border: "border-gray-200 dark:border-gray-700",     verb: "Unfollowed user" },
  browse:                 { icon: Eye,           label: "Browse",       color: "text-indigo-500 dark:text-indigo-400", bg: "bg-indigo-100 dark:bg-indigo-950/50", border: "border-indigo-200 dark:border-indigo-800", verb: "Browsed feed" },
  search:                 { icon: Search,        label: "Search",       color: "text-teal-600 dark:text-teal-400",     bg: "bg-teal-100 dark:bg-teal-950/50",     border: "border-teal-200 dark:border-teal-800",     verb: "Searched query" },
  scrape_trends:          { icon: TrendingUp,    label: "Trends",       color: "text-orange-500 dark:text-orange-400", bg: "bg-orange-100 dark:bg-orange-950/50", border: "border-orange-200 dark:border-orange-800", verb: "Scraped trends" },
  scrape_metrics:         { icon: BarChart2,     label: "Metrics",      color: "text-purple-600 dark:text-purple-400", bg: "bg-purple-100 dark:bg-purple-950/50", border: "border-purple-200 dark:border-purple-800", verb: "Scraped metrics" },
  unfollow_non_followers: { icon: UserMinus,     label: "Clean Ratio",  color: "text-rose-600 dark:text-rose-400",     bg: "bg-rose-100 dark:bg-rose-950/50",     border: "border-rose-200 dark:border-rose-800",     verb: "Cleaned non-followers" },
  follow_engagers:        { icon: Users,         label: "Target Follow",color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-100 dark:bg-emerald-950/50", border: "border-emerald-200 dark:border-emerald-800", verb: "Followed engagers" },
};

export const STATUS_META: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  pending:   { icon: Clock,        color: "text-gray-500 dark:text-gray-400", bg: "bg-gray-100 dark:bg-gray-800", label: "Pending" },
  executing: { icon: Loader2,      color: "text-blue-500 dark:text-blue-400", bg: "bg-blue-100 dark:bg-blue-950/60", label: "Running" },
  completed: { icon: CheckCircle2, color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-50 dark:bg-emerald-950/40", label: "Completed" },
  failed:    { icon: XCircle,      color: "text-rose-600 dark:text-rose-400", bg: "bg-rose-50 dark:bg-rose-950/40", label: "Failed" },
  skipped:   { icon: AlertTriangle,color: "text-amber-600 dark:text-amber-400", bg: "bg-amber-50 dark:bg-amber-950/40", label: "Skipped" },
};

export const TIME_RANGES = [
  { id: "3h",  label: "Last 3 Hours" },
  { id: "6h",  label: "Last 6 Hours" },
  { id: "12h", label: "Last 12 Hours" },
  { id: "24h", label: "Last 24 Hours" },
  { id: "3d",  label: "Last 3 Days" },
  { id: "7d",  label: "Last 7 Days" },
  { id: "all", label: "All Time" },
];
