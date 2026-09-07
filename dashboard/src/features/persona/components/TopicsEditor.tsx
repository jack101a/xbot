import React from "react";
import { Tag, ShieldAlert, Plus } from "lucide-react";
import { PersonaState } from "../types";

export function TopicsEditor({
  persona,
  setPersona,
  newPrimaryTopic,
  setNewPrimaryTopic,
  newAntiTopic,
  setNewAntiTopic,
  handleAddPrimaryTopic,
  handleRemovePrimaryTopic,
  handleAddAntiTopic,
  handleRemoveAntiTopic
}: {
  persona: PersonaState | null;
  setPersona: React.Dispatch<React.SetStateAction<PersonaState | null>>;
  newPrimaryTopic: string;
  setNewPrimaryTopic: (v: string) => void;
  newAntiTopic: string;
  setNewAntiTopic: (v: string) => void;
  handleAddPrimaryTopic: () => void;
  handleRemovePrimaryTopic: (idx: number) => void;
  handleAddAntiTopic: () => void;
  handleRemoveAntiTopic: (idx: number) => void;
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
      <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <Tag className="w-4 h-4 text-indigo-500" />
          <h3 className="font-bold text-sm text-slate-900 dark:text-white">Allowed Niche Topics</h3>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          The AI bot will actively seek out and tweet about these core subjects.
        </p>

        <div className="flex items-center gap-2">
          <input
            type="text"
            value={newPrimaryTopic}
            onChange={(e) => setNewPrimaryTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddPrimaryTopic()}
            placeholder="Add topic (e.g. Distributed Systems, Rust, Next.js)..."
            className="flex-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            onClick={handleAddPrimaryTopic}
            className="p-2 rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 transition flex-shrink-0"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex flex-wrap gap-2 pt-2">
          {(persona?.interests?.primary || []).map((t: string, idx: number) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800"
            >
              <span>{t}</span>
              <button
                onClick={() => handleRemovePrimaryTopic(idx)}
                className="hover:text-rose-500 transition"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      </div>

      <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-rose-500" />
          <h3 className="font-bold text-sm text-slate-900 dark:text-white">Strict Anti-Topics (Taboos)</h3>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          The AI bot will NEVER post, reply to, or engage with these forbidden topics.
        </p>
        <div className="flex flex-wrap gap-1.5 pt-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 self-center mr-1">Quick Add:</span>
          {[
            "Electoral Politics & Politicians",
            "Religion & Communal Debates",
            "Crypto, Meme Coins & Airdrops",
            "Celebrity Gossip & Scandals",
            "NSFW / 18+ Content",
            "Follow-for-Follow Spam",
          ].map((preset) => {
            const isAdded = (persona?.interests?.will_not_discuss || []).includes(preset);
            return (
              <button
                key={preset}
                type="button"
                disabled={isAdded}
                onClick={() => {
                  if (!isAdded) {
                    const current = persona?.interests?.will_not_discuss || [];
                    setPersona({
                      ...persona,
                      interests: {
                        ...persona?.interests,
                        will_not_discuss: [...current, preset],
                      },
                    });
                  }
                }}
                className={`px-2 py-0.5 rounded-lg text-[10px] font-medium border transition ${
                  isAdded
                    ? "bg-slate-100 dark:bg-slate-800 text-slate-400 border-slate-200 dark:border-slate-700 opacity-50 cursor-not-allowed"
                    : "bg-rose-50/70 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-800 hover:bg-rose-100 dark:hover:bg-rose-900/50 cursor-pointer"
                }`}
              >
                {isAdded ? "✓ " : "+ "}
                {preset}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            value={newAntiTopic}
            onChange={(e) => setNewAntiTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddAntiTopic()}
            placeholder="Add custom forbidden topic (e.g. Gossip, Drama, Specific Names)..."
            className="flex-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500"
          />
          <button
            onClick={handleAddAntiTopic}
            className="p-2 rounded-xl bg-rose-600 text-white hover:bg-rose-700 transition flex-shrink-0"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex flex-wrap gap-2 pt-2">
          {(persona?.interests?.will_not_discuss || []).map((t: string, idx: number) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800"
            >
              <span>{t}</span>
              <button
                onClick={() => handleRemoveAntiTopic(idx)}
                className="hover:text-rose-900 transition font-bold"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
