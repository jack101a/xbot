"use client";

import React, { useState, useEffect } from "react";
import {
  Brain,
  BookOpen,
  Sparkles,
  Sliders,
  Plus,
  Trash2,
  Save,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  FileText,
  Tag,
  ShieldAlert,
  ArrowRight,
  Upload
} from "lucide-react";
import { Profile, api } from "@/lib/api";

interface PersonaMemoryTabProps {
  profileId: string;
  selectedProfile: Profile;
  onRefresh: () => void;
}

export function PersonaMemoryTab({
  profileId,
  selectedProfile,
  onRefresh
}: PersonaMemoryTabProps) {
  const [subSection, setSubSection] = useState<"identity" | "topics" | "diary" | "learned">("identity");

  // Persona Data State
  const [persona, setPersona] = useState<any>(null);
  const [learnedState, setLearnedState] = useState<any>(null);
  const [diaryList, setDiaryList] = useState<any[]>([]);
  const [selectedDiaryDate, setSelectedDiaryDate] = useState<string | null>(null);
  const [diaryContent, setDiaryContent] = useState<string>("");

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reflecting, setReflecting] = useState(false);
  const [msg, setMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Character card import
  const [showCardModal, setShowCardModal] = useState(false);
  const [cardJson, setCardJson] = useState("");
  const [importingCard, setImportingCard] = useState(false);

  // New tag inputs
  const [newPrimaryTopic, setNewPrimaryTopic] = useState("");
  const [newAntiTopic, setNewAntiTopic] = useState("");

  const loadData = async () => {
    if (!profileId) return;
    setLoading(true);
    try {
      const [pData, lData, dData] = await Promise.all([
        api.getProfilePersona(profileId),
        api.getProfileLearnedState(profileId),
        api.getProfileDiary(profileId, 20)
      ]);
      setPersona(pData || {});
      setLearnedState(lData || {});
      setDiaryList(dData || []);
      if (dData && dData.length > 0 && !selectedDiaryDate) {
        setSelectedDiaryDate(dData[0].date);
        setDiaryContent(dData[0].content || "");
      }
    } catch (err: any) {
      console.error("Failed to load persona/memory data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [profileId]);

  const handleSavePersona = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await api.updateProfilePersona(profileId, persona);
      setMsg({ type: "success", text: "Persona identity & rules saved successfully!" });
      onRefresh();
    } catch (err: any) {
      setMsg({ type: "error", text: err.message || "Failed to save persona." });
    } finally {
      setSaving(false);
    }
  };

  const handleTriggerReflection = async () => {
    setReflecting(true);
    setMsg(null);
    try {
      await api.triggerProfileReflection(profileId);
      setMsg({ type: "success", text: "Cognitive reflection triggered! Reviewing recent posts and updating learned habits." });
      await loadData();
    } catch (err: any) {
      setMsg({ type: "error", text: err.message || "Failed to trigger reflection." });
    } finally {
      setReflecting(false);
    }
  };

  const handleImportCard = async () => {
    if (!cardJson.trim()) return;
    setImportingCard(true);
    setMsg(null);
    try {
      await api.importProfileCard(profileId, cardJson, true);
      setMsg({ type: "success", text: "Character card imported and merged into persona!" });
      setShowCardModal(false);
      setCardJson("");
      await loadData();
      onRefresh();
    } catch (err: any) {
      setMsg({ type: "error", text: err.message || "Failed to import character card." });
    } finally {
      setImportingCard(false);
    }
  };

  const handleAddPrimaryTopic = () => {
    if (!newPrimaryTopic.trim()) return;
    const current = persona?.interests?.primary || [];
    setPersona({
      ...persona,
      interests: {
        ...persona?.interests,
        primary: [...current, newPrimaryTopic.trim()]
      }
    });
    setNewPrimaryTopic("");
  };

  const handleRemovePrimaryTopic = (idx: number) => {
    const current = [...(persona?.interests?.primary || [])];
    current.splice(idx, 1);
    setPersona({
      ...persona,
      interests: {
        ...persona?.interests,
        primary: current
      }
    });
  };

  const handleAddAntiTopic = () => {
    if (!newAntiTopic.trim()) return;
    const current = persona?.interests?.will_not_discuss || [];
    setPersona({
      ...persona,
      interests: {
        ...persona?.interests,
        will_not_discuss: [...current, newAntiTopic.trim()]
      }
    });
    setNewAntiTopic("");
  };

  const handleRemoveAntiTopic = (idx: number) => {
    const current = [...(persona?.interests?.will_not_discuss || [])];
    current.splice(idx, 1);
    setPersona({
      ...persona,
      interests: {
        ...persona?.interests,
        will_not_discuss: current
      }
    });
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Sub-Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Brain className="w-5 h-5 text-indigo-500" />
            <span>AI Persona & Cognitive Memory</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Configure authentic tone of voice, niche boundary guardrails, daily diary logs, and auto-learned heuristics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCardModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 transition shadow-sm"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Import Character Card</span>
          </button>

          <button
            onClick={handleSavePersona}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-600/20 transition disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? "Saving..." : "Save Persona"}</span>
          </button>
        </div>
      </div>

      {/* Notification Message */}
      {msg && (
        <div
          className={`p-4 rounded-xl flex items-center justify-between border ${
            msg.type === "success"
              ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
              : "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300"
          }`}
        >
          <div className="flex items-center gap-3">
            {msg.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
            )}
            <span className="text-sm font-medium">{msg.text}</span>
          </div>
          <button onClick={() => setMsg(null)} className="text-xs font-semibold underline hover:opacity-75">
            Dismiss
          </button>
        </div>
      )}

      {/* Sub Tab Navigation */}
      <div className="flex items-center gap-2 p-1 rounded-xl bg-slate-100 dark:bg-slate-800/60 max-w-xl">
        <button
          onClick={() => setSubSection("identity")}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition ${
            subSection === "identity"
              ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
              : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          Identity & Voice
        </button>
        <button
          onClick={() => setSubSection("topics")}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition ${
            subSection === "topics"
              ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
              : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          Topic Boundaries
        </button>
        <button
          onClick={() => setSubSection("diary")}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition ${
            subSection === "diary"
              ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
              : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          Daily Diary
        </button>
        <button
          onClick={() => setSubSection("learned")}
          className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition ${
            subSection === "learned"
              ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
              : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
          }`}
        >
          Learned Memory
        </button>
      </div>

      {/* Sub-Section 1: Identity & Voice */}
      {subSection === "identity" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-4">
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

          <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-4">
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
                value={Array.isArray(persona?.goals?.short_term) ? persona.goals.short_term.join(", ") : ""}
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
                value={Array.isArray(persona?.goals?.content_pillars) ? persona.goals.content_pillars.join(", ") : ""}
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
      )}

      {/* Sub-Section 2: Topic Boundaries */}
      {subSection === "topics" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Primary Topics */}
          <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-4">
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
                className="p-2 rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 transition"
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

          {/* Anti-Topics / Taboos */}
          <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-500" />
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">Strict Anti-Topics (Taboos)</h3>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              The AI bot will NEVER post, reply to, or engage with these forbidden topics.
            </p>

            <div className="flex items-center gap-2">
              <input
                type="text"
                value={newAntiTopic}
                onChange={(e) => setNewAntiTopic(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAddAntiTopic()}
                placeholder="Add forbidden topic (e.g. Politics, Celebrity Gossip, Meme Coins)..."
                className="flex-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
              <button
                onClick={handleAddAntiTopic}
                className="p-2 rounded-xl bg-rose-600 text-white hover:bg-rose-700 transition"
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
      )}

      {/* Sub-Section 3: Daily Diary */}
      {subSection === "diary" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-2">
            <h3 className="font-bold text-xs uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-3">
              Diary Entries Log
            </h3>
            {diaryList.length > 0 ? (
              <div className="space-y-1">
                {diaryList.map((d) => (
                  <button
                    key={d.date}
                    onClick={() => {
                      setSelectedDiaryDate(d.date);
                      setDiaryContent(d.content || "");
                    }}
                    className={`w-full flex items-center justify-between p-2.5 rounded-xl text-xs font-semibold transition text-left ${
                      selectedDiaryDate === d.date
                        ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                        : "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <BookOpen className="w-3.5 h-3.5" />
                      <span>{d.date}</span>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 opacity-60" />
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 py-6 text-center">No diary entries found.</p>
            )}
          </div>

          <div className="lg:col-span-2 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-500" />
                <span>Diary for {selectedDiaryDate || "Today"}</span>
              </h3>
              <span className="text-[11px] text-slate-400">Markdown format</span>
            </div>

            <div className="prose dark:prose-invert max-w-none text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap font-mono bg-slate-50 dark:bg-slate-950/60 p-4 rounded-xl border border-slate-200 dark:border-slate-800 max-h-96 overflow-y-auto">
              {diaryContent || "Select a diary date on the left to read the AI persona's reflections and daily journal."}
            </div>
          </div>
        </div>
      )}

      {/* Sub-Section 4: Learned Memory */}
      {subSection === "learned" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between p-5 rounded-2xl border border-indigo-200 dark:border-indigo-800/60 bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-transparent">
            <div>
              <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-500" />
                <span>Performance-Driven Subconscious Reflection</span>
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">
                Reflections processed: {learnedState?.reflection_count || 0} &bull; Last updated:{" "}
                {learnedState?.last_reflected_at ? new Date(learnedState.last_reflected_at).toLocaleString() : "Never"}
              </p>
            </div>

            <button
              onClick={handleTriggerReflection}
              disabled={reflecting}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${reflecting ? "animate-spin" : ""}`} />
              <span>{reflecting ? "Reflecting..." : "Trigger Reflection Now"}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Behavioral Adaptations */}
            <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-3">
              <h4 className="font-bold text-xs uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                Behavioral Adaptations
              </h4>
              <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
                {(learnedState?.characteristics?.behavioral_adaptations || []).map((item: string, i: number) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-indigo-500 font-bold">&bull;</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              {(!learnedState?.characteristics?.behavioral_adaptations || learnedState.characteristics.behavioral_adaptations.length === 0) && (
                <p className="text-xs text-slate-400 italic">No behavioral adaptations synthesized yet.</p>
              )}
            </div>

            {/* Emerging Topics */}
            <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-3">
              <h4 className="font-bold text-xs uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                Discovered High-ROI Topics
              </h4>
              <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
                {(learnedState?.interests?.emerging_topics || []).map((item: string, i: number) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-emerald-500 font-bold">&bull;</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              {(!learnedState?.interests?.emerging_topics || learnedState.interests.emerging_topics.length === 0) && (
                <p className="text-xs text-slate-400 italic">No emerging topics discovered yet.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Import Character Card Modal */}
      {showCardModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Import Character Card / JSON</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Paste your persona character card JSON (e.g. SillyTavern format or custom YAML/JSON) to automatically parse voice, style, and identity.
            </p>

            <textarea
              rows={8}
              value={cardJson}
              onChange={(e) => setCardJson(e.target.value)}
              placeholder="Paste JSON or character card text here..."
              className="w-full p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowCardModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleImportCard}
                disabled={importingCard}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white transition disabled:opacity-50"
              >
                {importingCard ? "Importing..." : "Parse & Import"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
