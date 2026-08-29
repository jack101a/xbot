import React from "react";
import { PersonaState } from "../types";

export function PersonaCardEditor({
  persona,
  setPersona
}: {
  persona: PersonaState | null;
  setPersona: React.Dispatch<React.SetStateAction<PersonaState | null>>;
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
      <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
        <h3 className="font-bold text-sm text-slate-900 dark:text-white">Core Identity & Background</h3>
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">
            Display Name
          </label>
          <input
            type="text"
            value={persona?.display_name || ""}
            onChange={(e) => setPersona({ ...persona, display_name: e.target.value })}
            className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">
            Background & Persona Story
          </label>
          <textarea
            rows={4}
            value={persona?.identity?.background || ""}
            onChange={(e) =>
              setPersona({
                ...persona,
                identity: { ...(persona?.identity || {}), background: e.target.value }
              })
            }
            placeholder="Senior AI engineer and open-source builder sharing real-world systems benchmarks and architecture breakdowns."
            className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">
            Communication Style
          </label>
          <input
            type="text"
            value={persona?.personality?.communication_style || ""}
            onChange={(e) =>
              setPersona({
                ...persona,
                personality: { ...(persona?.personality || {}), communication_style: e.target.value }
              })
            }
            placeholder="Direct, sharp, no corporate fluff, technical clarity."
            className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>
      <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
        <h3 className="font-bold text-sm text-slate-900 dark:text-white">Writing Style & Formatting</h3>
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">
            Tone of Voice
          </label>
          <input
            type="text"
            value={persona?.writing_style?.tone || ""}
            onChange={(e) =>
              setPersona({
                ...persona,
                writing_style: { ...(persona?.writing_style || {}), tone: e.target.value }
              })
            }
            placeholder="Authoritative, analytical, witty, contrarian."
            className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">
            Short-Term Goals
          </label>
          <textarea
            rows={2}
            value={Array.isArray(persona?.goals?.short_term) ? persona?.goals?.short_term.join(", ") : ""}
            onChange={(e) =>
              setPersona({
                ...persona,
                goals: {
                  ...(persona?.goals || {}),
                  short_term: e.target.value.split(",").map((s: string) => s.trim()).filter(Boolean)
                }
              })
            }
            placeholder="Grow 10,000 high-signal tech followers, establish thought leadership in AI agents."
            className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">
            Content Pillars (Comma Separated)
          </label>
          <input
            type="text"
            value={Array.isArray(persona?.goals?.content_pillars) ? persona?.goals?.content_pillars.join(", ") : ""}
            onChange={(e) =>
              setPersona({
                ...persona,
                goals: {
                  ...(persona?.goals || {}),
                  content_pillars: e.target.value.split(",").map((s: string) => s.trim()).filter(Boolean)
                }
              })
            }
            placeholder="AI Engineering, Architecture Diagrams, Coding Tips, Tech Critiques"
            className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>
    </div>
  );
}
