"use client";

import React from "react";
import { PrunerCriteria } from "../types";
import { Sliders, Eye, Heart, MessageSquare, Clock, ShieldAlert, Sparkles } from "lucide-react";

interface PrunerFilterCardProps {
  criteria: PrunerCriteria;
  setCriteria: React.Dispatch<React.SetStateAction<PrunerCriteria>>;
  onRun: () => void;
  onPreview: () => void;
  isRunning: boolean;
  isPreviewing: boolean;
  disabled: boolean;
}

export function PrunerFilterCard({
  criteria,
  setCriteria,
  onRun,
  onPreview,
  isRunning,
  isPreviewing,
  disabled,
}: PrunerFilterCardProps) {
  const handlePreset = (preset: "test" | "rapid" | "strict" | "aggressive") => {
    if (preset === "test") {
      setCriteria({
        min_views: 100,
        min_likes: 2,
        min_comments: 1,
        min_age_hours: 0,
        max_posts_to_delete: 10,
        match_mode: "all",
      });
    } else if (preset === "rapid") {
      setCriteria({
        min_views: 200,
        min_likes: 3,
        min_comments: 1,
        min_age_hours: 6,
        max_posts_to_delete: 10,
        match_mode: "all",
      });
    } else if (preset === "aggressive") {
      setCriteria({
        min_views: 500,
        min_likes: 10,
        min_comments: 3,
        min_age_hours: 12,
        max_posts_to_delete: 20,
        match_mode: "any",
      });
    } else {
      // balanced
      setCriteria({
        min_views: 300,
        min_likes: 5,
        min_comments: 2,
        min_age_hours: 24,
        max_posts_to_delete: 10,
        match_mode: "all",
      });
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-indigo-500" />
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">
              Pruning & Cleanup Rules
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Configure threshold criteria to purge low-performing original posts. Replies and comments are never touched.
          </p>
        </div>

        {/* Quick Presets */}
        <div className="flex flex-wrap items-center gap-1.5 bg-slate-100 dark:bg-slate-800/60 p-1 rounded-lg">
          <button
            type="button"
            onClick={() => handlePreset("test")}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
              criteria.min_age_hours === 0
                ? "bg-white dark:bg-slate-700 text-sky-600 dark:text-sky-400 font-semibold shadow-xs"
                : "text-slate-700 dark:text-slate-300 hover:bg-white/60 dark:hover:bg-slate-700/60"
            }`}
          >
            Immediate (0h)
          </button>
          <button
            type="button"
            onClick={() => handlePreset("rapid")}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
              criteria.min_age_hours === 6
                ? "bg-white dark:bg-slate-700 text-sky-600 dark:text-sky-400 font-semibold shadow-xs"
                : "text-slate-700 dark:text-slate-300 hover:bg-white/60 dark:hover:bg-slate-700/60"
            }`}
          >
            Rapid (6h)
          </button>
          <button
            type="button"
            onClick={() => handlePreset("strict")}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
              criteria.min_age_hours === 24 && criteria.match_mode === "all"
                ? "bg-white dark:bg-slate-700 text-sky-600 dark:text-sky-400 font-semibold shadow-xs"
                : "text-slate-700 dark:text-slate-300 hover:bg-white/60 dark:hover:bg-slate-700/60"
            }`}
          >
            Balanced (24h)
          </button>
          <button
            type="button"
            onClick={() => handlePreset("aggressive")}
            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
              criteria.match_mode === "any"
                ? "bg-white dark:bg-slate-700 text-amber-600 dark:text-amber-400 font-semibold shadow-xs"
                : "text-amber-600 dark:text-amber-400 hover:bg-white/60 dark:hover:bg-slate-700/60"
            }`}
          >
            Aggressive (Any)
          </button>
        </div>
      </div>

      {/* Grid of Metric Inputs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Min Views */}
        <div className="space-y-1.5">
          <label className="flex items-center gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-300">
            <Eye className="w-3.5 h-3.5 text-blue-500" />
            Min. Views / Impressions
          </label>
          <div className="relative">
            <input
              type="number"
              min="0"
              value={criteria.min_views}
              onChange={(e) => setCriteria({ ...criteria, min_views: Math.max(0, parseInt(e.target.value) || 0) })}
              className="w-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              placeholder="e.g. 200"
            />
            <span className="absolute right-3 top-2.5 text-xs text-slate-400">views</span>
          </div>
        </div>

        {/* Min Likes */}
        <div className="space-y-1.5">
          <label className="flex items-center gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-300">
            <Heart className="w-3.5 h-3.5 text-rose-500" />
            Min. Likes
          </label>
          <div className="relative">
            <input
              type="number"
              min="0"
              value={criteria.min_likes}
              onChange={(e) => setCriteria({ ...criteria, min_likes: Math.max(0, parseInt(e.target.value) || 0) })}
              className="w-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              placeholder="e.g. 5"
            />
            <span className="absolute right-3 top-2.5 text-xs text-slate-400">likes</span>
          </div>
        </div>

        {/* Min Comments */}
        <div className="space-y-1.5">
          <label className="flex items-center gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-300">
            <MessageSquare className="w-3.5 h-3.5 text-emerald-500" />
            Min. Replies / Comments
          </label>
          <div className="relative">
            <input
              type="number"
              min="0"
              value={criteria.min_comments}
              onChange={(e) => setCriteria({ ...criteria, min_comments: Math.max(0, parseInt(e.target.value) || 0) })}
              className="w-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              placeholder="e.g. 2"
            />
            <span className="absolute right-3 top-2.5 text-xs text-slate-400">replies</span>
          </div>
        </div>

        {/* Min Age / Grace Period */}
        <div className="space-y-1.5">
          <label className="flex items-center gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-300">
            <Clock className="w-3.5 h-3.5 text-amber-500" />
            Min. Post Age (Grace Period)
          </label>
          <select
            value={criteria.min_age_hours}
            onChange={(e) => setCriteria({ ...criteria, min_age_hours: parseInt(e.target.value) ?? 0 })}
            className="w-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
          >
            <option value={0}>0 Hours (Immediate / Test Mode)</option>
            <option value={6}>6 Hours (Fast)</option>
            <option value={12}>12 Hours (Rapid)</option>
            <option value={24}>24 Hours (Standard)</option>
            <option value={48}>48 Hours (Recommended)</option>
            <option value={72}>72 Hours (3 Days)</option>
            <option value={168}>7 Days (1 Week)</option>
          </select>
        </div>

        {/* Max Posts to Delete */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-300">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-500" />
              Max Posts to Delete (Batch Limit)
            </label>
            <div className="flex items-center gap-1">
              {[10, 25, 50, 100, 250, 500].map((num) => (
                <button
                  key={num}
                  type="button"
                  onClick={() => setCriteria({ ...criteria, max_posts_to_delete: num })}
                  className={`px-1.5 py-0.5 text-[10px] rounded transition-colors ${
                    criteria.max_posts_to_delete === num
                      ? "bg-rose-500 text-white font-semibold"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                  }`}
                >
                  {num}
                </button>
              ))}
            </div>
          </div>
          <div className="relative">
            <input
              type="number"
              min="1"
              max="500"
              value={criteria.max_posts_to_delete}
              onChange={(e) => setCriteria({ ...criteria, max_posts_to_delete: Math.min(500, Math.max(1, parseInt(e.target.value) || 1)) })}
              className="w-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
            />
            <span className="absolute right-3 top-2.5 text-xs text-slate-400">max / run (up to 500)</span>
          </div>
        </div>

        {/* Match Mode Toggle */}
        <div className="space-y-1.5">
          <label className="flex items-center gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-300">
            <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            Evaluation Match Mode
          </label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setCriteria({ ...criteria, match_mode: "all" })}
              className={`py-2 px-3 text-xs font-medium rounded-lg border transition-all ${
                criteria.match_mode === "all"
                  ? "bg-sky-50 dark:bg-sky-950/40 border-sky-500 text-sky-700 dark:text-sky-300 font-semibold"
                  : "bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400"
              }`}
            >
              Strict (Match All)
            </button>
            <button
              type="button"
              onClick={() => setCriteria({ ...criteria, match_mode: "any" })}
              className={`py-2 px-3 text-xs font-medium rounded-lg border transition-all ${
                criteria.match_mode === "any"
                  ? "bg-amber-50 dark:bg-amber-950/40 border-amber-500 text-amber-700 dark:text-amber-300 font-semibold"
                  : "bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400"
              }`}
            >
              Aggressive (Match Any)
            </button>
          </div>
        </div>
      </div>

      {/* Trigger Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-slate-100 dark:border-slate-800/80">
        <div className="text-xs text-slate-500 dark:text-slate-400">
          Target: <span className="font-semibold text-slate-700 dark:text-slate-300">Original Profile Tweets</span> • Grace: <span className="font-semibold text-slate-700 dark:text-slate-300">{criteria.min_age_hours === 0 ? "Immediate (0h)" : `>${criteria.min_age_hours}h old`}</span>
        </div>
        <div className="flex items-center gap-2.5 shrink-0">
          {/* Safe Preview / Dry-Run Button */}
          <button
            type="button"
            onClick={onPreview}
            disabled={disabled || isRunning || isPreviewing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-xs font-semibold shadow-xs transition-all active:scale-[0.98]"
            title="Scan your profile timeline and identify underperforming tweets without deleting them"
          >
            {isPreviewing ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Scanning Preview...
              </>
            ) : (
              <>
                <Eye className="w-4 h-4" />
                Scan & Preview
              </>
            )}
          </button>

          {/* Execute Prune Button */}
          <button
            type="button"
            onClick={onRun}
            disabled={disabled || isRunning || isPreviewing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white text-xs font-semibold shadow-xs transition-all active:scale-[0.98]"
            title="Scan and delete tweets matching your criteria in-place"
          >
            {isRunning ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Pruning Live...
              </>
            ) : (
              <>
                <ShieldAlert className="w-4 h-4" />
                Execute Prune
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
