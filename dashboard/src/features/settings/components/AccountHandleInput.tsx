"use client";

import React from "react";

interface AccountHandleInputProps {
  customHandle: string;
  setCustomHandle: (val: string) => void;
}

export function AccountHandleInput({
  customHandle,
  setCustomHandle,
}: AccountHandleInputProps) {
  return (
    <div className="relative z-10 mt-4">
      <label className="block text-xs font-semibold text-slate-300 mb-1">
        Your Real X Handle (@username) <span className="text-rose-400">*</span>
      </label>
      <div className="relative">
        <span className="absolute left-3 top-2.5 text-slate-500 font-mono text-xs">@</span>
        <input
          type="text"
          value={customHandle}
          onChange={(e) => setCustomHandle(e.target.value)}
          placeholder="e.g. elonmusk, my_real_handle"
          className="w-full pl-7 pr-3 py-2 bg-slate-950/80 border border-slate-700/80 rounded-lg text-xs text-white font-mono placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
          required
        />
      </div>
      <p className="text-[11px] text-slate-400 mt-1">
        Enter your exact Twitter username so the sync engine fetches your real profile picture and follower metrics.
      </p>
    </div>
  );
}
