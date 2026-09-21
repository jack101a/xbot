"use client";

import React, { useState, useEffect } from "react";
import {
  Sparkles,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Play,
  Save,
  ExternalLink,
  Server,
} from "lucide-react";
import { api } from "@/lib/api";
import { SystemConfig } from "@/lib/api/types";

interface ChatGPTBridgeCardProps {
  config?: Partial<SystemConfig>;
  setConfig?: (c: Partial<SystemConfig>) => void;
}

export function ChatGPTBridgeCard({ config, setConfig }: ChatGPTBridgeCardProps) {
  const [bridgeUrl, setBridgeUrl] = useState<string>("http://192.168.0.200:8465");
  const [status, setStatus] = useState<{
    status: string;
    online?: boolean;
    authenticated?: boolean;
    bridge_url?: string;
    latency_ms?: number;
    plan_type?: string;
    left_percent?: number;
    email?: string;
    message: string;
  } | null>(null);

  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [resultMsg, setResultMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await api.getChatGPTStatus();
      setStatus(res);
      if (res?.bridge_url) {
        setBridgeUrl(res.bridge_url);
      }
    } catch (e: any) {
      setStatus({
        status: "offline",
        online: false,
        authenticated: false,
        message: e?.message || "Could not check ChatGPT bridge status",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (config?.CHATGPT_BRIDGE_URL) {
      setBridgeUrl(config.CHATGPT_BRIDGE_URL);
    }
  }, [config?.CHATGPT_BRIDGE_URL]);

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleTestSession = async () => {
    if (!bridgeUrl.trim()) return;
    setTesting(true);
    setResultMsg(null);
    try {
      const res = await api.testChatGPTLiveSession(bridgeUrl.trim());
      if (res.authenticated) {
        setResultMsg({
          type: "success",
          text: `Verified! Connected to ${res.bridge_url || bridgeUrl} (${res.latency_ms}ms) · Account: ${res.user?.email || "Authenticated"} · Plan: ${(res.user?.plan || "Standard").toUpperCase()}`,
        });
        await fetchStatus();
      } else {
        setResultMsg({
          type: "error",
          text: res.message || "Connection test failed. Verify bridge URL and port.",
        });
      }
    } catch (err: any) {
      setResultMsg({
        type: "error",
        text: err?.message || "Error communicating with ChatGPT bridge",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSaveEndpoint = async () => {
    const trimmed = bridgeUrl.trim();
    if (!trimmed) return;
    setSaving(true);
    setResultMsg(null);
    try {
      await api.updateConfig({ CHATGPT_BRIDGE_URL: trimmed });
      if (setConfig && config) {
        setConfig({ ...config, CHATGPT_BRIDGE_URL: trimmed });
      }
      setResultMsg({
        type: "success",
        text: `Endpoint updated to ${trimmed} and saved to .env!`,
      });
      await fetchStatus();
    } catch (err: any) {
      setResultMsg({
        type: "error",
        text: err?.message || "Failed to update ChatGPT bridge URL",
      });
    } finally {
      setSaving(false);
    }
  };

  const isOnline = status?.online !== false && status?.status !== "offline";
  const isAuthed = status?.authenticated || status?.status === "authenticated";

  return (
    <div className="p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/70 shadow-sm space-y-3 mt-3">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white">
              ChatGPT Web Bridge (Remote Container)
            </h4>
            <p className="text-[10px] text-slate-500 dark:text-slate-400">
              Zero API cost · Offloaded Chromium · Isolated execution
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
          {/* Status Badge */}
          <span
            className={`inline-flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${
              isOnline && isAuthed
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                : isOnline
                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20"
                : "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20"
            }`}
          >
            {isOnline && isAuthed ? (
              <CheckCircle2 className="w-3 h-3" />
            ) : (
              <AlertCircle className="w-3 h-3" />
            )}
            {isOnline && isAuthed
              ? `Connected (${status?.latency_ms ? `${status.latency_ms}ms` : "Active"})`
              : isOnline
              ? "Bridge Reachable"
              : "Bridge Offline"}
          </span>

          <button
            type="button"
            onClick={fetchStatus}
            disabled={loading}
            className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition"
            title="Refresh Bridge Status"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* URL Config & Action Bar */}
      <div className="space-y-1.5 pt-1">
        <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300">
          Bridge Endpoint URL (Local LAN, Custom Port, or Remote VPS)
        </label>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-slate-400">
              <Server className="w-3.5 h-3.5" />
            </div>
            <input
              type="text"
              value={bridgeUrl}
              onChange={(e) => setBridgeUrl(e.target.value)}
              placeholder="http://192.168.0.200:8465"
              className="w-full pl-8 pr-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 font-mono text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={handleTestSession}
              disabled={testing || !bridgeUrl.trim()}
              className="px-3 py-1.5 text-xs font-semibold rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
              title="Test connection and verify quota"
            >
              <Play className={`w-3.5 h-3.5 ${testing ? "animate-spin" : ""}`} />
              <span>{testing ? "Testing..." : "Test Connection"}</span>
            </button>

            <button
              type="button"
              onClick={handleSaveEndpoint}
              disabled={saving || !bridgeUrl.trim()}
              className="px-3 py-1.5 text-xs font-semibold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white transition disabled:opacity-50 flex items-center gap-1.5 shadow-sm shadow-indigo-600/20"
              title="Save URL to system configuration and .env"
            >
              <Save className={`w-3.5 h-3.5 ${saving ? "animate-spin" : ""}`} />
              <span>{saving ? "Saving..." : "Save Endpoint"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Quota & Telemetry Info */}
      {status && isOnline && (
        <div className="text-[11px] text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-950/50 p-2.5 rounded-xl border border-slate-200/80 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-slate-900 dark:text-white">
              Account: {status.email || "Active"}
            </span>
            <span>•</span>
            <span>
              Plan: <span className="font-bold text-indigo-600 dark:text-indigo-400">{(status.plan_type || "Standard").toUpperCase()}</span>
            </span>
            {status.left_percent !== undefined && (
              <>
                <span>•</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                  Quota Left: {status.left_percent}%
                </span>
              </>
            )}
          </div>

          <a
            href={`${bridgeUrl.replace(/\/$/, "")}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[10px] font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            <span>Open Swagger Docs</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      )}

      {/* Result Message Banner */}
      {resultMsg && (
        <div
          className={`p-2.5 rounded-xl text-xs flex items-center gap-2 border ${
            resultMsg.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-800 dark:text-emerald-300"
              : "bg-rose-500/10 border-rose-500/20 text-rose-800 dark:text-rose-300"
          }`}
        >
          {resultMsg.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
          )}
          <span>{resultMsg.text}</span>
        </div>
      )}
    </div>
  );
}
