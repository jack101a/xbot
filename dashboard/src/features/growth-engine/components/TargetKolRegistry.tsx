"use client";

import React from "react";
import { Crosshair, Plus, Trash2, CheckCircle } from "lucide-react";

interface TargetKolRegistryProps {
  targetKols: any[];
  newKolHandle: string;
  setNewKolHandle: (val: string) => void;
  newKolAngle: string;
  setNewKolAngle: (val: any) => void;
  newKolPriority: string;
  setNewKolPriority: (val: any) => void;
  savingKols: boolean;
  handleAddKol: () => void;
  handleRemoveKol: (handle: string) => void;
  kolActionMsg: string | null;
}

export function TargetKolRegistry({
  targetKols,
  newKolHandle,
  setNewKolHandle,
  newKolAngle,
  setNewKolAngle,
  newKolPriority,
  setNewKolPriority,
  savingKols,
  handleAddKol,
  handleRemoveKol,
  kolActionMsg,
}: TargetKolRegistryProps) {
  return (
    <div className="lg:col-span-5 space-y-4">
      <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
            <Crosshair className="w-4 h-4 text-rose-500" />
            <span>Target KOL Creator Registry</span>
          </h3>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 font-semibold">
            {targetKols.length} Active
          </span>
        </div>

        {kolActionMsg && (
          <div className="p-2.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            <span>{kolActionMsg}</span>
          </div>
        )}

        {/* Add New KOL Form */}
        <div className="space-y-3 p-3 sm:p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800/80">
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              value={newKolHandle}
              onChange={(e) => setNewKolHandle(e.target.value)}
              placeholder="@creator_handle"
              className="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono text-slate-900 dark:text-white"
            />
            <select
              value={newKolAngle}
              onChange={(e: any) => setNewKolAngle(e.target.value)}
              className="px-2.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs text-slate-700 dark:text-slate-300"
            >
              <option value="contrarian">Contrarian</option>
              <option value="framework">Framework</option>
              <option value="witty">Witty</option>
              <option value="data">Data</option>
              <option value="insight">Insight</option>
            </select>
          </div>
          <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-2">
            <select
              value={newKolPriority}
              onChange={(e: any) => setNewKolPriority(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs text-slate-700 dark:text-slate-300"
            >
              <option value="high">High Priority</option>
              <option value="medium">Medium Priority</option>
              <option value="low">Low Priority</option>
            </select>
            <button
              onClick={handleAddKol}
              disabled={savingKols || !newKolHandle.trim()}
              className="px-3.5 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition disabled:opacity-50"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Creator</span>
            </button>
          </div>
        </div>

        {/* KOL List */}
        <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
          {targetKols.map((kol) => (
            <div
              key={kol.handle}
              className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/30 flex items-center justify-between group hover:border-rose-300 dark:hover:border-rose-900/60 transition"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-bold text-xs text-slate-900 dark:text-white font-mono truncate">
                    @{kol.handle}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-md font-semibold uppercase bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-400">
                    {kol.preferred_angle}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 capitalize mt-0.5 truncate">
                  {kol.priority} priority • {kol.category}
                </p>
              </div>
              <button
                onClick={() => handleRemoveKol(kol.handle)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/50 transition opacity-60 group-hover:opacity-100 flex-shrink-0 ml-2"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
