import React from "react";
import { CheckCircle2, AlertCircle } from "lucide-react";

interface SystemHealthBannerProps {
  actionMsg: { type: "success" | "error"; text: string } | null;
  onDismiss: () => void;
}

export function SystemHealthBanner({ actionMsg, onDismiss }: SystemHealthBannerProps) {
  if (!actionMsg) return null;

  return (
    <div
      className={`p-3.5 rounded-xl flex items-center justify-between border ${
        actionMsg.type === "success"
          ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
          : "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300"
      }`}
    >
      <div className="flex items-center gap-2.5">
        {actionMsg.type === "success" ? (
          <CheckCircle2 className="w-4 h-4 flex-shrink-0 text-emerald-600 dark:text-emerald-400" />
        ) : (
          <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-600 dark:text-rose-400" />
        )}
        <span className="text-xs sm:text-sm font-medium">{actionMsg.text}</span>
      </div>
      <button
        onClick={onDismiss}
        className="text-xs font-semibold underline hover:opacity-75 ml-2"
      >
        Dismiss
      </button>
    </div>
  );
}
