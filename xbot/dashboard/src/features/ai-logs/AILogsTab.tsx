"use client";

import React, { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { AILogHeader } from "./components/AILogHeader";
import { AILogItem } from "./components/AILogItem";
import { AILogFilterState, AIPromptLogItem } from "./types";
import { BotMessageSquare, RefreshCw } from "lucide-react";

export function AILogsTab() {
  const [logs, setLogs] = useState<AIPromptLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<AILogFilterState>({
    searchQuery: "",
    providerFilter: "",
    autoRefresh: true,
  });

  const fetchLogs = useCallback(async () => {
    try {
      const res = await api.system.getAIPromptLogs({
        limit: 100,
        provider: filter.providerFilter || undefined,
        q: filter.searchQuery || undefined,
      });
      if (res && res.logs) {
        setLogs(res.logs);
      }
    } catch (e) {
      console.error("Failed to load AI prompt logs:", e);
    } finally {
      setLoading(false);
    }
  }, [filter.providerFilter, filter.searchQuery]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    if (!filter.autoRefresh) return;
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [filter.autoRefresh, fetchLogs]);

  const handleClear = async () => {
    if (!confirm("Clear all recorded AI conversation logs?")) return;
    try {
      await api.system.clearAIPromptLogs();
      setLogs([]);
    } catch (e) {
      console.error("Failed to clear logs:", e);
    }
  };

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-4">
      <AILogHeader
        filter={filter}
        setFilter={setFilter}
        totalCount={logs.length}
        loading={loading}
        onRefresh={fetchLogs}
        onClear={handleClear}
      />

      {loading && logs.length === 0 ? (
        <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center space-y-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
          <RefreshCw className="w-6 h-6 animate-spin text-purple-500" />
          <p className="text-sm font-medium">Loading AI conversation logs...</p>
        </div>
      ) : logs.length === 0 ? (
        <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center space-y-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
          <BotMessageSquare className="w-10 h-10 text-slate-400" />
          <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">No AI Prompt Logs Recorded Yet</h3>
          <p className="text-xs text-slate-500 max-w-md">
            As the bot generates posts, analyzes viral tweets, optimizes hooks, or answers user queries, every outbound prompt and response will appear here in real time.
          </p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {logs.map((log) => (
            <AILogItem key={log.id} log={log} />
          ))}
        </div>
      )}
    </div>
  );
}
