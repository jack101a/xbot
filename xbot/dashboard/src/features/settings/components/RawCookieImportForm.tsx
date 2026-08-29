"use client";

import React from "react";

interface RawCookieImportFormProps {
  rawCookies: string;
  setRawCookies: (val: string) => void;
}

export function RawCookieImportForm({
  rawCookies,
  setRawCookies,
}: RawCookieImportFormProps) {
  return (
    <div className="space-y-3">
      <div className="p-3 bg-purple-950/40 border border-purple-800/40 rounded-xl text-[11px] text-purple-200/90 leading-relaxed">
        <span className="font-semibold text-purple-300 block mb-1">
          Paste Cookie Header or JSON:
        </span>
        <p className="text-slate-300">
          Paste raw cookie header string (e.g.{" "}
          <code className="font-mono text-purple-300">auth_token=...; ct0=...</code>) or export
          from browser extensions like <span className="font-medium text-white">Cookie-Editor</span>{" "}
          (JSON array).
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
          placeholder={
            'auth_token=xxxx; ct0=yyyy; twid="u=12345";\n\nOR\n[\n  {"name": "auth_token", "value": "xxxx"},\n  {"name": "ct0", "value": "yyyy"}\n]'
          }
          className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700/80 rounded-lg text-xs text-white font-mono placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 resize-none"
          required
        />
      </div>
    </div>
  );
}
