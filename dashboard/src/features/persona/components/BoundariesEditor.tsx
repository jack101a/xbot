import React, { useState } from "react";
import { ShieldAlert, Package, Ban, Sparkles, Eye, UserX, Plus } from "lucide-react";
import { PersonaState } from "../types";

interface BoundariesEditorProps {
  persona: PersonaState | null;
  setPersona: React.Dispatch<React.SetStateAction<PersonaState | null>>;
}

export function BoundariesEditor({ persona, setPersona }: BoundariesEditorProps) {
  const boundaries = persona?.boundaries || {};

  // Form input states
  const [newOwn, setNewOwn] = useState("");
  const [newNeverOwn, setNewNeverOwn] = useState("");
  const [newExpert, setNewExpert] = useState("");
  const [newSpectator, setNewSpectator] = useState("");
  const [newNeverRole, setNewNeverRole] = useState("");

  const updateBoundaries = (field: keyof typeof boundaries, updatedList: string[]) => {
    if (!persona) return;
    setPersona({
      ...persona,
      boundaries: {
        ...boundaries,
        [field]: updatedList,
      },
    });
  };

  const handleAddItem = (
    field: "owns" | "never_owns" | "expert_in" | "spectator_only" | "never_claim_to_be",
    value: string,
    clearFn: (v: string) => void
  ) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    const currentList = boundaries[field] || [];
    if (!currentList.includes(trimmed)) {
      updateBoundaries(field, [...currentList, trimmed]);
    }
    clearFn("");
  };

  const handleRemoveItem = (
    field: "owns" | "never_owns" | "expert_in" | "spectator_only" | "never_claim_to_be",
    index: number
  ) => {
    const currentList = boundaries[field] || [];
    updateBoundaries(
      field,
      currentList.filter((_, idx) => idx !== index)
    );
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-4 sm:p-5 rounded-2xl border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/50 dark:bg-indigo-950/30">
        <div className="flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-indigo-600 dark:text-indigo-400 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="font-bold text-sm text-slate-900 dark:text-white">
              Character Reality & Dynamic Boundaries
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 leading-relaxed">
              These dynamic boundaries strictly govern the bot&apos;s lived reality across all tweets, replies, and quote posts.
              Prevent AI hallucinations by declaring what the profile genuinely owns, what it knows, and what it must never claim.
            </p>
          </div>
        </div>
      </div>

      {/* Grid: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* 1. What I Own & Use */}
        <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Package className="w-4 h-4 text-emerald-500" />
            <h4 className="font-bold text-sm text-slate-900 dark:text-white">What I Own & Use</h4>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Physical gadgets and everyday tools the character can casually mention or use in scenes.
          </p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newOwn}
              onChange={(e) => setNewOwn(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddItem("owns", newOwn, setNewOwn)}
              placeholder="e.g. iPhone Pro, laptop for video editing, ring light..."
              className="flex-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <button
              type="button"
              onClick={() => handleAddItem("owns", newOwn, setNewOwn)}
              className="p-2 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 transition flex-shrink-0"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            {(boundaries.owns || []).map((item, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
              >
                <span>{item}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveItem("owns", idx)}
                  className="hover:text-rose-500 transition ml-0.5"
                >
                  &times;
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* 2. Never Claim to Own */}
        <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Ban className="w-4 h-4 text-rose-500" />
            <h4 className="font-bold text-sm text-slate-900 dark:text-white">Never Claim to Own</h4>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Hardware and items strictly forbidden from first-person claims (&quot;my GPU&quot;, &quot;my server&quot;).
          </p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newNeverOwn}
              onChange={(e) => setNewNeverOwn(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddItem("never_owns", newNeverOwn, setNewNeverOwn)}
              placeholder="e.g. Dedicated GPUs, server clusters, Linux dev rigs..."
              className="flex-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500"
            />
            <button
              type="button"
              onClick={() => handleAddItem("never_owns", newNeverOwn, setNewNeverOwn)}
              className="p-2 rounded-xl bg-rose-600 text-white hover:bg-rose-700 transition flex-shrink-0"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            {(boundaries.never_owns || []).map((item, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800"
              >
                <span>{item}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveItem("never_owns", idx)}
                  className="hover:text-rose-500 transition ml-0.5"
                >
                  &times;
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* 3. Deep Knowledge & Skills */}
        <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-500" />
            <h4 className="font-bold text-sm text-slate-900 dark:text-white">Deep Knowledge & Skills</h4>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Domains where the character can speak with genuine authority, deep nuance, and high aesthetic taste.
          </p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newExpert}
              onChange={(e) => setNewExpert(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddItem("expert_in", newExpert, setNewExpert)}
              placeholder="e.g. Visual aesthetics, video editing, Christopher Nolan cinema..."
              className="flex-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              type="button"
              onClick={() => handleAddItem("expert_in", newExpert, setNewExpert)}
              className="p-2 rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 transition flex-shrink-0"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            {(boundaries.expert_in || []).map((item, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800"
              >
                <span>{item}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveItem("expert_in", idx)}
                  className="hover:text-rose-500 transition ml-0.5"
                >
                  &times;
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* 4. Zero Knowledge / Spectator Only */}
        <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Eye className="w-4 h-4 text-amber-500" />
            <h4 className="font-bold text-sm text-slate-900 dark:text-white">Zero Knowledge / Spectator Only</h4>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Topics where the character must react ONLY as a curious outsider or consumer—never an expert lecturer.
          </p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newSpectator}
              onChange={(e) => setNewSpectator(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddItem("spectator_only", newSpectator, setNewSpectator)}
              placeholder="e.g. Software engineering, silicon hardware, financial trading..."
              className="flex-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-amber-500"
            />
            <button
              type="button"
              onClick={() => handleAddItem("spectator_only", newSpectator, setNewSpectator)}
              className="p-2 rounded-xl bg-amber-600 text-white hover:bg-amber-700 transition flex-shrink-0"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            {(boundaries.spectator_only || []).map((item, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
              >
                <span>{item}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveItem("spectator_only", idx)}
                  className="hover:text-rose-500 transition ml-0.5"
                >
                  &times;
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* 5. Never Claim to Be */}
        <div className="lg:col-span-2 p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <UserX className="w-4 h-4 text-rose-600" />
            <h4 className="font-bold text-sm text-slate-900 dark:text-white">Never Claim to Be (Role Exclusions)</h4>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Professional roles, titles, or occupations the bot must NEVER claim to hold or have worked in.
          </p>
          <div className="flex items-center gap-2 max-w-xl">
            <input
              type="text"
              value={newNeverRole}
              onChange={(e) => setNewNeverRole(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddItem("never_claim_to_be", newNeverRole, setNewNeverRole)}
              placeholder="e.g. Software developer, programmer, tech founder, VC..."
              className="flex-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500"
            />
            <button
              type="button"
              onClick={() => handleAddItem("never_claim_to_be", newNeverRole, setNewNeverRole)}
              className="p-2 rounded-xl bg-rose-600 text-white hover:bg-rose-700 transition flex-shrink-0"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            {(boundaries.never_claim_to_be || []).map((item, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800"
              >
                <span>{item}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveItem("never_claim_to_be", idx)}
                  className="hover:text-rose-500 transition ml-0.5"
                >
                  &times;
                </button>
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
