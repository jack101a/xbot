"use client";

import React, { useState } from "react";
import { 
  X, Key, FileCode, CheckCircle2, AlertCircle, Loader2, 
  ExternalLink, ShieldCheck, Sparkles, Monitor
} from "lucide-react";
import { api, Profile, ProfileAuthStatus } from "@/lib/api";

interface ConnectAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  profile: Profile | null;
  onSuccess?: (authStatus?: ProfileAuthStatus) => void;
}

export function ConnectAccountModal({
  isOpen,
  onClose,
  profile,
  onSuccess,
}: ConnectAccountModalProps) {
  const [activeTab, setActiveTab] = useState<"fast" | "raw">("fast");
  
  // Fast tab fields
  const [authToken, setAuthToken] = useState("");
  const [ct0, setCt0] = useState("");
  const [twid, setTwid] = useState("");
  
  // Raw tab field
  const [rawCookies, setRawCookies] = useState("");
  
  // Status states
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLaunchingBrowser, setIsLaunchingBrowser] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  if (!isOpen || !profile) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      let payload: {
        auth_token?: string;
        ct0?: string;
        twid?: string;
        raw_cookies?: string;
      } = {};

      if (activeTab === "fast") {
        if (!authToken.trim() || !ct0.trim()) {
          throw new Error("Both auth_token and ct0 are required for Fast Cookie Paste.");
        }
        payload = {
          auth_token: authToken.trim(),
          ct0: ct0.trim(),
          twid: twid.trim() || undefined,
        };
      } else {
        if (!rawCookies.trim()) {
          throw new Error("Please paste cookie header or JSON array in the field.");
        }
        payload = {
          raw_cookies: rawCookies.trim(),
        };
      }

      const res = await api.importProfileCookies(profile.id, payload);
      setSuccess("Account connected successfully! Session cookies saved.");
      
      // Auto-trigger sync or callback
      setTimeout(() => {
        if (onSuccess) {
          onSuccess(res.auth_status);
        }
        onClose();
        // Reset form
        setAuthToken("");
        setCt0("");
        setTwid("");
        setRawCookies("");
        setSuccess(null);
      }, 1000);
    } catch (err: any) {
      setError(err?.message || "Failed to import cookies.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLaunchBrowserLogin = async () => {
    setError(null);
    setIsLaunchingBrowser(true);
    try {
      const res = await api.launchProfileLoginSession(profile.id);
      alert(res.message || "Browser login session launched. Please log in on the opened browser window.");
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err?.message || "Failed to launch browser login session.");
    } finally {
      setIsLaunchingBrowser(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-md z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-slate-900/95 text-slate-100 border border-slate-700/60 rounded-2xl shadow-2xl max-w-lg w-full p-6 relative overflow-hidden backdrop-blur-xl">
        {/* Background ambient gradient */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(99,102,241,0.15),transparent)] pointer-events-none" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_80%,rgba(168,85,247,0.12),transparent)] pointer-events-none" />

        {/* Modal Header */}
        <div className="relative z-10 flex items-start justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
              <ShieldCheck size={20} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                Connect X Account
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  @{profile.x_handle}
                </span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Import session cookies to enable automated browsing & posting
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800/80 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="relative z-10 flex gap-2 mt-4 p-1 bg-slate-950/60 border border-slate-800 rounded-xl">
          <button
            type="button"
            onClick={() => { setActiveTab("fast"); setError(null); }}
            className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
              activeTab === "fast"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Key size={14} /> Fast Cookie Paste
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab("raw"); setError(null); }}
            className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
              activeTab === "raw"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <FileCode size={14} /> Paste Raw Header / JSON
          </button>
        </div>

        {/* Tab Content & Form */}
        <form onSubmit={handleSubmit} className="relative z-10 mt-4 space-y-4">
          {activeTab === "fast" ? (
            <div className="space-y-3">
              {/* Quick instructions */}
              <div className="p-3 bg-indigo-950/40 border border-indigo-800/40 rounded-xl text-[11px] text-indigo-200/90 leading-relaxed">
                <span className="font-semibold text-indigo-300 block mb-1 flex items-center gap-1.5">
                  <Sparkles size={13} /> Quick Instructions:
                </span>
                <ol className="list-decimal list-inside space-y-0.5 text-slate-300">
                  <li>Open <a href="https://x.com" target="_blank" rel="noreferrer" className="text-indigo-400 underline inline-flex items-center gap-0.5">x.com <ExternalLink size={10} /></a> and log in</li>
                  <li>Press <kbd className="px-1 py-0.5 bg-slate-800 rounded text-[10px] font-mono border border-slate-700">F12</kbd> (DevTools) &rarr; <span className="font-medium text-white">Application</span> tab</li>
                  <li>Under <span className="font-medium text-white">Storage &rarr; Cookies</span>, select <span className="font-mono text-indigo-300">https://x.com</span></li>
                  <li>Copy values for <code className="font-mono text-indigo-300">auth_token</code> and <code className="font-mono text-indigo-300">ct0</code></li>
                </ol>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  auth_token <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={authToken}
                  onChange={(e) => setAuthToken(e.target.value)}
                  placeholder="e.g. 3a7b9c0d1e2f4a5b6c7d8e9f..."
                  className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700/80 rounded-lg text-xs text-white font-mono placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  ct0 (CSRF Token) <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={ct0}
                  onChange={(e) => setCt0(e.target.value)}
                  placeholder="e.g. 1a2b3c4d5e6f7a8b9c0d1e2f..."
                  className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700/80 rounded-lg text-xs text-white font-mono placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  twid (User ID) <span className="text-slate-500 text-[10px]">(Optional)</span>
                </label>
                <input
                  type="text"
                  value={twid}
                  onChange={(e) => setTwid(e.target.value)}
                  placeholder="e.g. u%3D1234567890"
                  className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700/80 rounded-lg text-xs text-white font-mono placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="p-3 bg-purple-950/40 border border-purple-800/40 rounded-xl text-[11px] text-purple-200/90 leading-relaxed">
                <span className="font-semibold text-purple-300 block mb-1">
                  Paste Cookie Header or JSON:
                </span>
                <p className="text-slate-300">
                  Paste raw cookie header string (e.g. <code className="font-mono text-purple-300">auth_token=...; ct0=...</code>) or export from browser extensions like <span className="font-medium text-white">Cookie-Editor</span> (JSON array).
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Raw Cookie String or JSON Array <span className="text-rose-400">*</span>
                </label>
                <textarea
                  rows={6}
                  value={rawCookies}
                  onChange={(e) => setRawCookies(e.target.value)}
                  placeholder={'auth_token=xxxx; ct0=yyyy; twid="u=12345";\n\nOR\n[\n  {"name": "auth_token", "value": "xxxx"},\n  {"name": "ct0", "value": "yyyy"}\n]'}
                  className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700/80 rounded-lg text-xs text-white font-mono placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 resize-none"
                  required
                />
              </div>
            </div>
          )}

          {/* Feedback messages */}
          {error && (
            <div className="p-3 bg-rose-950/50 border border-rose-800/60 rounded-xl flex items-center gap-2 text-xs text-rose-300">
              <AlertCircle size={15} className="flex-shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="p-3 bg-emerald-950/50 border border-emerald-800/60 rounded-xl flex items-center gap-2 text-xs text-emerald-300">
              <CheckCircle2 size={15} className="flex-shrink-0 text-emerald-400" />
              <span>{success}</span>
            </div>
          )}

          {/* Action buttons */}
          <div className="pt-2 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={handleLaunchBrowserLogin}
              disabled={isLaunchingBrowser || isSubmitting}
              className="text-[11px] font-medium text-slate-400 hover:text-indigo-300 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-800 hover:border-indigo-500/40 hover:bg-indigo-950/30 transition-all disabled:opacity-50"
              title="Launch browser GUI to log in manually"
            >
              {isLaunchingBrowser ? <Loader2 size={12} className="animate-spin" /> : <Monitor size={12} />}
              <span>Launch Browser Login</span>
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 rounded-lg shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-2 disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    <span>Connecting...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck size={14} />
                    <span>Connect Account</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
