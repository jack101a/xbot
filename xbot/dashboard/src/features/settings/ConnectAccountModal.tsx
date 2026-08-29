"use client";

import React, { useState, useEffect } from "react";
import { Key, FileCode, CheckCircle2, AlertCircle } from "lucide-react";
import { api, Profile, ProfileAuthStatus } from "@/lib/api";
import { ConnectAccountHeader } from "./components/ConnectAccountHeader";
import { AccountHandleInput } from "./components/AccountHandleInput";
import { CookieImportForm } from "./components/CookieImportForm";
import { RawCookieImportForm } from "./components/RawCookieImportForm";
import { ConnectAccountActions } from "./components/ConnectAccountActions";

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
  const [customHandle, setCustomHandle] = useState("");
  const [authToken, setAuthToken] = useState("");
  const [ct0, setCt0] = useState("");
  const [twid, setTwid] = useState("");
  const [rawCookies, setRawCookies] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLaunchingBrowser, setIsLaunchingBrowser] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (profile) {
      setCustomHandle(profile.x_handle?.replace(/^@+/, "") || "");
    }
  }, [profile]);

  if (!isOpen || !profile) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      const cleanHandle = customHandle.trim().replace(/^@+/, "");
      if (cleanHandle && cleanHandle !== profile.x_handle?.replace(/^@+/, "")) {
        await api.updateProfile(profile.id, { x_handle: cleanHandle });
      }

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
      setSuccess("Account connected successfully! Probing & syncing profile from X...");

      try {
        await api.syncProfileFromX(profile.id);
      } catch (syncErr) {
        console.warn("Auto-sync notice:", syncErr);
      }

      setTimeout(() => {
        if (onSuccess) onSuccess(res.auth_status);
        onClose();
        setAuthToken("");
        setCt0("");
        setTwid("");
        setRawCookies("");
        setSuccess(null);
      }, 1200);
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
    <div className="fixed inset-0 bg-slate-950/70 z-50 flex items-center justify-center p-2.5 sm:p-4 animate-in fade-in duration-200">
      <div className="bg-slate-900/95 text-slate-100 border border-slate-700/60 rounded-2xl shadow-2xl max-w-lg w-full max-h-[92vh] overflow-y-auto p-4 sm:p-6 relative">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(99,102,241,0.15),transparent)] pointer-events-none" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_80%,rgba(168,85,247,0.12),transparent)] pointer-events-none" />

        <ConnectAccountHeader
          profile={profile}
          customHandle={customHandle}
          onClose={onClose}
        />

        <AccountHandleInput
          customHandle={customHandle}
          setCustomHandle={setCustomHandle}
        />

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
            <FileCode size={14} /> Paste Raw / JSON
          </button>
        </div>

        {/* Tab Content & Form */}
        <form onSubmit={handleSubmit} className="relative z-10 mt-4 space-y-4">
          {activeTab === "fast" ? (
            <CookieImportForm
              authToken={authToken}
              setAuthToken={setAuthToken}
              ct0={ct0}
              setCt0={setCt0}
              twid={twid}
              setTwid={setTwid}
            />
          ) : (
            <RawCookieImportForm
              rawCookies={rawCookies}
              setRawCookies={setRawCookies}
            />
          )}

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

          <ConnectAccountActions
            isLaunchingBrowser={isLaunchingBrowser}
            isSubmitting={isSubmitting}
            onLaunchBrowser={handleLaunchBrowserLogin}
            onClose={onClose}
          />
        </form>
      </div>
    </div>
  );
}
