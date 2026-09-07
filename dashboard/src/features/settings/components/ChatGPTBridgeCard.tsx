"use client";

import React, { useState, useEffect } from "react";
import { Sparkles, CheckCircle2, AlertCircle, RefreshCw, ChevronDown, ChevronUp, Play, UserCheck } from "lucide-react";
import { api } from "@/lib/api";

export function ChatGPTBridgeCard() {
  const [status, setStatus] = useState<{
    status: string;
    has_cookie_file: boolean;
    cookie_count: number;
    has_valid_session_token: boolean;
    message: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showPaste, setShowPaste] = useState(false);
  const [rawCookies, setRawCookies] = useState("");
  const [importing, setImporting] = useState(false);
  const [resultMsg, setResultMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await api.getChatGPTStatus();
      setStatus(res);
    } catch (e: any) {
      setStatus({
        status: "error",
        has_cookie_file: false,
        cookie_count: 0,
        has_valid_session_token: false,
        message: e?.message || "Could not check ChatGPT bridge status",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleTestSession = async () => {
    setTesting(true);
    setResultMsg(null);
    try {
      const res = await api.testChatGPTLiveSession();
      if (res.authenticated) {
        setResultMsg({
          type: "success",
          text: `Verified! Live session active for ${res.user?.email || "ChatGPT account"} (${res.latency_ms}ms)`,
        });
        await fetchStatus();
      } else {
        setResultMsg({
          type: "error",
          text: res.message || "Live session check failed. Please refresh cookies.",
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

  const handleImport = async () => {
    if (!rawCookies.trim()) return;
    setImporting(true);
    setResultMsg(null);
    try {
      const res = await api.importChatGPTCookies(rawCookies.trim());
      if (res.status === "success") {
        setResultMsg({
          type: "success",
          text: `Imported ${res.cookie_count} cookies! Session is ${res.has_valid_session_token ? "VALID" : "missing session token"}. Running live test...`,
        });
        setRawCookies("");
        setShowPaste(false);
        await fetchStatus();
        await handleTestSession();
      } else {
        setResultMsg({ type: "error", text: res.message || "Failed to import cookies" });
      }
    } catch (err: any) {
      setResultMsg({ type: "error", text: err?.message || "Cookie import failed" });
    } finally {
      setImporting(false);
    }
  };

  const isAuthed = status?.status === "authenticated" || status?.has_valid_session_token;

  return (
    <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/40 dark:bg-emerald-950/20 space-y-3 mt-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-900 dark:text-emerald-300">
            ChatGPT Web Bridge (Zero API Cost)
          </h4>
        </div>
        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
          <span
            className={`inline-flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${
              isAuthed
                ? "bg-emerald-100 dark:bg-emerald-900/80 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700"
                : "bg-amber-100 dark:bg-amber-900/80 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-700"
            }`}
          >
            {isAuthed ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
            {isAuthed ? "Session Active" : "Cookie Required"}
          </span>

          <button
            type="button"
            onClick={handleTestSession}
            disabled={testing || !status?.has_cookie_file}
            className="px-2.5 py-1 text-[10px] font-bold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition disabled:opacity-50 flex items-center gap-1 shadow-sm"
            title="Test live ChatGPT connection"
          >
            <Play className={`w-3 h-3 ${testing ? "animate-spin" : ""}`} />
            <span>{testing ? "Testing..." : "Test Live Session"}</span>
          </button>

          <button
            type="button"
            onClick={fetchStatus}
            disabled={loading}
            className="p-1 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 transition"
            title="Refresh cookie status"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
        Powering <strong>Major Posts, Viral Threads, Quotes, and Studio DALL-E 3 Images</strong> directly via your logged-in ChatGPT account.
      </p>

      {status?.has_cookie_file && (
        <div className="text-[10px] text-emerald-800 dark:text-emerald-400 font-mono flex items-center gap-1.5 flex-wrap">
          <span className="font-semibold">✓ {status.cookie_count} cookies loaded</span>
          <span>•</span>
          <span>{status.message}</span>
        </div>
      )}

      {resultMsg && (
        <div
          className={`p-2.5 rounded-lg text-xs flex items-center gap-2 ${
            resultMsg.type === "success"
              ? "bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-200"
              : "bg-rose-100 dark:bg-rose-900/60 text-rose-800 dark:text-rose-200"
          }`}
        >
          {resultMsg.type === "success" ? (
            <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          )}
          <span>{resultMsg.text}</span>
        </div>
      )}

      <div className="pt-1">
        <button
          type="button"
          onClick={() => setShowPaste(!showPaste)}
          className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 hover:text-emerald-800 dark:hover:text-emerald-200 flex items-center gap-1 transition"
        >
          <span>{showPaste ? "Hide Cookie Import" : "Paste / Update ChatGPT Cookies"}</span>
          {showPaste ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {showPaste && (
          <div className="mt-2.5 space-y-2 p-3 rounded-lg bg-white dark:bg-slate-900 border border-emerald-200 dark:border-emerald-800/60">
            <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300">
              Paste Cookies JSON array or Netscape text:
            </label>
            <p className="text-[10px] text-slate-500 dark:text-slate-400">
              Export cookies while logged into <strong>chatgpt.com</strong> (e.g. using the &quot;Cookie-Editor&quot; extension $\rightarrow$ Export JSON) and paste below.
            </p>
            <textarea
              rows={4}
              value={rawCookies}
              onChange={(e) => setRawCookies(e.target.value)}
              placeholder='[{"name": "__Secure-next-auth.session-token", "value": "eyJ...", "domain": ".chatgpt.com"}, ...]'
              className="w-full p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 font-mono text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowPaste(false)}
                className="px-3 py-1 text-xs rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleImport}
                disabled={importing || !rawCookies.trim()}
                className="px-3 py-1 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
              >
                <RefreshCw className={`w-3 h-3 ${importing ? "animate-spin" : ""}`} />
                <span>{importing ? "Importing & Verifying..." : "Save & Verify Session"}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
