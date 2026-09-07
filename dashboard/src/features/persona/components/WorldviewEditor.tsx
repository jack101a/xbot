import React, { useState } from "react";
import {
  Compass,
  Languages,
  Smile,
  Plus,
  Trash2,
  Tag,
  Check,
  Sparkles,
  Flame,
  ShieldAlert,
  Film,
  Smartphone,
  Bot,
  Sliders,
} from "lucide-react";
import { PersonaState, EntityStance, LanguageConfig, ExpressivenessConfig } from "../types";

interface WorldviewEditorProps {
  persona: PersonaState | null;
  setPersona: React.Dispatch<React.SetStateAction<PersonaState | null>>;
}

const DEFAULT_STANCES: EntityStance[] = [
  {
    name: "Christopher Nolan",
    category: "cinema",
    archetype: "loyalist",
    sentiment_split: { praise: 75, analysis: 20, critique: 5 },
    talking_points: ["practical sets & miniatures", "70mm IMAX cinematography", "sound mixing polarization"],
    behavioral_rule: "Defend practical visual stunts and commitment to theatrical cinema, playfully roast his dialogue audio mixing.",
    is_active: true,
  },
  {
    name: "One Piece",
    category: "anime",
    archetype: "loyalist",
    sentiment_split: { praise: 80, analysis: 15, critique: 5 },
    talking_points: ["Oda's foreshadowing", "worldbuilding scale", "pacing nuance"],
    behavioral_rule: "Praise Oda's masterclass worldbuilding and character emotional payoffs; celebrate epic moments with hype.",
    is_active: true,
  },
  {
    name: "Corporate AI Slop",
    category: "tech",
    archetype: "nemesis",
    sentiment_split: { praise: 5, analysis: 15, critique: 80 },
    talking_points: ["LinkedIn influencer jargon", "shallow prompt wrappers", "overhyped promises"],
    behavioral_rule: "Cynically dismantle superficial buzzwords and fake benchmark claims with dry developer wit.",
    is_active: true,
  },
  {
    name: "Modern Flagship Smartphones",
    category: "tech",
    archetype: "nuanced_critic",
    sentiment_split: { praise: 35, analysis: 45, critique: 20 },
    talking_points: ["AI camera over-processing", "battery vs thermals", "hardware plateau"],
    behavioral_rule: "Analyze camera color science and hardware engineering; call out aggressive oil-painting AI sharpening.",
    is_active: true,
  },
];

