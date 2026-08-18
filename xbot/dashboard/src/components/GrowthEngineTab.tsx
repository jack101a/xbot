"use client";

import React, { useState, useEffect } from "react";
import { 
  Crosshair, 
  Sparkles, 
  TrendingUp, 
  Vote, 
  Plus, 
  Trash2, 
  RefreshCw, 
  CheckCircle, 
  AlertCircle,
  ExternalLink,
  Sliders,
  Send,
  Zap,
  Layers,
  ArrowRight
} from "lucide-react";
import { api, Profile } from "@/lib/api";

interface TargetKOL {
  handle: string;
  category: string;
  priority: "high" | "medium" | "low";
  preferred_angle: "contrarian" | "framework" | "witty" | "data" | "insight";
}

interface HookCandidate {
  archetype: string;
  hook_text: string;
  score: number;
  reasoning: string;
}

export function GrowthEngineTab({ 
  profileId, 
  selectedProfile 
}: { 
  profileId: string; 
  selectedProfile: Profile; 
}) {
  const [subTab, setSubTab] = useState<"sniper" | "hooks" | "polls" | "trends">("sniper");
  
  // Persona & Target KOL State
  const [personaData, setPersonaData] = useState<any>(null);
  const [targetKols, setTargetKols] = useState<TargetKOL[]>([]);
  const [newKolHandle, setNewKolHandle] = useState("");
  const [newKolCategory, setNewKolCategory] = useState("tech_ai");
  const [newKolPriority, setNewKolPriority] = useState<"high" | "medium" | "low">("high");
  const [newKolAngle, setNewKolAngle] = useState<"contrarian" | "framework" | "witty" | "data" | "insight">("insight");
  const [savingKols, setSavingKols] = useState(false);
  const [kolActionMsg, setKolActionMsg] = useState<string | null>(null);

  // Hook Optimizer Interactive State
  const [hookDraftText, setHookDraftText] = useState("");
  const [hookTopic, setHookTopic] = useState("");
  const [hookOptimizing, setHookOptimizing] = useState(false);
  const [hookCandidates, setHookCandidates] = useState<HookCandidate[]>([]);
  const [winningHook, setWinningHook] = useState<HookCandidate | null>(null);
  const [optimizedPostResult, setOptimizedPostResult] = useState<string | null>(null);

  // Poll Generator Interactive State
  const [pollTopic, setPollTopic] = useState("");
  const [generatingPoll, setGeneratingPoll] = useState(false);
  const [generatedPoll, setGeneratedPoll] = useState<{
    question: string;
    options: string[];
    duration_days: number;
    context_hook?: string;
    reasoning?: string;
  } | null>(null);
  const [stagingPoll, setStagingPoll] = useState(false);
  const [pollSuccessMsg, setPollSuccessMsg] = useState<string | null>(null);

  // Trend Radar State
  const [trendsList, setTrendsList] = useState<any[]>([]);
  const [loadingTrends, setLoadingTrends] = useState(false);

  // Load Persona Data
  useEffect(() => {
    async function loadData() {
      if (!profileId) return;
      try {
        const p = await api.getProfilePersona(profileId);
        setPersonaData(p);
        if (p?.target_kols) {
          setTargetKols(p.target_kols);
        }
      } catch (err) {
        console.error("Failed to load persona for growth engine", err);
      }
    }
    loadData();
  }, [profileId]);

  // Handle Add KOL
  const handleAddKol = async () => {
    if (!newKolHandle.trim()) return;
    const cleanHandle = newKolHandle.trim().replace(/^@/, "");
    const updated = [
      ...targetKols.filter(k => k.handle.toLowerCase() !== cleanHandle.toLowerCase()),
      {
        handle: cleanHandle,
        category: newKolCategory,
        priority: newKolPriority,
        preferred_angle: newKolAngle
      }
    ];
    setTargetKols(updated);
    setNewKolHandle("");
    await saveTargetKols(updated);
  };

  // Handle Remove KOL
  const handleRemoveKol = async (handle: string) => {
    const updated = targetKols.filter(k => k.handle.toLowerCase() !== handle.toLowerCase());
    setTargetKols(updated);
    await saveTargetKols(updated);
  };

  // Save KOL list to persona
  const saveTargetKols = async (kols: TargetKOL[]) => {
    setSavingKols(true);
    setKolActionMsg(null);
    try {
      const updatedPersona = {
        ...(personaData || {}),
        target_kols: kols
      };
      await api.updateProfilePersona(profileId, updatedPersona);
      setPersonaData(updatedPersona);
      setKolActionMsg("Target KOL registry updated successfully!");
      setTimeout(() => setKolActionMsg(null), 3500);
    } catch (err: any) {
      alert("Failed to save KOL list: " + err.message);
    } finally {
      setSavingKols(false);
    }
  };

  // Run Hook Optimizer Simulation
  const handleOptimizeHook = async () => {
    if (!hookDraftText.trim() && !hookTopic.trim()) return;
    setHookOptimizing(true);
    setOptimizedPostResult(null);
    setHookCandidates([]);
    try {
      // Simulate/Trigger hook generation
      const mockCandidates: HookCandidate[] = [
        {
          archetype: "curiosity_gap",
          hook_text: `99% of people build ${hookTopic || "agents"} completely wrong. Here is the 1 flaw:`,
          score: 9.4,
          reasoning: "High intrigue, challenges common consensus, forces scroll pause."
        },
        {
          archetype: "contrarian",
          hook_text: `Why ${hookTopic || "this trend"} is actually a massive trap:`,
          score: 8.8,
          reasoning: "Polarizing statement triggering debate comments."
        },
        {
          archetype: "framework_breakdown",
          hook_text: `We stress-tested ${hookTopic || "this method"}. Here are the 3 hard takeaways:`,
          score: 8.2,
          reasoning: "High bookmark and share potential."
        },
        {
          archetype: "story_relatable",
          hook_text: `6 months ago, we made a huge mistake with ${hookTopic || "our system"}. What we learned:`,
          score: 7.9,
          reasoning: "Personal vulnerability drives organic empathy."
        }
      ];
      setHookCandidates(mockCandidates);
      setWinningHook(mockCandidates[0]);
      setOptimizedPostResult(`${mockCandidates[0].hook_text}\n\n${hookDraftText.trim() || "1. Focus on deterministic loops.\n2. Keep context lean.\n3. Verify before completion."}`);
    } finally {
      setHookOptimizing(false);
    }
  };

  // Generate Interactive Poll
  const handleGeneratePoll = async () => {
    setGeneratingPoll(true);
    setPollSuccessMsg(null);
    try {
      const topic = pollTopic.trim() || "AI Agents in Production";
      setGeneratedPoll({
        question: `Will autonomous AI agents replace 50% of junior dev workflows by 2027?`,
        options: [
          "Yes, easily",
          "No, mostly hype",
          "Already happening",
          "See results"
        ],
        duration_days: 1,
        context_hook: `The shift to autonomous agent architecture is moving faster than expected.`,
        reasoning: "Polarizing prediction dividing developers, prompting high comment volume."
      });
    } finally {
      setGeneratingPoll(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      {/* HEADER BANNER */}
      <div className="bg-gradient-to-r from-blue-900/30 via-indigo-900/20 to-purple-900/30 border border-blue-500/30 rounded-xl p-6 relative overflow-hidden backdrop-blur-md">
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-2 text-blue-400 font-semibold text-xs uppercase tracking-wider mb-1">
              <Zap size={14} className="animate-pulse text-blue-400" />
              Algorithmic Growth Engine
            </div>
            <h2 className="text-xl font-bold text-app-text flex items-center gap-2">
              Audience & Reach Multipliers
            </h2>
            <p className="text-sm text-app-text/60 mt-1 max-w-2xl">
              Exploit the X recommendation algorithm: hijack traffic with Sniper Replies on top KOLs, maximize dwell time with Viral Hooks, and drive active click signals with Native Polls.
            </p>
          </div>
          <div className="flex items-center gap-2 bg-black/40 border border-white/10 px-3 py-2 rounded-lg text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="text-app-text/80 font-medium">9.0x Reply Multiplier Active</span>
          </div>
        </div>
      </div>

      {/* SUB-TABS */}
      <div className="flex gap-2 border-b border-app-border/[0.08] pb-2">
        {[
          { id: "sniper", label: `KOL Sniper (${targetKols.length})`, icon: <Crosshair size={15} /> },
          { id: "hooks", label: "Viral Hook Optimizer", icon: <Sparkles size={15} /> },
          { id: "polls", label: "Interactive Poll Studio", icon: <Vote size={15} /> },
          { id: "trends", label: "Trend & News Radar", icon: <TrendingUp size={15} /> },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setSubTab(tab.id as any)}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
              subTab === tab.id 
                ? "bg-blue-600/20 text-blue-400 border border-blue-500/40 shadow-sm" 
                : "text-app-text/50 hover:text-app-text/80 hover:bg-white/[0.02]"
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* 1. KOL SNIPER SUBTAB */}
      {subTab === "sniper" && (
        <div className="space-y-6">
          <div className="bg-app-card border border-app-border/[0.08] rounded-xl p-6 space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-base font-bold text-app-text flex items-center gap-2">
                  <Crosshair size={18} className="text-blue-400" />
                  Target Key Opinion Leaders (KOLs)
                </h3>
                <p className="text-xs text-app-text/50 mt-0.5">
                  XBot watches these accounts every 120s and executes top-3 replies within 180s to siphon viral reach.
                </p>
              </div>
              {kolActionMsg && (
                <div className="text-xs text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-3 py-1.5 rounded-md flex items-center gap-1.5">
                  <CheckCircle size={14} /> {kolActionMsg}
                </div>
              )}
            </div>

            {/* ADD KOL FORM */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 bg-black/20 p-4 rounded-lg border border-white/5">
              <div className="md:col-span-2">
                <label className="text-[11px] font-semibold text-app-text/60 uppercase">X Handle</label>
                <input
                  type="text"
                  placeholder="e.g. elonmusk, sama, ylecun"
                  value={newKolHandle}
                  onChange={(e) => setNewKolHandle(e.target.value)}
                  className="w-full bg-black/40 border border-app-border/[0.12] rounded-md px-3 py-1.5 text-xs text-app-text focus:border-blue-500 focus:outline-none mt-1"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-app-text/60 uppercase">Priority</label>
                <select
                  value={newKolPriority}
                  onChange={(e: any) => setNewKolPriority(e.target.value)}
                  className="w-full bg-black/40 border border-app-border/[0.12] rounded-md px-3 py-1.5 text-xs text-app-text focus:border-blue-500 focus:outline-none mt-1"
                >
                  <option value="high">High Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="low">Low Priority</option>
                </select>
              </div>
              <div>
                <label className="text-[11px] font-semibold text-app-text/60 uppercase">Strategy Angle</label>
                <select
                  value={newKolAngle}
                  onChange={(e: any) => setNewKolAngle(e.target.value)}
                  className="w-full bg-black/40 border border-app-border/[0.12] rounded-md px-3 py-1.5 text-xs text-app-text focus:border-blue-500 focus:outline-none mt-1"
                >
                  <option value="insight">Insightful Add</option>
                  <option value="contrarian">Contrarian Debate</option>
                  <option value="framework">3-Bullet Summary</option>
                  <option value="witty">Witty Humor</option>
                  <option value="data">Data / Stats</option>
                </select>
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleAddKol}
                  disabled={!newKolHandle.trim() || savingKols}
                  className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold py-2 px-3 rounded-md flex items-center justify-center gap-1.5 transition-all shadow-md"
                >
                  <Plus size={14} /> Add Target
                </button>
              </div>
            </div>

            {/* KOL TABLE */}
            <div className="border border-app-border/[0.08] rounded-lg overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-white/[0.02] border-b border-app-border/[0.08] text-app-text/50 font-semibold uppercase text-[10px]">
                  <tr>
                    <th className="py-2.5 px-4">Target Handle</th>
                    <th className="py-2.5 px-4">Category</th>
                    <th className="py-2.5 px-4">Priority</th>
                    <th className="py-2.5 px-4">Preferred Response Angle</th>
                    <th className="py-2.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-app-border/[0.04]">
                  {targetKols.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-app-text/40 italic">
                        No target KOLs configured yet. Add your first influencer above to start sniping!
                      </td>
                    </tr>
                  ) : (
                    targetKols.map((kol) => (
                      <tr key={kol.handle} className="hover:bg-white/[0.01] transition-colors">
                        <td className="py-3 px-4 font-semibold text-app-text flex items-center gap-2">
                          <span className="text-blue-400">@{kol.handle}</span>
                          <a 
                            href={`https://x.com/${kol.handle}`} 
                            target="_blank" 
                            rel="noreferrer"
                            className="text-app-text/30 hover:text-app-text/70"
                          >
                            <ExternalLink size={12} />
                          </a>
                        </td>
                        <td className="py-3 px-4 text-app-text/70">{kol.category}</td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            kol.priority === 'high' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                            kol.priority === 'medium' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                            'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                          }`}>
                            {kol.priority}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-purple-500/20 text-purple-300 border border-purple-500/30">
                            {kol.preferred_angle}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => handleRemoveKol(kol.handle)}
                            className="p-1 text-app-text/40 hover:text-rose-400 hover:bg-rose-500/10 rounded transition-colors"
                            title="Remove Target"
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 2. VIRAL HOOK OPTIMIZER SUBTAB */}
      {subTab === "hooks" && (
        <div className="space-y-6">
          <div className="bg-app-card border border-app-border/[0.08] rounded-xl p-6 space-y-5">
            <div>
              <h3 className="text-base font-bold text-app-text flex items-center gap-2">
                <Sparkles size={18} className="text-purple-400" />
                Viral Hook Multi-Generator & Scorer
              </h3>
              <p className="text-xs text-app-text/50 mt-0.5">
                Generate 4 scroll-stopping opening archetypes for any topic and evaluate dwell-time scores.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-3">
                <div>
                  <label className="text-[11px] font-semibold text-app-text/60 uppercase">Topic / Narrative</label>
                  <input
                    type="text"
                    placeholder="e.g. Autonomous AI Agents, Python Async, Creator Monetization"
                    value={hookTopic}
                    onChange={(e) => setHookTopic(e.target.value)}
                    className="w-full bg-black/40 border border-app-border/[0.12] rounded-md px-3 py-2 text-xs text-app-text focus:border-purple-500 focus:outline-none mt-1"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-app-text/60 uppercase">Draft Body / Key Points</label>
                  <textarea
                    rows={4}
                    placeholder="Enter the core points or body text you want to convey..."
                    value={hookDraftText}
                    onChange={(e) => setHookDraftText(e.target.value)}
                    className="w-full bg-black/40 border border-app-border/[0.12] rounded-md px-3 py-2 text-xs text-app-text focus:border-purple-500 focus:outline-none mt-1 resize-none"
                  />
                </div>
                <button
                  onClick={handleOptimizeHook}
                  disabled={hookOptimizing || (!hookTopic.trim() && !hookDraftText.trim())}
                  className="w-full bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-semibold py-2.5 px-4 rounded-md flex items-center justify-center gap-2 transition-all shadow-md"
                >
                  <Sparkles size={15} />
                  {hookOptimizing ? "Scoring 4 Hook Archetypes..." : "Generate & Score Viral Hooks"}
                </button>
              </div>

              {/* RESULTS PREVIEW */}
              <div className="bg-black/30 border border-white/5 rounded-lg p-4 space-y-3">
                <div className="text-xs font-semibold text-app-text/70 flex items-center justify-between">
                  <span>Archetype Candidates</span>
                  {winningHook && (
                    <span className="text-emerald-400 font-mono text-[10px]">
                      Top Score: {winningHook.score}/10
                    </span>
                  )}
                </div>

                {hookCandidates.length === 0 ? (
                  <div className="h-44 flex flex-col items-center justify-center text-center text-app-text/40 text-xs italic">
                    Enter a topic and click generate to test 4 hook formulas.
                  </div>
                ) : (
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {hookCandidates.map((c, idx) => (
                      <div 
                        key={idx}
                        onClick={() => {
                          setWinningHook(c);
                          setOptimizedPostResult(`${c.hook_text}\n\n${hookDraftText.trim()}`);
                        }}
                        className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                          winningHook?.archetype === c.archetype
                            ? "bg-purple-950/40 border-purple-500/50 shadow-sm"
                            : "bg-white/[0.02] border-white/5 hover:border-white/10"
                        }`}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-[10px] font-bold uppercase text-purple-300">
                            {c.archetype.replace('_', ' ')}
                          </span>
                          <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/50 px-1.5 py-0.5 rounded border border-emerald-500/20">
                            ★ {c.score}/10
                          </span>
                        </div>
                        <p className="text-app-text font-medium">{c.hook_text}</p>
                        <p className="text-[10px] text-app-text/40 mt-1">{c.reasoning}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* FULL POST PREVIEW */}
            {optimizedPostResult && (
              <div className="mt-4 p-4 rounded-lg bg-black/40 border border-purple-500/30 space-y-2">
                <div className="text-xs font-semibold text-purple-300 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle size={14} /> Dwell-Optimized Post Output
                </div>
                <pre className="text-xs text-app-text whitespace-pre-wrap font-sans bg-black/60 p-3 rounded border border-white/5">
                  {optimizedPostResult}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. INTERACTIVE POLL STUDIO SUBTAB */}
      {subTab === "polls" && (
        <div className="space-y-6">
          <div className="bg-app-card border border-app-border/[0.08] rounded-xl p-6 space-y-5">
            <div>
              <h3 className="text-base font-bold text-app-text flex items-center gap-2">
                <Vote size={18} className="text-indigo-400" />
                Interactive Niche Poll Studio
              </h3>
              <p className="text-xs text-app-text/50 mt-0.5">
                Generate debate-provoking polls that force click interactions and algorithmic signal boosts.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-3">
                <div>
                  <label className="text-[11px] font-semibold text-app-text/60 uppercase">Niche / Debate Theme</label>
                  <input
                    type="text"
                    placeholder="e.g. AI vs Human Devs, TypeScript vs Python, Open Source LLMs"
                    value={pollTopic}
                    onChange={(e) => setPollTopic(e.target.value)}
                    className="w-full bg-black/40 border border-app-border/[0.12] rounded-md px-3 py-2 text-xs text-app-text focus:border-indigo-500 focus:outline-none mt-1"
                  />
                </div>
                <button
                  onClick={handleGeneratePoll}
                  disabled={generatingPoll}
                  className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold py-2.5 px-4 rounded-md flex items-center justify-center gap-2 transition-all shadow-md"
                >
                  <Vote size={15} />
                  {generatingPoll ? "Synthesizing Poll Choices..." : "Generate High-Engagement Poll"}
                </button>
              </div>

              {/* POLL PREVIEW */}
              <div className="bg-black/30 border border-white/5 rounded-lg p-4 space-y-3">
                <div className="text-xs font-semibold text-app-text/70">
                  X Platform Poll Preview (≤25 chars per option)
                </div>

                {!generatedPoll ? (
                  <div className="h-44 flex flex-col items-center justify-center text-center text-app-text/40 text-xs italic">
                    Generate a poll to preview interactive voting cards.
                  </div>
                ) : (
                  <div className="space-y-3 bg-black/40 p-4 rounded-lg border border-indigo-500/30">
                    {generatedPoll.context_hook && (
                      <p className="text-xs text-app-text/80">{generatedPoll.context_hook}</p>
                    )}
                    <p className="text-sm font-bold text-app-text">{generatedPoll.question}</p>
                    <div className="space-y-1.5">
                      {generatedPoll.options.map((opt, idx) => (
                        <div key={idx} className="bg-white/5 border border-white/10 px-3 py-2 rounded-md text-xs font-medium text-app-text flex justify-between">
                          <span>{opt}</span>
                          <span className="text-[10px] text-app-text/40 font-mono">{opt.length}/25</span>
                        </div>
                      ))}
                    </div>
                    <div className="text-[10px] text-app-text/40 flex justify-between pt-1">
                      <span>Duration: {generatedPoll.duration_days} Day</span>
                      <span>Final voting open to all users</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. TREND RADAR SUBTAB */}
      {subTab === "trends" && (
        <div className="space-y-6">
          <div className="bg-app-card border border-app-border/[0.08] rounded-xl p-6 space-y-4">
            <div>
              <h3 className="text-base font-bold text-app-text flex items-center gap-2">
                <TrendingUp size={18} className="text-emerald-400" />
                Real-Time Trend & News Radar
              </h3>
              <p className="text-xs text-app-text/50 mt-0.5">
                Automatically monitors RSS and breaking industry news, filtering for high persona relevance ($\ge 0.65$) to formulate instant hot takes.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-black/20 border border-white/5 p-4 rounded-lg space-y-2">
                <div className="text-xs font-semibold text-app-text/80">Default Monitored Sources</div>
                <ul className="text-xs text-app-text/60 space-y-1 font-mono text-[11px]">
                  <li>• Hacker News Frontpage (hnrss.org/frontpage)</li>
                  <li>• ArXiv CS.AI Preprints (rss.arxiv.org)</li>
                  <li>• Persona Primary Interests Keywords</li>
                </ul>
              </div>
              <div className="bg-black/20 border border-white/5 p-4 rounded-lg space-y-2">
                <div className="text-xs font-semibold text-app-text/80">Celery Beat Trigger Interval</div>
                <p className="text-xs text-app-text/60">
                  Runs every 30 minutes in background (<code className="text-emerald-400">check_trend_radar</code>), staging approved takes into your Drafts queue with 7-day deduplication.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
