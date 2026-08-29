"use client";

import React from "react";
import { Sparkles, ExternalLink } from "lucide-react";

interface CookieImportFormProps {
  authToken: string;
  setAuthToken: (val: string) => void;
  ct0: string;
  setCt0: (val: string) => void;
  twid: string;
  setTwid: (val: string) => void;
}

export function CookieImportForm({
  authToken,
  setAuthToken,
  ct0,
  setCt0,
  twid,
  setTwid,
}: CookieImportFormProps) {
  return (
    <div className="space-y-3">
      {/* Quick instructions */}
      <div className="p-3 bg-indigo-950/40 border border-indigo-800/40 rounded-xl text-[11px] text-indigo-200/90 leading-relaxed">
        <span className="font-semibold text-indigo-300 mb-1 flex items-center gap-1.5">
          <Sparkles size={13} /> Quick Instructions:
        </span>
        <ol className="list-decimal list-inside space-y-0.5 text-slate-300">
          <li>
            Open{" "}
            <a
              href="https://x.com"
              target="_blank"
              rel="noreferrer"
              className="text-indigo-400 underline inline-flex items-center gap-0.5"
            >
              x.com <ExternalLink size={10} />
            </a>{" "}
            and log in
          </li>
          <li>
            Press{" "}
            <kbd className="px-1 py-0.5 bg-slate-800 rounded text-[10px] font-mono border border-slate-700">
              F12
            </kbd>{" "}
            (DevTools) &rarr; <span className="font-medium text-white">Application</span> tab
          </li>
          <li>
            Under <span className="font-medium text-white">Storage &rarr; Cookies</span>, select{" "}
            <span className="font-mono text-indigo-300">https://x.com</span>
          </li>
          <li>
            Copy values for <code className="font-mono text-indigo-300">auth_token</code> and{" "}
            <code className="font-mono text-indigo-300">ct0</code>
          </li>
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
  );
}