export function WorldviewEditor({ persona, setPersona }: WorldviewEditorProps) {
  const stances = persona?.stances || [];
  const langConfig: LanguageConfig = persona?.language_config || {
    primary_language: "en",
    enable_hinglish: true,
    hinglish_mode: "mirror_and_punchline",
    slang_register: "urban_buff",
    enable_hindi_script: true,
  };
  const expConfig: ExpressivenessConfig = persona?.expressiveness_config || {
    emoji_mode: "contextual_tone",
    max_emojis: 2,
    allow_zero_emojis: true,
    reply_meme_rate: 25,
    thread_media_rate: 60,
  };

  const [isAddingCustom, setIsAddingCustom] = useState(false);
  const [newEntityName, setNewEntityName] = useState("");
  const [newEntityCategory, setNewEntityCategory] = useState("cinema");
  const [newEntityArchetype, setNewEntityArchetype] = useState("loyalist");
  const [newEntityPraise, setNewEntityPraise] = useState(70);
  const [newEntityAnalysis, setNewEntityAnalysis] = useState(20);
  const [newEntityCritique, setNewEntityCritique] = useState(10);
  const [newEntityRule, setNewEntityRule] = useState("");
  const [newEntityTag, setNewEntityTag] = useState("");
  const [newEntityTalkingPoints, setNewEntityTalkingPoints] = useState<string[]>([]);

  const [activeTagInputs, setActiveTagInputs] = useState<{ [index: number]: string }>({});

  const updateStances = (newStances: EntityStance[]) => {
    setPersona((prev) => (prev ? { ...prev, stances: newStances } : prev));
  };

  const updateLangConfig = (partial: Partial<LanguageConfig>) => {
    setPersona((prev) => {
      if (!prev) return prev;
      const current = prev.language_config || langConfig;
      return { ...prev, language_config: { ...current, ...partial } };
    });
  };

  const updateExpConfig = (partial: Partial<ExpressivenessConfig>) => {
    setPersona((prev) => {
      if (!prev) return prev;
      const current = prev.expressiveness_config || expConfig;
      return { ...prev, expressiveness_config: { ...current, ...partial } };
    });
  };

  const handleToggleStanceActive = (idx: number) => {
    const next = [...stances];
    next[idx] = { ...next[idx], is_active: !next[idx].is_active };
    updateStances(next);
  };

  const handleDeleteStance = (idx: number) => {
    const next = stances.filter((_, i) => i !== idx);
    updateStances(next);
  };

  const handleSplitChange = (
    idx: number,
    field: "praise" | "analysis" | "critique",
    val: number
  ) => {
    const next = [...stances];
    const item = { ...next[idx] };
    const currentSplit = { ...item.sentiment_split };
    const clampedVal = Math.max(0, Math.min(100, val));
    currentSplit[field] = clampedVal;

    // Auto-normalize the other two fields
    const otherFields = (["praise", "analysis", "critique"] as const).filter((f) => f !== field);
    const remainder = Math.max(0, 100 - clampedVal);
    const sumOther = (currentSplit[otherFields[0]] || 0) + (currentSplit[otherFields[1]] || 0);

    if (sumOther > 0) {
      currentSplit[otherFields[0]] = Math.round((currentSplit[otherFields[0]] / sumOther) * remainder);
      currentSplit[otherFields[1]] = remainder - currentSplit[otherFields[0]];
    } else {
      currentSplit[otherFields[0]] = Math.round(remainder / 2);
      currentSplit[otherFields[1]] = remainder - currentSplit[otherFields[0]];
    }

    item.sentiment_split = currentSplit;
    next[idx] = item;
    updateStances(next);
  };

  const handleAddTagToStance = (idx: number) => {
    const tag = activeTagInputs[idx]?.trim();
    if (!tag) return;
    const next = [...stances];
    const pts = next[idx].talking_points || [];
    if (!pts.includes(tag)) {
      next[idx] = { ...next[idx], talking_points: [...pts, tag] };
      updateStances(next);
    }
    setActiveTagInputs((prev) => ({ ...prev, [idx]: "" }));
  };

  const handleRemoveTagFromStance = (idx: number, tagIdx: number) => {
    const next = [...stances];
    const pts = [...(next[idx].talking_points || [])];
    pts.splice(tagIdx, 1);
    next[idx] = { ...next[idx], talking_points: pts };
    updateStances(next);
  };

  const handleApplyPreset = (preset: EntityStance) => {
    if (stances.some((s) => s.name.toLowerCase() === preset.name.toLowerCase())) {
      return;
    }
    updateStances([...stances, preset]);
  };

  const handleCreateCustomStance = () => {
    if (!newEntityName.trim()) return;
    const newStance: EntityStance = {
      name: newEntityName.trim(),
      category: newEntityCategory,
      archetype: newEntityArchetype,
      sentiment_split: {
        praise: newEntityPraise,
        analysis: newEntityAnalysis,
        critique: newEntityCritique,
      },
      talking_points: newEntityTalkingPoints,
      behavioral_rule: newEntityRule.trim(),
      is_active: true,
    };
    updateStances([...stances, newStance]);
    setNewEntityName("");
    setNewEntityRule("");
    setNewEntityTalkingPoints([]);
    setIsAddingCustom(false);
  };

  const getArchetypeBadge = (archetype: string) => {
    switch (archetype) {
      case "loyalist":
        return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
      case "nemesis":
        return "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20";
      case "nuanced_critic":
        return "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20";
      case "guilty_pleasure":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
      default:
        return "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20";
    }
  };

  return (
    <div className="space-y-8">
      {/* 1. ENTITY STANCES & IDOLS / NEMESES */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 p-5 sm:p-6 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20">
              <Compass className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-900 dark:text-white">
                Worldview Stances & Orientations
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Define how your persona naturally feels towards specific creators, franchises, tech, or trends (Idols vs Nemeses vs Nuanced Critics).
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsAddingCustom(!isAddingCustom)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-sky-600 hover:bg-sky-700 text-white shadow-sm transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{isAddingCustom ? "Cancel" : "Add Custom Stance"}</span>
            </button>
          </div>
        </div>

        {/* Quick Presets */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-500 dark:text-slate-400">Quick Presets:</div>
          <div className="flex flex-wrap gap-2">
            {DEFAULT_STANCES.map((preset) => {
              const alreadyAdded = stances.some((s) => s.name.toLowerCase() === preset.name.toLowerCase());
              return (
                <button
                  key={preset.name}
                  onClick={() => handleApplyPreset(preset)}
                  disabled={alreadyAdded}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                    alreadyAdded
                      ? "opacity-50 cursor-not-allowed border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-800/40 text-slate-400"
                      : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-sky-500 hover:text-sky-600 dark:hover:text-sky-400 text-slate-700 dark:text-slate-200"
                  }`}
                >
                  <Sparkles className="w-3 h-3 text-amber-500" />
                  <span>{preset.name}</span>
                  <span className="text-[10px] text-slate-400">({preset.archetype})</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Custom Stance Creator Modal/Form */}
        {isAddingCustom && (
          <div className="p-4 rounded-xl border border-sky-200 dark:border-sky-900/60 bg-sky-50/40 dark:bg-sky-950/20 space-y-4">
            <div className="text-xs font-bold text-sky-900 dark:text-sky-300 uppercase tracking-wider">
              Create New Entity Stance
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Entity / Topic Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Quentin Tarantino, Apple, Elden Ring"
                  value={newEntityName}
                  onChange={(e) => setNewEntityName(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Category
                </label>
                <select
                  value={newEntityCategory}
                  onChange={(e) => setNewEntityCategory(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                >
                  <option value="cinema">Cinema & Pop Culture</option>
                  <option value="anime">Anime & Manga</option>
                  <option value="tech">Consumer Tech & AI</option>
                  <option value="gaming">Gaming & Esports</option>
                  <option value="culture">Internet Culture</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Persona Archetype
                </label>
                <select
                  value={newEntityArchetype}
                  onChange={(e) => setNewEntityArchetype(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                >
                  <option value="loyalist">Loyalist (Avid Fan / Defends Craft)</option>
                  <option value="nemesis">Nemesis (Critical / Mocks Slop)</option>
                  <option value="nuanced_critic">Nuanced Critic (Balanced Analysis)</option>
                  <option value="guilty_pleasure">Guilty Pleasure (Affectionate Roaster)</option>
                  <option value="enthusiast">Enthusiast (Hype & Theories)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Sentiment Split (%) — Praise / Analysis / Critique
              </label>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-bold">
                    Praise: {newEntityPraise}%
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={newEntityPraise}
                    onChange={(e) => {
                      const p = Number(e.target.value);
                      setNewEntityPraise(p);
                      const rem = 100 - p;
                      setNewEntityAnalysis(Math.round(rem * 0.6));
                      setNewEntityCritique(rem - Math.round(rem * 0.6));
                    }}
                    className="w-full accent-emerald-500"
                  />
                </div>
                <div>
                  <span className="text-[11px] text-sky-600 dark:text-sky-400 font-bold">
                    Analysis: {newEntityAnalysis}%
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={newEntityAnalysis}
                    onChange={(e) => {
                      const a = Number(e.target.value);
                      setNewEntityAnalysis(a);
                      setNewEntityCritique(Math.max(0, 100 - newEntityPraise - a));
                    }}
                    className="w-full accent-sky-500"
                  />
                </div>
                <div>
                  <span className="text-[11px] text-rose-600 dark:text-rose-400 font-bold">
                    Critique: {newEntityCritique}%
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={newEntityCritique}
                    onChange={(e) => {
                      const c = Number(e.target.value);
                      setNewEntityCritique(c);
                      setNewEntityAnalysis(Math.max(0, 100 - newEntityPraise - c));
                    }}
                    className="w-full accent-rose-500"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Specific Behavioral Directive
              </label>
              <input
                type="text"
                placeholder="e.g. Always praise cinematography and score, but point out pacing drags in act 2."
                value={newEntityRule}
                onChange={(e) => setNewEntityRule(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setIsAddingCustom(false)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateCustomStance}
                disabled={!newEntityName.trim()}
                className="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-sky-600 hover:bg-sky-700 text-white disabled:opacity-50"
              >
                Save Stance
              </button>
            </div>
          </div>
        )}

        {/* Existing Stance Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {stances.length === 0 ? (
            <div className="col-span-full py-8 text-center text-xs text-slate-500 dark:text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
              No entity stances configured yet. Add a quick preset above or create a custom stance.
            </div>
          ) : (
            stances.map((stance, idx) => {
              const praise = stance.sentiment_split?.praise ?? 60;
              const analysis = stance.sentiment_split?.analysis ?? 30;
              const critique = stance.sentiment_split?.critique ?? 10;

              return (
                <div
                  key={`${stance.name}-${idx}`}
                  className={`rounded-xl border transition p-4 space-y-3.5 ${
                    stance.is_active
                      ? "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 shadow-sm"
                      : "opacity-60 border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40"
                  }`}
                >
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-slate-900 dark:text-white">
                          {stance.name}
                        </span>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${getArchetypeBadge(
                            stance.archetype
                          )}`}
                        >
                          {stance.archetype.replace("_", " ")}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-500 dark:text-slate-400">
                        {stance.category}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleToggleStanceActive(idx)}
                        title={stance.is_active ? "Stance active" : "Stance paused"}
                        className={`text-xs px-2 py-1 rounded-md font-semibold border transition ${
                          stance.is_active
                            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                            : "bg-slate-100 dark:bg-slate-800 text-slate-400 border-slate-200 dark:border-slate-700"
                        }`}
                      >
                        {stance.is_active ? "Active" : "Paused"}
                      </button>
                      <button
                        onClick={() => handleDeleteStance(idx)}
                        className="p-1 rounded-md text-slate-400 hover:text-rose-500 transition"
                        title="Delete stance"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Sentiment Ratio Bar */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-[10px] font-semibold text-slate-500 dark:text-slate-400">
                      <span className="text-emerald-600 dark:text-emerald-400">Praise: {praise}%</span>
                      <span className="text-sky-600 dark:text-sky-400">Analysis: {analysis}%</span>
                      <span className="text-rose-600 dark:text-rose-400">Critique: {critique}%</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800 flex overflow-hidden">
                      <div style={{ width: `${praise}%` }} className="bg-emerald-500 transition-all" />
                      <div style={{ width: `${analysis}%` }} className="bg-sky-500 transition-all" />
                      <div style={{ width: `${critique}%` }} className="bg-rose-500 transition-all" />
                    </div>

                    <div className="pt-1 grid grid-cols-3 gap-2">
                      <div>
                        <span className="text-[10px] text-slate-400">Praise</span>
                        <input
                          type="range"
                          min={0}
                          max={100}
                          value={praise}
                          onChange={(e) => handleSplitChange(idx, "praise", Number(e.target.value))}
                          className="w-full accent-emerald-500 h-1"
                        />
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400">Analysis</span>
                        <input
                          type="range"
                          min={0}
                          max={100}
                          value={analysis}
                          onChange={(e) => handleSplitChange(idx, "analysis", Number(e.target.value))}
                          className="w-full accent-sky-500 h-1"
                        />
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400">Critique</span>
                        <input
                          type="range"
                          min={0}
                          max={100}
                          value={critique}
                          onChange={(e) => handleSplitChange(idx, "critique", Number(e.target.value))}
                          className="w-full accent-rose-500 h-1"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Behavioral Rule Directive */}
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                      Behavioral Directive
                    </label>
                    <input
                      type="text"
                      value={stance.behavioral_rule || ""}
                      onChange={(e) => {
                        const next = [...stances];
                        next[idx] = { ...next[idx], behavioral_rule: e.target.value };
                        updateStances(next);
                      }}
                      placeholder="e.g. Always praise practical stunts, lightly tease sound mixing."
                      className="w-full px-2.5 py-1.5 rounded-lg text-xs border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                    />
                  </div>

                  {/* Talking Points Chips */}
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                      Talking Points
                    </label>
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {(stance.talking_points || []).map((tp, tpIdx) => (
                        <span
                          key={tpIdx}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                        >
                          <span>{tp}</span>
                          <button
                            onClick={() => handleRemoveTagFromStance(idx, tpIdx)}
                            className="hover:text-rose-500 text-slate-400"
                          >
                            ×
                          </button>
                        </span>
                      ))}
                    </div>

                    <div className="flex items-center gap-1.5">
                      <input
                        type="text"
                        placeholder="Add theme tag..."
                        value={activeTagInputs[idx] || ""}
                        onChange={(e) =>
                          setActiveTagInputs((prev) => ({ ...prev, [idx]: e.target.value }))
                        }
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            handleAddTagToStance(idx);
                          }
                        }}
                        className="flex-1 px-2 py-1 text-xs rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
                      />
                      <button
                        onClick={() => handleAddTagToStance(idx)}
                        className="p-1 px-2 text-xs rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold"
                      >
                        Add
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 2. MULTILINGUAL CODE-SWITCHING & REGISTER */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 p-5 sm:p-6 shadow-sm space-y-6">
        <div className="flex items-center gap-2.5 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <Languages className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-base text-slate-900 dark:text-white">
              Multilingual Code-Switching & Dialect
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Configure natural Hinglish and Hindi code-switching based on sociolinguistic conversational patterns.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Primary Language
              </label>
              <select
                value={langConfig.primary_language}
                onChange={(e) => updateLangConfig({ primary_language: e.target.value })}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                <option value="en">English (Global Default)</option>
                <option value="hi">Hindi (Devanagari Primary)</option>
              </select>
            </div>

            {/* Hinglish Toggle Switch */}
            <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40">
              <div>
                <div className="text-xs font-bold text-slate-900 dark:text-white">
                  Enable Hinglish Code-Switching
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Allow natural blend of English and Hindi for Indian pop-culture and banter.
                </div>
              </div>
              <button
                type="button"
                onClick={() => updateLangConfig({ enable_hinglish: !langConfig.enable_hinglish })}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  langConfig.enable_hinglish ? "bg-emerald-500" : "bg-slate-300 dark:bg-slate-700"
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    langConfig.enable_hinglish ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>

            {/* Devanagari Hindi Toggle Switch */}
            <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40">
              <div>
                <div className="text-xs font-bold text-slate-900 dark:text-white">
                  Devanagari Hindi Script Replies
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Reply in native Hindi script when the parent post is written in Devanagari.
                </div>
              </div>
              <button
                type="button"
                onClick={() => updateLangConfig({ enable_hindi_script: !langConfig.enable_hindi_script })}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  langConfig.enable_hindi_script ? "bg-emerald-500" : "bg-slate-300 dark:bg-slate-700"
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    langConfig.enable_hindi_script ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Code-Switching Strategy Mode
              </label>
              <div className="space-y-2">
                {[
                  {
                    id: "mirror_and_punchline",
                    title: "Mirror & Punchline (Sociolinguistic Best Practice)",
                    desc: "State technical premise in English; deliver comedic punchline, shock, or evaluative reaction in natural Hinglish.",
                  },
                  {
                    id: "mirror_only",
                    title: "Mirror Only",
                    desc: "Only code-switch if the parent tweet or active discussion specifically contains Hindi/Hinglish.",
                  },
                  {
                    id: "full_bilingual",
                    title: "Fluid Bilingual",
                    desc: "Freely switch between English and Hinglish across all standalone posts and replies.",
                  },
                ].map((mode) => (
                  <label
                    key={mode.id}
                    className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition ${
                      langConfig.hinglish_mode === mode.id
                        ? "border-sky-500 bg-sky-50/40 dark:bg-sky-950/20"
                        : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/40 hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    <input
                      type="radio"
                      name="hinglish_mode"
                      value={mode.id}
                      checked={langConfig.hinglish_mode === mode.id}
                      onChange={() => updateLangConfig({ hinglish_mode: mode.id })}
                      className="mt-0.5 accent-sky-600"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-900 dark:text-white">
                        {mode.title}
                      </div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        {mode.desc}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Slang Register & Vocabulary Tier
              </label>
              <select
                value={langConfig.slang_register}
                onChange={(e) => updateLangConfig({ slang_register: e.target.value })}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                <option value="urban_buff">Urban Creator Buff (yaar, sahi mein, scene kya hai, legit, bhai)</option>
                <option value="casual_desi">Casual Street Desi (arre bhai, kya baat hai, matlab kuch bhi, bawaal)</option>
                <option value="minimal">Minimal / Subtle Tone Markers (rare 'yaar', 'sahi hai')</option>
              </select>
            </div>

            {/* Live Example Simulation */}
            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-xs space-y-1.5">
              <div className="text-[10px] font-bold text-sky-600 dark:text-sky-400 uppercase tracking-wider">
                Live Output Preview ({langConfig.slang_register})
              </div>
              <p className="italic text-slate-700 dark:text-slate-300">
                &ldquo;The camera sensor hardware is flagship tier, par aggressive AI over-sharpening ki wajah se sab oil painting lag raha hai yaar.&rdquo;
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 3. EXPRESSIVENESS, EMOJI GRAMMAR & MEDIA */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 p-5 sm:p-6 shadow-sm space-y-6">
        <div className="flex items-center gap-2.5 border-b border-slate-200 dark:border-slate-800 pb-4">
          <div className="p-2 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <Smile className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-base text-slate-900 dark:text-white">
              Semantic Emojis & Media Rules
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Emojis are paralinguistic tone markers (irony, exhaustion, deadpan wit) — never locked to fixed topic categories.
            </p>
          </div>
        </div>

        {/* Highlight Alert Box */}
        <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-900/40 bg-amber-50/50 dark:bg-amber-950/20 text-xs text-amber-900 dark:text-amber-300 space-y-1">
          <div className="font-bold flex items-center gap-1.5">
            <Flame className="w-4 h-4 text-amber-500" />
            <span>Anti-Slop Emoji Philosophy</span>
          </div>
          <p className="text-[11px] leading-relaxed opacity-90">
            Humans on X use emojis as subtext, irony, and punctuation (💀, 😭, 🫠, 👀, ✨, 🫡). We strictly ban topic-labeling emojis (e.g. NEVER use 🍿 for cinema or 🤖 for tech). Zero emojis is completely natural for dry, cynical, or analytical takes.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Emoji Mode
              </label>
              <div className="space-y-2">
                {[
                  {
                    id: "contextual_tone",
                    title: "Contextual Tone Markers (Recommended)",
                    desc: "Emojis function as emotional tone markers (irony, shock, fatigue, dry humor). 0-2 max.",
                  },
                  {
                    id: "minimal",
                    title: "Minimal",
                    desc: "Very rare, subtle punctuation (0-1 max). Most posts have zero emojis.",
                  },
                  {
                    id: "none",
                    title: "Strict Zero Emojis",
                    desc: "Strictly ban all emojis from generation for 100% clean typography.",
                  },
                ].map((mode) => (
                  <label
                    key={mode.id}
                    className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition ${
                      expConfig.emoji_mode === mode.id
                        ? "border-sky-500 bg-sky-50/40 dark:bg-sky-950/20"
                        : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/40 hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    <input
                      type="radio"
                      name="emoji_mode"
                      value={mode.id}
                      checked={expConfig.emoji_mode === mode.id}
                      onChange={() => updateExpConfig({ emoji_mode: mode.id })}
                      className="mt-0.5 accent-sky-600"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-900 dark:text-white">
                        {mode.title}
                      </div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        {mode.desc}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40">
              <div>
                <div className="text-xs font-bold text-slate-900 dark:text-white">
                  Allow Zero Emojis (Authentic Human Default)
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Allow 0 emojis when writing deadpan or cynical takes.
                </div>
              </div>
              <button
                type="button"
                onClick={() => updateExpConfig({ allow_zero_emojis: !expConfig.allow_zero_emojis })}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  expConfig.allow_zero_emojis ? "bg-emerald-500" : "bg-slate-300 dark:bg-slate-700"
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    expConfig.allow_zero_emojis ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
          </div>

          <div className="space-y-5">
            <div>
              <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                <span>Max Emojis Per Post / Reply</span>
                <span className="font-bold text-sky-600 dark:text-sky-400">{expConfig.max_emojis} Emojis</span>
              </div>
              <input
                type="range"
                min={0}
                max={3}
                value={expConfig.max_emojis}
                onChange={(e) => updateExpConfig({ max_emojis: Number(e.target.value) })}
                className="w-full accent-sky-500"
              />
              <div className="flex justify-between text-[10px] text-slate-400 mt-1">
                <span>0 (None)</span>
                <span>1</span>
                <span>2 (Recommended)</span>
                <span>3</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                <span>Meme / Reaction GIF Attachment Rate</span>
                <span className="font-bold text-amber-600 dark:text-amber-400">{expConfig.reply_meme_rate}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={expConfig.reply_meme_rate}
                onChange={(e) => updateExpConfig({ reply_meme_rate: Number(e.target.value) })}
                className="w-full accent-amber-500"
              />
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                Target probability of attaching a relevant reaction GIF or meme when comedic timing fits.
              </p>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                <span>Thread Visuals & Media Rate</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400">{expConfig.thread_media_rate}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={expConfig.thread_media_rate}
                onChange={(e) => updateExpConfig({ thread_media_rate: Number(e.target.value) })}
                className="w-full accent-emerald-500"
              />
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                Target frequency of attaching screenshots, diagrams, or cinema stills to long-form threads.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
