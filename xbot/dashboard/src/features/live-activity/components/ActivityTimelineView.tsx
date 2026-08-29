import React, { useState, useEffect, useCallback } from "react";
import { Calendar, Search, RotateCcw, Loader2, Activity } from "lucide-react";
import { api, ActivityListResponse } from "@/lib/api";
import { TIME_RANGES } from "../constants";
import { ActivityCard } from "./ActivityCard";

export function ActivityTimelineView({ profileId }: { profileId: string }) {
  const [timeRange, setTimeRange] = useState("24h");
  const [actionType, setActionType] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [data, setData] = useState<ActivityListResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchActivities = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getActivities(profileId, {
        time_range: timeRange,
        action_type: actionType,
        status: statusFilter,
        search: searchQuery || undefined,
        limit: 50,
      });
      setData(res);
    } catch (e) {
      console.error("Failed to load activities", e);
    } finally {
      setLoading(false);
    }
  }, [profileId, timeRange, actionType, statusFilter, searchQuery]);

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities]);

  const counts = data?.summary_counts || {
    total: 0, completed: 0, skipped: 0, failed: 0,
    replies: 0, likes: 0, posts: 0, quotes: 0, follows: 0, unfollows: 0,
  };

  return (
    <div className="space-y-4">
      <div className="bg-panel/80 rounded-xl p-3 border border-app-border/[0.06] shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-app-text/70">
          <Calendar size={14} className="text-indigo-500" />
          <span>Rolling Time Filter:</span>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap w-full sm:w-auto">
          {TIME_RANGES.map(tr => (
            <button
              key={tr.id}
              onClick={() => setTimeRange(tr.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                timeRange === tr.id
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "bg-app text-app-text/60 hover:text-app-text hover:bg-app/80 border border-app-border/[0.05]"
              }`}
            >
              {tr.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-2.5">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
          {[
            { id: "all", label: "All Actions", count: counts.total },
            { id: "reply", label: "💬 Replies", count: counts.replies },
            { id: "like", label: "❤️ Likes", count: counts.likes },
            { id: "post", label: "✍️ Posts & Polls", count: counts.posts },
            { id: "quote", label: "💬 Quotes", count: counts.quotes },
            { id: "follow", label: "👥 Follows", count: counts.follows },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActionType(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                actionType === tab.id
                  ? "bg-panel text-app-text font-bold shadow-sm border border-app-border/[0.12]"
                  : "text-app-text/50 hover:text-app-text hover:bg-app/50"
              }`}
            >
              <span>{tab.label}</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                actionType === tab.id ? "bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 font-bold" : "bg-app text-app-text/40"
              }`}>
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="text-xs bg-panel border border-app-border/[0.08] rounded-lg px-2.5 py-1.5 text-app-text font-medium outline-none focus:border-indigo-500"
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed Only</option>
            <option value="skipped">Skipped Only</option>
            <option value="failed">Failed Only</option>
          </select>
          <div className="relative flex-1 sm:w-48">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-app-text/40" />
            <input
              type="text"
              placeholder="Search activity..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-7 pr-3 py-1.5 text-xs bg-panel border border-app-border/[0.08] rounded-lg text-app-text placeholder-app-text/30 outline-none focus:border-indigo-500"
            />
          </div>
          <button
            onClick={fetchActivities}
            className="p-1.5 rounded-lg border border-app-border/[0.08] text-app-text/50 hover:text-app-text hover:bg-app transition-all"
            title="Refresh Timeline"
          >
            <RotateCcw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12 text-app-text/40 gap-2">
          <Loader2 size={20} className="animate-spin text-indigo-500" />
          <span className="text-sm font-medium">Loading activity stream for {TIME_RANGES.find(t => t.id === timeRange)?.label}...</span>
        </div>
      )}

      {!loading && data && data.items.length === 0 && (
        <div className="text-center py-16 bg-panel/40 rounded-2xl border border-app-border/[0.06] space-y-2">
          <Activity size={40} className="mx-auto text-app-text/20" />
          <p className="text-sm font-semibold text-app-text/60">No actions found for {TIME_RANGES.find(t => t.id === timeRange)?.label}</p>
          <p className="text-xs text-app-text/40">Try switching to a longer time range (e.g. Last 24 Hours or 7 Days) or running a session.</p>
        </div>
      )}

      {!loading && data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map(item => (
            <ActivityCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
