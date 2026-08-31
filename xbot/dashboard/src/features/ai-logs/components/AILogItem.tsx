"use client";

import React, { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Zap,
  Clock,
  AlertCircle,
  CheckCircle2,
  Terminal,
  Bot,
  User,
} from "lucide-react";
import { AIPromptLogItem } from "../types";

interface AILogItemProps {
  log: AIPromptLogItem;
}

export function AILogItem({ log }: AILogItemProps) {
  const [expanded, setExpanded] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState(false);
  const [copiedOutput, setCopiedOutput] = useState(false);

  const copyText = async (text: string, isPrompt: boolean) => {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
      if (isPrompt) {
        setCopiedPrompt(true);
        setTimeout(() => setCopiedPrompt(false), 2000);
      } else {
        setCopiedOutput(true);
        setTimeout(() => setCopiedOutput(false), 2000);
      }
    } catch (err) {
      console.warn("Clipboard copy error:", err);
    }
  };

  const isChatGPT = log.provider.toLowerCase().includes("chatgpt");
  const isError = log.status === "error";

  return (
    <div
      className={`border rounded-xl transition overflow-hidden ${
        isError
          ? "border-rose-300 dark:border-rose-900/60 bg-rose-50/20 dark:bg-rose-950/10"
          : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700"
      }`}
    >
      {/* Header Row */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="p-3.5 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer select-none"
      >
        <div className="flex items-start sm:items-center gap-3 min-w-0">
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
              isError
                ? "bg-rose-100 dark:bg-rose-950/60 text-rose-600"
                : isChatGPT
                ? "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400"
                : "bg-purple-100 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400"
            }`}
          >
            {isError ? <AlertCircle className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-xs text-slate-900 dark:text-slate-100 uppercase tracking-wider">
                {log.action_type || "AI Request"}
              </span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-medium ${
                  isChatGPT
                    ? "bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                }`}
              >
                {log.provider}/{log.model}
              </span>
              {log.profile_slug && log.profile_slug !== "global" && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 font-mono">
                  @{log.profile_slug}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 truncate mt-0.5 max-w-xl font-mono">
              {log.user_prompt || log.system_prompt || "(Empty prompt payload)"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto text-xs text-slate-500 dark:text-slate-400 flex-shrink-0">
          <div className="flex items-center gap-1 font-mono text-[11px] bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
            <Zap className="w-3 h-3 text-amber-500" />
            {log.latency_ms}ms
          </div>
          <span className="text-[11px] hidden md:inline">{log.iso_time}</span>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </div>

      {/* Expanded Details Body */}
      {expanded && (
        <div className="border-t border-slate-100 dark:border-slate-800/80 p-4 sm:p-5 bg-slate-50/50 dark:bg-slate-950/50 space-y-4">
          {/* System Prompt (if present) */}
          {log.system_prompt && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
                <span className="flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-purple-500" /> System Directives
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    copyText(log.system_prompt, true);
                  }}
                  className="text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition flex items-center gap-1 text-[11px]"
                >
                  {copiedPrompt ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                  {copiedPrompt ? "Copied" : "Copy"}
                </button>
              </div>
              <pre className="text-xs font-mono bg-slate-900 text-slate-100 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                {log.system_prompt}
              </pre>
            </div>
          )}

          {/* User Prompt */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
              <span className="flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-blue-500" /> User Input & Task Prompt
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  copyText(log.user_prompt, true);
                }}
                className="text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition flex items-center gap-1 text-[11px]"
              >
                {copiedPrompt ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                {copiedPrompt ? "Copied" : "Copy"}
              </button>
            </div>
            <pre className="text-xs font-mono bg-slate-100 dark:bg-slate-900 text-slate-800 dark:text-slate-200 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto border border-slate-200 dark:border-slate-800">
              {log.user_prompt || "(None)"}
            </pre>
          </div>

          {/* AI Output / Response */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
              <span className="flex items-center gap-1.5">
                <Bot className="w-3.5 h-3.5 text-emerald-500" /> AI Output Response
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  copyText(log.response, false);
                }}
                className="text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition flex items-center gap-1 text-[11px]"
              >
                {copiedOutput ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                {copiedOutput ? "Copied" : "Copy"}
              </button>
            </div>

            {log.error_message ? (
              <div className="p-3 bg-rose-100/70 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-200 text-xs rounded-lg font-mono">
                <strong>Model Error:</strong> {log.error_message}
              </div>
            ) : (
              <pre className="text-xs font-mono bg-emerald-950/10 dark:bg-emerald-950/20 text-emerald-900 dark:text-emerald-200 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto border border-emerald-200/50 dark:border-emerald-800/40">
                {log.response || "(Empty response)"}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
