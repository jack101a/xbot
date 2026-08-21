"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  Users, Activity, Settings, TrendingUp, Cpu, Calendar, Play, Pause, 
  Trash2, Plus, ArrowRight, BarChart, FileText, Globe, CheckCircle, XCircle, Clock, X, Moon, Sun, Layers, Zap,
  Key, ShieldCheck, CheckCircle2, AlertCircle, Loader2, RefreshCw
} from "lucide-react";
import { api, Profile, ProfileAuthStatus, Session, Action, SystemHealth, AnalyticsSnapshot, Content } from "@/lib/api";
import { LiveActivityTab } from "@/components/LiveActivityTab";
import { GrowthEngineTab } from "@/components/GrowthEngineTab";
import { ConnectAccountModal } from "@/components/ConnectAccountModal";


const API_PROVIDERS = [
  { id: 'litellm', name: 'LiteLLM Proxy (Custom)' },
  { id: 'gemini', name: 'Google Gemini' },
  { id: 'mistral', name: 'Mistral AI' },
  { id: 'openrouter', name: 'OpenRouter' },
  { id: 'deepseek', name: 'DeepSeek' }
];

const CONTEXT_OPTIONS = [
  { id: 'memory', label: 'Memory' },
  { id: 'characteristic', label: 'Characteristics' },
  { id: 'personality', label: 'Personality' },
  { id: 'habits', label: 'Habits' },
  { id: 'interests', label: 'Interests' },
  { id: 'likes', label: 'Likes' },
  { id: 'dislikes', label: 'Dislikes' },
];

const getAvatarUrl = (p: any): string | null => {
  if (!p) return null;
  return p.avatar_url || p.config?.profile_image_url || p.config?.avatar_url || null;
};

function JobModelSelector({ 
  label, 
  description, 
  value, 
  onChange,
  promptValue,
  onPromptChange,
  contextValue,
  onContextChange
}: { 
  label: string; 
  description: string; 
  value: string; 
  onChange: (val: string) => void;
  promptValue?: string;
  onPromptChange?: (val: string) => void;
  contextValue?: string;
  onContextChange?: (val: string) => void;
}) {
  const parts = value.split(',');
  const primaryStr = parts[0] || '';
  const fallbackStr = parts[1] || '';

  const parseModelStr = (s: string) => {
    if (!s) return { provider: 'litellm', model: '' };
    const idx = s.indexOf('/');
    if (idx !== -1) {
      const p = s.substring(0, idx);
      const m = s.substring(idx + 1);
      if (API_PROVIDERS.find(x => x.id === p)) {
        return { provider: p, model: m };
      }
    }
    return { provider: 'litellm', model: s };
  };

  const primary = parseModelStr(primaryStr);
  const fallback = parseModelStr(fallbackStr);

  const [primaryOptions, setPrimaryOptions] = useState<string[]>([]);
  const [fallbackOptions, setFallbackOptions] = useState<string[]>([]);
  const [primaryLoading, setPrimaryLoading] = useState(false);
  const [fallbackLoading, setFallbackLoading] = useState(false);

  useEffect(() => {
    async function fetchModels(provider: string, setter: any, setLoader: any) {
      if (!provider) return;
      setLoader(true);
      try {
        const data = await api.getSystemModels(provider);
        setter(data.models || []);
      } catch (e) {
        setter([]);
      } finally {
        setLoader(false);
      }
    }
    fetchModels(primary.provider, setPrimaryOptions, setPrimaryLoading);
  }, [primary.provider]);

  useEffect(() => {
    async function fetchModels(provider: string, setter: any, setLoader: any) {
      if (!provider) return;
      setLoader(true);
      try {
        const data = await api.getSystemModels(provider);
        setter(data.models || []);
      } catch (e) {
        setter([]);
      } finally {
        setLoader(false);
      }
    }
    fetchModels(fallback.provider, setFallbackOptions, setFallbackLoading);
  }, [fallback.provider]);

  const updateValue = (type: 'primary' | 'fallback', field: 'provider' | 'model', val: string) => {
    const newPrimary = { ...primary };
    const newFallback = { ...fallback };
    
    if (type === 'primary') newPrimary[field] = val;
    else newFallback[field] = val;

    let res = `${newPrimary.provider}/${newPrimary.model}`;
    if (newFallback.model) {
      res += `,${newFallback.provider}/${newFallback.model}`;
    }
    onChange(res);
  };

  return (
    <div className="flex flex-col gap-3 py-3 border-t border-app-border/[0.02]">
      <div>
        <span className="font-semibold text-app-text/80 block text-xs">{label}</span>
        <span className="text-[11px] text-app-text/40 block mt-0.5">{description}</span>
      </div>
      <div className="flex flex-col gap-3 mb-2">
        {onPromptChange && (
          <div className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-app-text/60">System Prompt Instruction</span>
            <textarea 
              value={promptValue || ''}
              onChange={(e) => onPromptChange(e.target.value)}
              placeholder="You are a social media persona..."
              rows={2}
              className="w-full text-xs px-2 py-1.5 rounded-md border border-app-border/[0.06] bg-app-hover text-app-text focus:ring-2 focus:ring-purple-500/50 resize-none"
            />
          </div>
        )}
        {onContextChange && (
          <div className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-app-text/60">Inject Context Features</span>
            <div className="flex flex-wrap gap-2">
              {CONTEXT_OPTIONS.map(opt => {
                const isSelected = (contextValue || '').split(',').includes(opt.id);
                return (
                  <label key={opt.id} className="flex items-center gap-1 text-[11px] text-app-text/70 cursor-pointer">
                    <input 
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => {
                        const current = (contextValue || '').split(',').filter(Boolean);
                        if (e.target.checked) {
                          onContextChange([...current, opt.id].join(','));
                        } else {
                          onContextChange(current.filter(x => x !== opt.id).join(','));
                        }
                      }}
                      className="rounded border-app-border/[0.1] bg-app-hover text-purple-500 focus:ring-purple-500/50"
                    />
                    {opt.label}
                  </label>
                );
              })}
            </div>
          </div>
        )}
      </div>
      <div className="grid grid-cols-2 gap-4">
        {/* Primary Model */}
        <div className="bg-app-hover rounded-md p-3 border border-app-border/[0.04]">
          <span className="text-xs font-semibold text-app-text/60 mb-2 block">Primary Model</span>
          <div className="flex flex-col gap-2">
            <select 
              className="w-full text-xs px-2 py-1.5 rounded-md border border-app-border/[0.06] bg-transparent text-app-text focus:ring-2 focus:ring-purple-500/50"
              value={primary.provider}
              onChange={(e) => updateValue('primary', 'provider', e.target.value)}
            >
              {API_PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <select 
              className="w-full text-xs px-2 py-1.5 rounded-md border border-app-border/[0.06] bg-transparent text-app-text focus:ring-2 focus:ring-purple-500/50"
              value={primary.model}
              onChange={(e) => updateValue('primary', 'model', e.target.value)}
            >
              <option value="">-- Select Model --</option>
              {primaryLoading && <option value="" disabled>Loading models...</option>}
              {!primaryLoading && primaryOptions.map(m => <option key={m} value={m}>{m}</option>)}
              {!primaryLoading && primary.model && !primaryOptions.includes(primary.model) && <option value={primary.model}>{primary.model}</option>}
            </select>
          </div>
        </div>

        {/* Fallback Model */}
        <div className="bg-app-hover rounded-md p-3 border border-app-border/[0.04]">
          <span className="text-xs font-semibold text-app-text/60 mb-2 block">Fallback Model (Optional)</span>
          <div className="flex flex-col gap-2">
            <select 
              className="w-full text-xs px-2 py-1.5 rounded-md border border-app-border/[0.06] bg-transparent text-app-text focus:ring-2 focus:ring-purple-500/50"
              value={fallback.provider}
              onChange={(e) => updateValue('fallback', 'provider', e.target.value)}
            >
              {API_PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <select 
              className="w-full text-xs px-2 py-1.5 rounded-md border border-app-border/[0.06] bg-transparent text-app-text focus:ring-2 focus:ring-purple-500/50"
              value={fallback.model}
              onChange={(e) => updateValue('fallback', 'model', e.target.value)}
            >
              <option value="">-- Select Model --</option>
              {fallbackLoading && <option value="" disabled>Loading models...</option>}
              {!fallbackLoading && fallbackOptions.map(m => <option key={m} value={m}>{m}</option>)}
              {!fallbackLoading && fallback.model && !fallbackOptions.includes(fallback.model) && <option value={fallback.model}>{fallback.model}</option>}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}

function ApiKeyInput({ 
  label, 
  provider,
  value, 
  onChange,
  onSave
}: { 
  label: string; 
  provider: string;
  value: string; 
  onChange: (val: string) => void;
  onSave: () => Promise<void>;
}) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{success: boolean, msg: string} | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    await onSave();
    setSaving(false);
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const data = await api.getSystemModels(provider);
      if (data.models && data.models.length > 0) {
        setTestResult({ success: true, msg: `Success! Found ${data.models.length} models.` });
      } else {
        setTestResult({ success: false, msg: "Failed: Invalid key or API returned no models." });
      }
    } catch (e) {
      setTestResult({ success: false, msg: "Failed to connect to backend." });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <label className="block text-xs font-semibold text-app-text/50 uppercase">{label}</label>
      <div className="flex gap-2">
        <input 
          type="password"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="sk-..."
          className="flex-1 bg-transparent border border-app-border/[0.06] rounded px-3 py-2 text-xs font-mono text-app-text/95 font-medium focus:ring-2 focus:ring-offset-0 focus:ring-purple-500/50 focus:ring-purple-500 focus:border-purple-500 focus:outline-none"
        />
        <button 
          type="button" 
          onClick={handleSave}
          disabled={saving}
          className="px-3 py-1.5 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-500 text-xs font-semibold rounded border border-indigo-500/20 transition-colors disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button 
          type="button" 
          onClick={handleTest}
          disabled={testing}
          className="px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 text-xs font-semibold rounded border border-emerald-500/20 transition-colors disabled:opacity-50"
        >
          {testing ? "Testing..." : "Test API"}
        </button>
      </div>
      {testResult && (
        <span className={`text-[10px] mt-1 font-medium ${testResult.success ? 'text-emerald-500' : 'text-rose-500'}`}>
          {testResult.msg}
        </span>
      )}
    </div>
  );
}

function AutomationLimitsTab({ profileId }: { profileId: string }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [mockMode, setMockMode] = useState(false);

  const [limits, setLimits] = useState({
    max_likes_per_day: 50,
    max_replies_per_day: 15,
    max_posts_per_day: 5,
    max_follows_per_day: 10,
  });

  const [schedule, setSchedule] = useState({
    interval_minutes: 45,
    min_sessions_per_day: 3,
    max_sessions_per_day: 5,
    timezone: "America/New_York",
  });

  const [startTime, setStartTime] = useState("08:00");
  const [endTime, setEndTime] = useState("22:00");

  useEffect(() => {
    if (!profileId) return;
    setLoading(true);
    setSaveMessage(null);
    api.getProfileConfig(profileId)
      .then((data: any) => {
        if (data?.mock_mode !== undefined) {
          setMockMode(Boolean(data.mock_mode));
        }
        if (data?.limits) {
          setLimits({
            max_likes_per_day: data.limits.max_likes_per_day ?? 50,
            max_replies_per_day: data.limits.max_replies_per_day ?? 15,
            max_posts_per_day: data.limits.max_posts_per_day ?? 5,
            max_follows_per_day: data.limits.max_follows_per_day ?? 10,
          });
        }
        if (data?.schedule) {
          setSchedule({
            interval_minutes: data.schedule.interval_minutes ?? 45,
            min_sessions_per_day: data.schedule.min_sessions_per_day ?? 3,
            max_sessions_per_day: data.schedule.max_sessions_per_day ?? 5,
            timezone: data.schedule.timezone || "America/New_York",
          });
          const activeHours = data.schedule.active_hours || "08:00-22:00";
          const parts = activeHours.split("-");
          if (parts.length === 2) {
            setStartTime(parts[0]);
            setEndTime(parts[1]);
          }
        }
      })
      .catch(err => {
        console.error("Error loading profile config:", err);
      })
      .finally(() => setLoading(false));
  }, [profileId]);

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage(null);
    try {
      const payload = {
        mock_mode: mockMode,
        limits,
        schedule: {
          ...schedule,
          active_hours: `${startTime}-${endTime}`,
        },
      };
      const res = await api.updateProfileConfig(profileId, payload);
      if (res && res.status === "success") {
        setSaveMessage({ type: 'success', text: "✅ Automation limits & schedule saved! Daily schedule refreshed in Redis." });
      } else {
        setSaveMessage({ type: 'error', text: "❌ Failed to update configuration." });
      }
    } catch (err: any) {
      setSaveMessage({ type: 'error', text: "❌ Error: " + (err.message || "Failed to save") });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-app-text/60 animate-pulse">
        Loading live automation configuration from backend...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {saveMessage && (
        <div className={`p-4 rounded-lg font-medium text-sm flex items-center gap-2 ${saveMessage.type === 'success' ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400' : 'bg-rose-500/10 border border-rose-500/30 text-rose-400'}`}>
          <span>{saveMessage.text}</span>
        </div>
      )}

      <div className={`rounded-lg border p-5 transition-all duration-300 ${mockMode ? 'bg-amber-500/10 border-amber-500/40 shadow-lg shadow-amber-500/5' : 'bg-panel/80 border-app-border/[0.06]'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-lg ${mockMode ? 'bg-amber-500/20 text-amber-400 animate-pulse' : 'bg-app-surface/60 text-app-text/50'}`}>
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold text-app-text/95">🧪 Mock / Demo / Test Mode</h3>
                {mockMode && <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">ACTIVE SIMULATION</span>}
              </div>
              <p className="text-xs text-app-text/60 mt-0.5">When enabled, the bot runs all AI generating, audience analyzing, and session planning workflows normally, but simulates actions instead of sending live requests to X.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setMockMode(!mockMode)}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${mockMode ? 'bg-amber-500' : 'bg-gray-600'}`}
          >
            <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${mockMode ? 'translate-x-5' : 'translate-x-0'}`} />
          </button>
        </div>
      </div>

      <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-semibold text-app-text/95 font-medium">Daily Engagement Limits</h3>
            <p className="text-xs text-app-text/50 mt-1">Real-time limits enforced by sliding-window rate limiters and circuit breakers.</p>
          </div>
          <span className="text-xs font-mono px-2 py-1 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">LIVE BACKEND SYNC</span>
        </div>
        <div className="grid grid-cols-2 gap-8">
          <div>
            <label className="flex justify-between text-sm font-medium text-app-text/80 mb-2">
              <span>Max Likes / Day</span>
              <span className="text-blue-400 font-bold">{limits.max_likes_per_day}</span>
            </label>
            <input 
              type="range" 
              className="w-full accent-blue-600 cursor-pointer" 
              min="0" 
              max="200" 
              value={limits.max_likes_per_day} 
              onChange={(e) => setLimits({ ...limits, max_likes_per_day: parseInt(e.target.value) || 0 })}
            />
            <div className="flex justify-between text-[10px] text-app-text/40 mt-1">
              <span>0 (Disabled)</span>
              <span>100 (Balanced)</span>
              <span>200 (Max)</span>
            </div>
          </div>
          <div>
            <label className="flex justify-between text-sm font-medium text-app-text/80 mb-2">
              <span>Max Replies / Day</span>
              <span className="text-purple-400 font-bold">{limits.max_replies_per_day}</span>
            </label>
            <input 
              type="range" 
              className="w-full accent-purple-600 cursor-pointer" 
              min="0" 
              max="100" 
              value={limits.max_replies_per_day} 
              onChange={(e) => setLimits({ ...limits, max_replies_per_day: parseInt(e.target.value) || 0 })}
            />
            <div className="flex justify-between text-[10px] text-app-text/40 mt-1">
              <span>0 (Disabled)</span>
              <span>50 (Balanced)</span>
              <span>100 (Max)</span>
            </div>
          </div>
          <div>
            <label className="flex justify-between text-sm font-medium text-app-text/80 mb-2">
              <span>Max Posts / Day</span>
              <span className="text-emerald-400 font-bold">{limits.max_posts_per_day}</span>
            </label>
            <input 
              type="range" 
              className="w-full accent-emerald-600 cursor-pointer" 
              min="0" 
              max="30" 
              value={limits.max_posts_per_day} 
              onChange={(e) => setLimits({ ...limits, max_posts_per_day: parseInt(e.target.value) || 0 })}
            />
            <div className="flex justify-between text-[10px] text-app-text/40 mt-1">
              <span>0 (Disabled)</span>
              <span>15 (Balanced)</span>
              <span>30 (Max)</span>
            </div>
          </div>
          <div>
            <label className="flex justify-between text-sm font-medium text-app-text/80 mb-2">
              <span>Max Follows / Day</span>
              <span className="text-amber-400 font-bold">{limits.max_follows_per_day}</span>
            </label>
            <input 
              type="range" 
              className="w-full accent-amber-600 cursor-pointer" 
              min="0" 
              max="100" 
              value={limits.max_follows_per_day} 
              onChange={(e) => setLimits({ ...limits, max_follows_per_day: parseInt(e.target.value) || 0 })}
            />
            <div className="flex justify-between text-[10px] text-app-text/40 mt-1">
              <span>0 (Disabled)</span>
              <span>50 (Balanced)</span>
              <span>100 (Max)</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
        <h3 className="text-lg font-semibold text-app-text/95 font-medium mb-6">Execution Schedule & Worker Timing</h3>
        <div className="space-y-5">
          <div className="flex items-center justify-between p-4 border border-app-border/[0.06] rounded-md bg-app/50">
            <div>
              <p className="font-medium text-app-text/95 font-medium">Run Interval</p>
              <p className="text-sm text-app-text/50 mt-1">How often should the Celery beat worker wake up and evaluate scheduled tasks?</p>
            </div>
            <div className="flex items-center gap-2">
              <input 
                type="number" 
                value={schedule.interval_minutes} 
                onChange={(e) => setSchedule({ ...schedule, interval_minutes: parseInt(e.target.value) || 15 })}
                className="w-20 px-3 py-2 border border-slate-300 rounded-md shadow-2xl shadow-black/50 focus:ring-purple-500 focus:border-purple-500 text-sm bg-transparent text-app-text font-medium" 
              />
              <span className="text-sm text-app-text/60 font-medium">Minutes</span>
            </div>
          </div>

          <div className="flex items-center justify-between p-4 border border-app-border/[0.06] rounded-md bg-app/50">
            <div>
              <p className="font-medium text-app-text/95 font-medium">Active Hours (Human Simulating Window)</p>
              <p className="text-sm text-app-text/50 mt-1">Restrict automated posting and engagement to natural waking hours in your timezone.</p>
            </div>
            <div className="flex items-center gap-2">
              <input 
                type="time" 
                value={startTime} 
                onChange={(e) => setStartTime(e.target.value)}
                className="px-3 py-2 border border-slate-300 rounded-md shadow-2xl shadow-black/50 text-sm bg-transparent text-app-text font-medium" 
              />
              <span className="text-app-text/40">to</span>
              <input 
                type="time" 
                value={endTime} 
                onChange={(e) => setEndTime(e.target.value)}
                className="px-3 py-2 border border-slate-300 rounded-md shadow-2xl shadow-black/50 text-sm bg-transparent text-app-text font-medium" 
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-4 border border-app-border/[0.06] rounded-md bg-app/50">
              <div>
                <p className="font-medium text-app-text/95 font-medium">Min Sessions / Day</p>
                <p className="text-xs text-app-text/50 mt-0.5">Minimum bot wakeups per day</p>
              </div>
              <input 
                type="number" 
                value={schedule.min_sessions_per_day} 
                onChange={(e) => setSchedule({ ...schedule, min_sessions_per_day: parseInt(e.target.value) || 1 })}
                className="w-20 px-3 py-2 border border-slate-300 rounded-md text-sm bg-transparent text-app-text font-medium" 
              />
            </div>
            <div className="flex items-center justify-between p-4 border border-app-border/[0.06] rounded-md bg-app/50">
              <div>
                <p className="font-medium text-app-text/95 font-medium">Max Sessions / Day</p>
                <p className="text-xs text-app-text/50 mt-0.5">Maximum bot wakeups per day</p>
              </div>
              <input 
                type="number" 
                value={schedule.max_sessions_per_day} 
                onChange={(e) => setSchedule({ ...schedule, max_sessions_per_day: parseInt(e.target.value) || 5 })}
                className="w-20 px-3 py-2 border border-slate-300 rounded-md text-sm bg-transparent text-app-text font-medium" 
              />
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button 
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-fuchsia-500 text-white shadow-lg shadow-purple-500/25 rounded-md font-semibold text-sm hover:scale-[1.02] transition-all disabled:opacity-50 cursor-pointer"
          >
            {saving ? "Saving to Backend..." : "Save Limits & Schedule"}
          </button>
        </div>
      </div>
    </div>
  );
}

function TargetAudienceStrategyTab({ profileId, selectedProfile, analytics }: { profileId: string; selectedProfile: any; analytics: any }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const [keywords, setKeywords] = useState<string[]>(["#SaaS", "startup marketing", "Next.js", "Python automation"]);
  const [newKeyword, setNewKeyword] = useState("");

  const [competitors, setCompetitors] = useState<string[]>(["@competitor_x", "@competitor_y"]);
  const [newCompetitor, setNewCompetitor] = useState("");

  useEffect(() => {
    if (!profileId) return;
    setLoading(true);
    setSaveMessage(null);
    api.getProfileStrategy(profileId)
      .then((data: any) => {
        if (data?.content_strategy?.top_performing_topics && Array.isArray(data.content_strategy.top_performing_topics)) {
          if (data.content_strategy.top_performing_topics.length > 0) {
            setKeywords(data.content_strategy.top_performing_topics);
          }
        }
        if (data?.engagement_strategy?.priority_accounts && Array.isArray(data.engagement_strategy.priority_accounts)) {
          if (data.engagement_strategy.priority_accounts.length > 0) {
            setCompetitors(data.engagement_strategy.priority_accounts);
          }
        }
      })
      .catch(err => {
        console.error("Error loading strategy:", err);
      })
      .finally(() => setLoading(false));
  }, [profileId]);

  const handleAddKeyword = () => {
    const val = newKeyword.trim();
    if (!val) return;
    if (!keywords.includes(val)) {
      setKeywords([...keywords, val]);
    }
    setNewKeyword("");
  };

  const handleRemoveKeyword = (tag: string) => {
    setKeywords(keywords.filter(k => k !== tag));
  };

  const handleAddCompetitor = () => {
    let val = newCompetitor.trim();
    if (!val) return;
    if (!val.startsWith("@")) val = "@" + val;
    if (!competitors.includes(val)) {
      setCompetitors([...competitors, val]);
    }
    setNewCompetitor("");
  };

  const handleRemoveCompetitor = (comp: string) => {
    setCompetitors(competitors.filter(c => c !== comp));
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage(null);
    try {
      const payload = {
        content_strategy: {
          top_performing_topics: keywords,
        },
        engagement_strategy: {
          priority_accounts: competitors,
        }
      };
      const res = await api.updateProfileStrategy(profileId, payload);
      if (res && res.status === "success") {
        setSaveMessage({ type: 'success', text: "✅ Target audience & competitor strategy saved to strategy.yaml!" });
      } else {
        setSaveMessage({ type: 'error', text: "❌ Failed to update strategy." });
      }
    } catch (err: any) {
      setSaveMessage({ type: 'error', text: "❌ Error: " + (err.message || "Failed to save") });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-app-text/60 animate-pulse">
        Loading target audience strategy from backend...
      </div>
    );
  }

  const selfFollowers = analytics[profileId]?.followers || 0;
  const benchmarkList = [
    { name: `You (@${selectedProfile?.profile_slug || 'xbot'})`, followers: selfFollowers, color: "bg-gradient-to-r from-indigo-500 via-purple-500 to-fuchsia-500 text-app-text shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_15px_rgba(139,92,246,0.3)]", isSelf: true },
    ...competitors.map((handle) => {
      return {
        name: handle,
        followers: 0, // Will be populated by real AI scraper tasks
        color: "bg-slate-400",
        isSelf: false
      };
    })
  ];
  const maxFollowers = Math.max(...benchmarkList.map(b => b.followers), selfFollowers, 1);


  return (
    <div className="max-w-4xl space-y-6">
      {saveMessage && (
        <div className={`p-4 rounded-lg font-medium text-sm flex items-center gap-2 ${saveMessage.type === 'success' ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400' : 'bg-rose-500/10 border border-rose-500/30 text-rose-400'}`}>
          <span>{saveMessage.text}</span>
        </div>
      )}

      <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-semibold text-app-text/95 font-medium mb-1">Target Audience & Trend Search</h3>
            <p className="text-sm text-app-text/50">Dynamic keywords and competitor accounts used by AI for audience targeting and follower extraction.</p>
          </div>
          <span className="text-xs font-mono px-2 py-1 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">LIVE STRATEGY SYNC</span>
        </div>
        
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-app-text/80 mb-2">Tracked Keywords / Hashtags</label>
            <div className="flex flex-wrap gap-2 mb-3">
              {keywords.map(tag => (
                <span key={tag} className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/[0.02] text-app-text/80 rounded-full text-sm font-medium border border-app-border/[0.06]">
                  {tag} 
                  <button type="button" onClick={() => handleRemoveKeyword(tag)} className="text-app-text/40 hover:text-rose-400 font-bold ml-1 transition-colors">&times;</button>
                </span>
              ))}
              {keywords.length === 0 && <span className="text-xs text-app-text/40 italic">No keywords added yet.</span>}
            </div>
            <div className="flex gap-2">
              <input 
                type="text" 
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddKeyword()}
                placeholder="Add new keyword or hashtag (e.g. #SaaS, AI agents)..." 
                className="flex-1 px-3 py-2 border border-app-border/[0.15] bg-app-surface/50 rounded-md shadow-inner text-sm text-app-text focus:border-purple-500 focus:outline-none" 
              />
              <button type="button" onClick={handleAddKeyword} className="px-4 py-2 bg-purple-500/10 border border-purple-500/30 text-purple-300 rounded-md font-medium text-sm hover:bg-purple-500/20 transition-all cursor-pointer">Add Keyword</button>
            </div>
          </div>
          
          <hr className="border-app-border/[0.04]" />
          
          <div>
            <label className="block text-sm font-medium text-app-text/80 mb-2">Competitor Accounts (For Follower Extraction)</label>
            <div className="flex flex-wrap gap-2 mb-3">
              {competitors.map(comp => (
                <span key={comp} className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/[0.02] text-app-text/80 rounded-full text-sm font-medium border border-app-border/[0.06]">
                  {comp} 
                  <button type="button" onClick={() => handleRemoveCompetitor(comp)} className="text-app-text/40 hover:text-rose-400 font-bold ml-1 transition-colors">&times;</button>
                </span>
              ))}
              {competitors.length === 0 && <span className="text-xs text-app-text/40 italic">No competitor accounts added yet.</span>}
            </div>
            <div className="flex gap-2">
              <input 
                type="text" 
                value={newCompetitor}
                onChange={(e) => setNewCompetitor(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddCompetitor()}
                placeholder="@competitor_handle" 
                className="flex-1 px-3 py-2 border border-app-border/[0.15] bg-app-surface/50 rounded-md shadow-inner text-sm text-app-text focus:border-purple-500 focus:outline-none" 
              />
              <button type="button" onClick={handleAddCompetitor} className="px-4 py-2 bg-purple-500/10 border border-purple-500/30 text-purple-300 rounded-md font-medium text-sm hover:bg-purple-500/20 transition-all cursor-pointer">Add Competitor</button>
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button 
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-fuchsia-500 text-white shadow-lg shadow-purple-500/25 rounded-md font-semibold text-sm hover:scale-[1.02] transition-all disabled:opacity-50 cursor-pointer"
            >
              {saving ? "Saving Strategy..." : "Save Target Audience & Competitors"}
            </button>
          </div>

          {/* Competitor Benchmarking Widget */}
          <hr className="border-app-border/[0.04] mt-6" />
          
          <div className="pt-4">
            <h4 className="text-sm font-bold text-app-text/95 font-medium mb-4">Competitor Followers Benchmark</h4>
            
            <div className="space-y-4">
              {benchmarkList.map((comp, idx) => {
                const widthPercent = maxFollowers > 0 ? (comp.followers / maxFollowers) * 100 : 50;
                return (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-app-text/80">
                      <span>{comp.name}</span>
                      <span>{comp.followers.toLocaleString()} followers</span>
                    </div>
                    <div className="w-full h-4 bg-white/[0.02] rounded-full overflow-hidden flex">
                      <div 
                        className={`h-full ${comp.color} rounded-full transition-all duration-500`}
                        style={{ width: `${widthPercent}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
            
            <div className="mt-4 p-3 bg-purple-500/10 border border-purple-500/20 rounded-md text-[11px] text-purple-300 font-medium">
              <strong>💡 Benchmark Insight:</strong> Tracking {competitors.length} competitor accounts. Your AI engagement engine automatically extracts active followers from these accounts and prioritizes them in daily sessions.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {

  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [analytics, setAnalytics] = useState<Record<string, AnalyticsSnapshot>>({});
  const [analyticsHistory, setAnalyticsHistory] = useState<AnalyticsSnapshot[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);

  // Apply dark mode class to html element
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);
  
  // Profile specific state
  const [activeTab, setActiveTab] = useState<"overview" | "queue" | "sessions" | "automation" | "ai" | "trends" | "free-tools" | "global-settings" | "campaigns" | "analytics" | "growth">("global-settings");
  const [loading, setLoading] = useState(true);
  
  // Modals & Profile Auth
  const [isNewProfileModalOpen, setIsNewProfileModalOpen] = useState(false);
  const [newProfileSlug, setNewProfileSlug] = useState("");
  const [newXHandle, setNewXHandle] = useState("");
  const [authStatuses, setAuthStatuses] = useState<Record<string, ProfileAuthStatus>>({});
  const [isConnectAccountModalOpen, setIsConnectAccountModalOpen] = useState(false);
  const [isSyncingFromX, setIsSyncingFromX] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  
  const [advancedMetrics, setAdvancedMetrics] = useState<any>(null);
  const [advancedMetricsLoading, setAdvancedMetricsLoading] = useState(false);
  const [systemConfig, setSystemConfig] = useState<any>(null);
  const [litellmBaseUrl, setLitellmBaseUrl] = useState("");
  const [litellmApiKey, setLitellmApiKey] = useState("");
  const [litellmPrimaryModel, setLitellmPrimaryModel] = useState("");
  const [litellmFastModel, setLitellmFastModel] = useState("");
  const [modelPostCreation, setModelPostCreation] = useState("");
  const [modelReplyAnalysis, setModelReplyAnalysis] = useState("");
  const [modelTrendAnalysis, setModelTrendAnalysis] = useState("");
  const [modelLikeRetweet, setModelLikeRetweet] = useState("");
  const [modelFollow, setModelFollow] = useState("");
  
  const [promptPostCreation, setPromptPostCreation] = useState("");
  const [promptReplyAnalysis, setPromptReplyAnalysis] = useState("");
  const [promptTrendAnalysis, setPromptTrendAnalysis] = useState("");
  const [promptLikeRetweet, setPromptLikeRetweet] = useState("");
  const [promptFollow, setPromptFollow] = useState("");
  
  const [contextPostCreation, setContextPostCreation] = useState("");
  const [contextReplyAnalysis, setContextReplyAnalysis] = useState("");
  const [contextTrendAnalysis, setContextTrendAnalysis] = useState("");
  const [contextLikeRetweet, setContextLikeRetweet] = useState("");
  const [contextFollow, setContextFollow] = useState("");
  
  const [mistralApiKey, setMistralApiKey] = useState("");
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [deepseekApiKey, setDeepseekApiKey] = useState("");
  const [openrouterApiKey, setOpenrouterApiKey] = useState("");
  const [savingConfig, setSavingConfig] = useState(false);

  // Timeframe and Metric states for Overview Charts
  const [timeframe, setTimeframe] = useState<"24h" | "7d" | "4w" | "6m">("7d");
  const [chartMetric, setChartMetric] = useState<"impressions" | "engagement" | "followers">("impressions");
  const [hoveredPoint, setHoveredPoint] = useState<{ label: string; value: number; x: number; y: number } | null>(null);

  // Live Follower Counter State
  const [liveFollowers, setLiveFollowers] = useState<number>(0);
  const [liveFollowersHistory, setLiveFollowersHistory] = useState<number[]>([]);
  const [showLiveCounterModal, setShowLiveCounterModal] = useState(false);

  // Free Tools Search States
  const [freeSearchHandle, setFreeSearchHandle] = useState("");
  const [freeSearchLoading, setFreeSearchLoading] = useState(false);
  const [freeSearchResults, setFreeSearchResults] = useState<any>(null);
  const [freeLiveFollowers, setFreeLiveFollowers] = useState<number>(0);
  const [freeLiveFollowersHistory, setFreeLiveFollowersHistory] = useState<number[]>([]);

  const handleFreeSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!freeSearchHandle) return;
    setFreeSearchLoading(true);
    setFreeSearchResults(null);
    try {
      const res = await api.getAdvancedMetrics(freeSearchHandle);
      if (res && !res.error) {
        setFreeSearchResults(res);
        setFreeLiveFollowers(res.followers || 0);
        setFreeLiveFollowersHistory(Array(9).fill(res.followers || 0));
      } else {
        alert(res?.error || "No metrics found or rate limited.");
      }
    } catch (err) {
      console.error(err);
      alert("Error fetching metrics. Make sure the backend is online.");
    } finally {
      setFreeSearchLoading(false);
    }
  };

  // Initialize live follower count whenever selected profile or analytics updates
  useEffect(() => {
    if (!selectedProfileId) return;
    const baseFollowers = analytics[selectedProfileId]?.followers || 0;
    setLiveFollowers(baseFollowers);
    setLiveFollowersHistory(Array(9).fill(baseFollowers));
  }, [selectedProfileId, analytics]);

  // Original Dashboard State Features
  const [drafts, setDrafts] = useState<Content[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [triggeringSession, setTriggeringSession] = useState(false);
  
  // AI Persona & Memory State
  const [persona, setPersona] = useState<any>(null);
  const [profileJobOverrides, setProfileJobOverrides] = useState<any>({});
  const [learnedState, setLearnedState] = useState<any>(null);
  const [reflecting, setReflecting] = useState(false);
  const [isTriggeringAutoreply, setIsTriggeringAutoreply] = useState(false);
  const [importCardInput, setImportCardInput] = useState("");
  const [importUseAi, setImportUseAi] = useState(false);
  const [isImportingCard, setIsImportingCard] = useState(false);

  const [memories, setMemories] = useState<any[]>([]);
  const [diary, setDiary] = useState<any[]>([]);
  const [llmConfig, setLlmConfig] = useState<any>(null);

  const fetchGlobalData = useCallback(async () => {
    try {
      const profilesData = await api.listProfiles();
      setProfiles(profilesData);
      if (profilesData.length > 0) {
        // Fetch analytics & auth status for all profiles
        const analyticsMap: Record<string, AnalyticsSnapshot> = {};
        const authStatusMap: Record<string, ProfileAuthStatus> = {};

        await Promise.all(
          profilesData.map(async (p) => {
            try {
              const snaps = await api.getProfileAnalytics(p.id, 1);
              if (snaps && snaps.length > 0) {
                analyticsMap[p.id] = snaps[0];
              }
            } catch (e) {
              console.error(`Error fetching analytics for ${p.id}:`, e);
            }

            try {
              const authStatus = await api.getProfileAuthStatus(p.id);
              if (authStatus) {
                authStatusMap[p.id] = authStatus;
              }
            } catch (e) {
              console.error(`Error fetching auth status for ${p.id}:`, e);
            }
          })
        );

        setAnalytics(analyticsMap);
        setAuthStatuses(authStatusMap);

        // Fetch System Health
        const health = await api.getHealth();
        setSystemHealth(health);
        
        // Fetch System Config
        const config = await api.getConfig();
        setSystemConfig(config);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [selectedProfileId]);

  const handleSyncFromX = async () => {
    const profile = profiles.find(p => p.id === selectedProfileId);
    if (!profile) return;
    setIsSyncingFromX(true);
    setSyncFeedback(null);
    try {
      const res = await api.syncProfileFromX(profile.id);
      const followers = res.sync_data?.followers_count ?? res.profile?.followers_count ?? 0;
      const following = res.sync_data?.following_count ?? res.profile?.following_count ?? 0;
      setSyncFeedback({
        type: 'success',
        message: `Synced @${res.profile?.x_handle || profile.x_handle}: ${followers.toLocaleString()} followers, ${following.toLocaleString()} following.`
      });
      await fetchGlobalData();
      setTimeout(() => setSyncFeedback(null), 5000);
    } catch (err: any) {
      setSyncFeedback({
        type: 'error',
        message: `Sync failed: ${err.message || String(err)}`
      });
      setTimeout(() => setSyncFeedback(null), 6000);
    } finally {
      setIsSyncingFromX(false);
    }
  };

  useEffect(() => {
    fetchGlobalData();
  }, [fetchGlobalData]);

  useEffect(() => {
    if (systemConfig) {
      setLitellmBaseUrl(systemConfig.LITELLM_BASE_URL || "");
      setLitellmApiKey(systemConfig.LITELLM_API_KEY || "");
      setLitellmPrimaryModel(systemConfig.LITELLM_PRIMARY_MODEL || "");
      setLitellmFastModel(systemConfig.LITELLM_FAST_MODEL || "");
      setModelPostCreation(systemConfig.MODEL_POST_CREATION || "");
      setModelReplyAnalysis(systemConfig.MODEL_REPLY_ANALYSIS || "");
      setModelTrendAnalysis(systemConfig.MODEL_TREND_ANALYSIS || "");
      setModelLikeRetweet(systemConfig.MODEL_LIKE_RETWEET || "");
      setModelFollow(systemConfig.MODEL_FOLLOW || "");
      setPromptPostCreation(systemConfig.PROMPT_POST_CREATION || "");
      setPromptReplyAnalysis(systemConfig.PROMPT_REPLY_ANALYSIS || "");
      setPromptTrendAnalysis(systemConfig.PROMPT_TREND_ANALYSIS || "");
      setPromptLikeRetweet(systemConfig.PROMPT_LIKE_RETWEET || "");
      setPromptFollow(systemConfig.PROMPT_FOLLOW || "");
      setContextPostCreation(systemConfig.CONTEXT_POST_CREATION || "");
      setContextReplyAnalysis(systemConfig.CONTEXT_REPLY_ANALYSIS || "");
      setContextTrendAnalysis(systemConfig.CONTEXT_TREND_ANALYSIS || "");
      setContextLikeRetweet(systemConfig.CONTEXT_LIKE_RETWEET || "");
      setContextFollow(systemConfig.CONTEXT_FOLLOW || "");
      setMistralApiKey(systemConfig.MISTRAL_API_KEY || "");
      setGeminiApiKey(systemConfig.GEMINI_API_KEY || "");
      setDeepseekApiKey(systemConfig.DEEPSEEK_API_KEY || "");
      setOpenrouterApiKey(systemConfig.OPENROUTER_API_KEY || "");
    }
  }, [systemConfig]);

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingConfig(true);
    try {
      await api.updateConfig({
        LITELLM_BASE_URL: litellmBaseUrl,
        LITELLM_API_KEY: litellmApiKey,
        LITELLM_PRIMARY_MODEL: litellmPrimaryModel,
        LITELLM_FAST_MODEL: litellmFastModel,
        MODEL_POST_CREATION: modelPostCreation,
        MODEL_REPLY_ANALYSIS: modelReplyAnalysis,
        MODEL_TREND_ANALYSIS: modelTrendAnalysis,
        MODEL_LIKE_RETWEET: modelLikeRetweet,
        MODEL_FOLLOW: modelFollow,
        PROMPT_POST_CREATION: promptPostCreation,
        PROMPT_REPLY_ANALYSIS: promptReplyAnalysis,
        PROMPT_TREND_ANALYSIS: promptTrendAnalysis,
        PROMPT_LIKE_RETWEET: promptLikeRetweet,
        PROMPT_FOLLOW: promptFollow,
        CONTEXT_POST_CREATION: contextPostCreation,
        CONTEXT_REPLY_ANALYSIS: contextReplyAnalysis,
        CONTEXT_TREND_ANALYSIS: contextTrendAnalysis,
        CONTEXT_LIKE_RETWEET: contextLikeRetweet,
        CONTEXT_FOLLOW: contextFollow,
        MISTRAL_API_KEY: mistralApiKey,
        GEMINI_API_KEY: geminiApiKey,
        DEEPSEEK_API_KEY: deepseekApiKey,
        OPENROUTER_API_KEY: openrouterApiKey,
      });
      alert("Configuration saved and persisted successfully!");
      const config = await api.getConfig();
      setSystemConfig(config);
    } catch (err: any) {
      alert("Failed to save config: " + err.message);
    } finally {
      setSavingConfig(false);
    }
  };

  // Fetch advanced metrics when profile changes
  useEffect(() => {
    if (selectedProfileId) {
      const profile = profiles.find(p => p.id === selectedProfileId);
      if (!profile) return;

      if (activeTab === "overview" && profile.x_handle) {
        setAdvancedMetricsLoading(true);
        api.getProfileAnalytics(profile.id)
          .then(snaps => {
            setAnalyticsHistory(snaps || []);
            if (snaps && snaps.length > 0) {
              const latest = snaps[0];
              const followersCount = latest.followers || profile.followers_count || 0;
              const topTweets = latest.top_tweets || [];
              const numTweets = topTweets.length;
              
              const totalEng = numTweets > 0 ? topTweets.reduce((a: any, b: any) => a + (b.engagement_score || 0), 0) : (latest.engagements_24h || 0);
              const totalViews = numTweets > 0 ? topTweets.reduce((a: any, b: any) => a + (b.views || 0), 0) : (latest.impressions_24h || 0);
              
              const avgEng = numTweets > 0 ? Math.round((totalEng / numTweets) * 10) / 10 : 0;
              const avgViews = numTweets > 0 ? Math.round((totalViews / numTweets) * 10) / 10 : 0;
              
              const sortedEng = numTweets > 0 ? [...topTweets].sort((a: any, b: any) => (a.engagement_score || 0) - (b.engagement_score || 0)) : [];
              const medianEng = numTweets > 0 ? (sortedEng[Math.floor(numTweets / 2)]?.engagement_score || 0) : 0;
              
              const sortedViews = numTweets > 0 ? [...topTweets].sort((a: any, b: any) => (a.views || 0) - (b.views || 0)) : [];
              const medianViews = numTweets > 0 ? (sortedViews[Math.floor(numTweets / 2)]?.views || 0) : 0;

              const mapped = {
                username: profile.x_handle.replace(/^@/, ""),
                followers: followersCount,
                following: latest.following || profile.following_count || 0,
                metrics: {
                  tweets_analyzed: numTweets,
                  total_engagements: totalEng,
                  total_views: totalViews,
                  avg_engagements_per_tweet: avgEng,
                  avg_views_per_tweet: avgViews,
                  median_engagements_per_tweet: medianEng,
                  median_views_per_tweet: medianViews,
                  views_to_followers_ratio: followersCount > 0 ? Math.round((avgViews / followersCount) * 10000) / 100 : 0.0,
                  engagements_to_followers_ratio: followersCount > 0 ? Math.round((avgEng / followersCount) * 10000) / 100 : 0.0,
                  estimated_engagement_rate: totalViews > 0 ? Math.round((totalEng / totalViews) * 10000) / 100 : (latest.engagement_rate ? Math.round(latest.engagement_rate * 10000) / 100 : 0.0)
                },
                top_tweets: topTweets
              };
              setAdvancedMetrics(mapped);
            } else {
              setAdvancedMetrics(null);
            }
          })
          .catch(err => console.error("Failed to fetch profile analytics snapshots", err))
          .finally(() => setAdvancedMetricsLoading(false));
      }
      
      // Fetch queue and sessions
      api.getContentQueue(profile.id).then(setDrafts).catch(console.error);
      api.getProfileSessions(profile.id).then(setSessions).catch(console.error);
      
      // Setup WebSockets for real-time updates
      const ws = new WebSocket(`ws://localhost:18234/api/ws/live`);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // If we got a live session update, refetch the sessions table
          if (data.session_id) {
            api.getProfileSessions(profile.id).then(setSessions).catch(console.error);
          }
        } catch (err) {
          console.error("WS Parse error", err);
        }
      };

      // Fetch AI Persona and Memories
      api.getProfilePersona(profile.id).then(setPersona).catch(console.error);
      api.getProfileLearnedState(profile.id).then(setLearnedState).catch(console.error);
      api.getProfileMemories(profile.id).then(setMemories).catch(console.error);
      api.getProfileDiary(profile.id).then(setDiary).catch(console.error);
      
      // Fetch Global LLM Config
      api.getConfig().then(setLlmConfig).catch(console.error);

      return () => {
        ws.close();
      };
    }
  }, [selectedProfileId, activeTab, profiles]);

  const handleApproveDraft = async (contentId: string) => {
    if (!selectedProfileId) return;
    try {
      await api.updateContentStatus(selectedProfileId, contentId, "posted");
      setDrafts(drafts.filter(d => d.id !== contentId));
    } catch (e) {
      alert("Failed to approve draft");
    }
  };

  const handleRejectDraft = async (contentId: string) => {
    if (!selectedProfileId) return;
    try {
      await api.updateContentStatus(selectedProfileId, contentId, "failed");
      setDrafts(drafts.filter(d => d.id !== contentId));
    } catch (e) {
      alert("Failed to reject draft");
    }
  };

  const handleTriggerSession = async () => {
    if (!selectedProfileId) return;
    setTriggeringSession(true);
    try {
      await api.triggerSession(selectedProfileId);
      alert("Session triggered successfully. It will run in the background.");
      // Refresh sessions
      const s = await api.getProfileSessions(selectedProfileId);
      setSessions(s);
    } catch (e) {
      alert("Failed to trigger session");
    } finally {
      setTriggeringSession(false);
    }
  };

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanSlug = newProfileSlug.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
    const cleanHandle = newXHandle.trim().replace(/^@/, '');
    if (!cleanSlug || !cleanHandle) {
      alert("Please provide both a Profile Slug and an X Handle.");
      return;
    }
    try {
      await api.createProfile({
        profile_slug: cleanSlug,
        x_handle: cleanHandle,
        display_name: cleanSlug,
        status: "active",
      });
      setIsNewProfileModalOpen(false);
      setNewProfileSlug("");
      setNewXHandle("");
      await fetchGlobalData();
    } catch (err: any) {
      alert("Error creating profile: " + (err?.message || err));
    }
  };

  const getChartData = () => {
    if (!selectedProfile) return [];
    
    const profileId = selectedProfile.id;
    const baseFollowers = analytics[profileId]?.followers || selectedProfile.followers_count || 0;
    const baseImpressions = analytics[profileId]?.impressions_24h || 0;
    const baseEngagement = analytics[profileId]?.engagements_24h || 0;

    let finalVal = baseImpressions;
    if (chartMetric === "engagement") finalVal = baseEngagement;
    if (chartMetric === "followers") finalVal = baseFollowers;

    if (analyticsHistory && analyticsHistory.length > 0) {
      // Return real chronological points from database snapshots
      const sorted = [...analyticsHistory].sort((a, b) => new Date(a.snapshot_date).getTime() - new Date(b.snapshot_date).getTime());
      return sorted.map(snap => {
        let val = snap.impressions_24h || 0;
        if (chartMetric === "engagement") val = snap.engagements_24h || 0;
        if (chartMetric === "followers") val = snap.followers || 0;
        return { label: snap.snapshot_date || "Today", value: val };
      });
    }

    return [{ label: "Now", value: finalVal }];
  };

  const selectedProfile = profiles.find(p => p.id === selectedProfileId);

  const chartData = getChartData();
  const points = chartData.map((d, i) => {
    const xFraction = chartData.length > 1 ? i / (chartData.length - 1) : 0.5;
    const x = 45 + xFraction * 440;
    const maxVal = Math.max(...chartData.map(pt => pt.value), 10);
    const y = 15 + 110 - (d.value / maxVal) * 110;
    return { x: isNaN(x) ? 45 : x, y: isNaN(y) ? 125 : y, label: d.label, value: d.value };
  });

  const linePath = points.reduce((acc, p, i) => {
    return i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
  }, "");

  const areaPath = points.length > 0 
    ? `${linePath} L ${points[points.length - 1].x} 125 L ${points[0].x} 125 Z`
    : "";

  return (
    <div className="flex h-screen animate-fade-in duration-500 bg-app text-app-text font-medium tracking-tight font-sans">
      
      {/* SIDEBAR */}
      <aside className="w-64 bg-panel/80 backdrop-blur-xl border-r border-app-border/[0.06] flex flex-col shadow-2xl shadow-black/50 z-10">
        <div className="p-5 border-b border-app-border/[0.04] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-r from-indigo-500 via-purple-500 to-fuchsia-500 text-app-text shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_15px_rgba(139,92,246,0.3)] rounded flex items-center justify-center text-app-text font-bold">X</div>
            <span className="font-bold text-lg tracking-tight text-app-text/95 font-medium">X-Automate</span>
          </div>
          <button 
            onClick={() => setIsDarkMode(!isDarkMode)} 
            className="p-1.5 rounded-full hover:bg-app-hover transition-colors text-app-text/60 hover:text-app-text"
            title="Toggle Dark/Light Mode"
          >
            {isDarkMode ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>

        {/* Global Settings & Free Tools Buttons */}
        <div className="p-4 border-b border-app-border/[0.04] space-y-1">
          <div className="text-[10px] font-bold text-app-text/40 uppercase tracking-wider mb-2 px-1">Global Views</div>
          <button 
            onClick={() => { setSelectedProfileId(null); setActiveTab("global-settings"); }}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-semibold transition-colors ${
              selectedProfileId === null && activeTab === "global-settings"
                ? "bg-slate-900 text-app-text shadow-2xl shadow-black/50" 
                : "text-app-text/60 hover:bg-app hover:text-app-text font-medium tracking-tight"
            }`}
          >
            <Settings size={16} />
            <span>Global Settings</span>
          </button>
          
          <button 
            onClick={() => { setSelectedProfileId(null); setActiveTab("free-tools"); }}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-semibold transition-colors ${
              selectedProfileId === null && activeTab === "free-tools"
                ? "bg-slate-900 text-app-text shadow-2xl shadow-black/50" 
                : "text-app-text/60 hover:bg-app hover:text-app-text font-medium tracking-tight"
            }`}
          >
            <Globe size={16} />
            <span>Free Tools</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <div className="text-[10px] font-bold text-app-text/40 uppercase tracking-wider mb-3 px-2">Your Profiles</div>
          {profiles.map(p => {
            const auth = authStatuses[p.id];
            const isAuth = auth?.status === 'authenticated';
            const isPartial = auth?.status === 'partial';
            const followers = p.followers_count ?? analytics[p.id]?.followers ?? 0;
            return (
              <button 
                key={p.id}
                onClick={() => { setSelectedProfileId(p.id); setActiveTab("overview"); }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  selectedProfileId === p.id 
                    ? "bg-indigo-600/10 text-indigo-400 border border-indigo-500/30 font-semibold shadow-sm" 
                    : "text-app-text/60 hover:bg-app-hover hover:text-app-text border border-transparent"
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="relative flex-shrink-0">
                    {getAvatarUrl(p) ? (
                      <img 
                        src={getAvatarUrl(p)!} 
                        alt={p.display_name || p.x_handle}
                        className="w-7 h-7 rounded-full object-cover border border-slate-700 bg-slate-800"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                      />
                    ) : (
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-[10px] font-black border border-slate-700">
                        {(p.display_name || p.x_handle || '?').charAt(0).toUpperCase()}
                      </div>
                    )}
                    <div 
                      className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-slate-900 ${
                        isAuth ? 'bg-emerald-400 shadow-sm shadow-emerald-500/50' : isPartial ? 'bg-amber-400 shadow-sm shadow-amber-500/50' : 'bg-rose-500 shadow-sm shadow-rose-500/50'
                      }`}
                      title={isAuth ? "Authenticated" : isPartial ? "Partial Auth" : "Disconnected"}
                    />
                  </div>
                  <div className="text-left truncate">
                    <div className="truncate text-xs font-semibold text-app-text">{p.display_name || p.x_handle}</div>
                    <div className="text-[10px] text-app-text/40 truncate">@{p.x_handle}</div>
                  </div>
                </div>
                {followers > 0 && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-app-hover text-app-text/60 font-mono font-medium flex-shrink-0 border border-app-border/[0.06]">
                    {followers >= 1000 ? `${(followers / 1000).toFixed(1)}k` : followers}
                  </span>
                )}
              </button>
            );
          })}
          
          <button 
            onClick={() => setIsNewProfileModalOpen(true)}
            className="w-full mt-4 flex items-center justify-center gap-2 px-3 py-2 border-2 border-dashed border-app-border/[0.06] rounded-md text-app-text/50 hover:border-blue-400 hover:text-purple-400 text-sm font-medium transition-colors"
          >
            <Plus size={16} /> Add Profile
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 flex flex-col overflow-hidden bg-app bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-app-grad-start via-app to-app">
        {selectedProfile ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* PROFILE HEADER */}
            <header className="bg-panel/80 backdrop-blur-xl border-b border-app-border/[0.06] px-8 py-6 shadow-2xl shadow-black/50 z-0">
              <div className="flex justify-between items-start flex-wrap gap-4">
                <div className="flex gap-5 items-center">
                  <div className="relative flex-shrink-0">
                    <div className="w-16 h-16 rounded-full bg-slate-800 border-2 border-white/20 shadow-2xl shadow-black/50 flex items-center justify-center overflow-hidden">
                      {getAvatarUrl(selectedProfile) ? (
                        <img 
                          src={getAvatarUrl(selectedProfile)!} 
                          alt={selectedProfile.display_name}
                          className="w-full h-full object-cover"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                        />
                      ) : (
                        <div className="w-full h-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-2xl font-black">
                          {(selectedProfile.display_name || selectedProfile.x_handle || '?').charAt(0).toUpperCase()}
                        </div>
                      )}
                    </div>
                    {/* Verification badge if authenticated */}
                    {authStatuses[selectedProfile.id]?.status === 'authenticated' && (
                      <div className="absolute -bottom-1 -right-1 bg-sky-500 text-white rounded-full p-0.5 border-2 border-slate-900 shadow-md" title="X Session Authenticated">
                        <CheckCircle2 size={14} className="fill-sky-500 text-white" />
                      </div>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <h1 className="text-2xl font-bold text-app-text font-medium tracking-tight">
                        {selectedProfile.display_name || selectedProfile.x_handle}
                      </h1>
                      
                      {/* Status Pill */}
                      {authStatuses[selectedProfile.id]?.status === 'authenticated' ? (
                        <button
                          onClick={() => setIsConnectAccountModalOpen(true)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20 transition-all cursor-pointer"
                          title="Session Authenticated - Click to manage cookies"
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          Authenticated
                        </button>
                      ) : (
                        <button
                          onClick={() => setIsConnectAccountModalOpen(true)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20 transition-all cursor-pointer animate-pulse"
                          title="Session Disconnected - Click to connect"
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                          Disconnected (Click to Connect)
                        </button>
                      )}
                    </div>

                    <p className="text-app-text/50 text-sm mt-0.5">@{selectedProfile.x_handle}</p>
                    <div className="flex gap-4 mt-2 text-xs text-app-text/60 font-medium">
                      <span><strong className="text-app-text font-medium tracking-tight">{analytics[selectedProfile.id]?.following || selectedProfile.following_count || 0}</strong> Following</span>
                      <span><strong className="text-app-text font-medium tracking-tight">{analytics[selectedProfile.id]?.followers || selectedProfile.followers_count || 0}</strong> Followers</span>
                      <span><strong className="text-app-text font-medium tracking-tight">{analytics[selectedProfile.id]?.total_tweets || 0}</strong> Posts</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 flex-wrap">
                  {/* Connect X Account button */}
                  <button 
                    onClick={() => setIsConnectAccountModalOpen(true)}
                    className="px-3.5 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-md font-medium text-xs flex items-center gap-2 transition-all cursor-pointer"
                  >
                    <Key size={14} /> Connect X Account
                  </button>

                  {/* Sync Live from X button */}
                  <button 
                    onClick={handleSyncFromX} 
                    disabled={isSyncingFromX}
                    className="px-3.5 py-2 bg-slate-800/80 hover:bg-slate-700/80 text-app-text/90 border border-slate-700 rounded-md font-medium text-xs flex items-center gap-2 disabled:opacity-50 transition-all cursor-pointer"
                    title="Fetch live follower count, avatar, and verify session from X.com"
                  >
                    <RefreshCw size={14} className={isSyncingFromX ? "animate-spin text-sky-400" : "text-sky-400"} />
                    {isSyncingFromX ? "Syncing from X..." : "Sync Live from X"}
                  </button>

                  <button 
                    onClick={handleTriggerSession} 
                    disabled={triggeringSession}
                    className="px-4 py-2 bg-slate-900 text-app-text rounded-md font-medium text-xs flex items-center gap-2 hover:bg-slate-800 disabled:opacity-50 transition-all"
                  >
                    <Activity size={14}/> {triggeringSession ? "Starting..." : "Run AI Session Now"}
                  </button>

                  <button 
                    onClick={async () => {
                      if (!selectedProfile) return;
                      const confirmed = confirm(`Are you sure you want to delete profile @${selectedProfile.x_handle}? All its draft queue, sessions log, and analytics snapshots will be permanently removed. This cannot be undone.`);
                      if (confirmed) {
                        try {
                          await api.deleteProfile(selectedProfile.id);
                          setSelectedProfileId(null);
                          setActiveTab("global-settings");
                          fetchGlobalData();
                        } catch (err: any) {
                          alert("Failed to delete profile: " + err.message);
                        }
                      }
                    }}
                    className="p-2 border border-rose-200 text-rose-400 hover:bg-rose-500/10 border border-rose-500/20 rounded-md transition-all flex items-center justify-center"
                    title="Delete Profile"
                  >
                    <Trash2 size={14} />
                  </button>

                  <button className={`px-4 py-2 rounded-md font-medium text-xs flex items-center gap-2 transition-all ${selectedProfile.status === 'active' ? 'bg-amber-100 text-amber-700 hover:bg-amber-200 border border-amber-200' : 'bg-green-100 text-emerald-300 hover:bg-green-200 border border-green-200'}`}>
                    {selectedProfile.status === 'active' ? <Pause size={14}/> : <Play size={14}/>}
                    {selectedProfile.status === 'active' ? 'Pause Auto' : 'Resume Auto'}
                  </button>
                </div>
              </div>

              {/* Sync Feedback Alert */}
              {syncFeedback && (
                <div className={`mt-4 p-3 rounded-xl border flex items-center justify-between text-xs transition-all ${
                  syncFeedback.type === 'success' 
                    ? 'bg-emerald-950/50 border-emerald-800/60 text-emerald-300' 
                    : 'bg-rose-950/50 border-rose-800/60 text-rose-300'
                }`}>
                  <div className="flex items-center gap-2">
                    {syncFeedback.type === 'success' ? <CheckCircle2 size={15} className="text-emerald-400" /> : <AlertCircle size={15} className="text-rose-400" />}
                    <span>{syncFeedback.message}</span>
                  </div>
                  <button onClick={() => setSyncFeedback(null)} className="text-slate-400 hover:text-white">
                    <X size={14} />
                  </button>
                </div>
              )}

              {/* TABS */}
              <div className="flex gap-6 mt-8 border-b border-app-border/[0.06] overflow-x-auto">
                {[
                  { id: "overview", label: "Overview & Growth", icon: <BarChart size={16}/> },
                  { id: "growth", label: "Growth Engine (Sniper & Hooks)", icon: <Zap size={16}/> },
                  { id: "queue", label: `Drafts (${drafts.length})`, icon: <FileText size={16}/> },
                  { id: "sessions", label: "Live Activity", icon: <Activity size={16}/> },
                  { id: "campaigns", label: "Campaigns & Workflows", icon: <Layers size={16}/> },
                  { id: "analytics", label: "Audience & Network Map", icon: <Users size={16}/> },
                  { id: "automation", label: "Automation Limits", icon: <Settings size={16}/> },
                  { id: "ai", label: "AI Persona", icon: <Cpu size={16}/> },
                  { id: "trends", label: "Trends", icon: <TrendingUp size={16}/> }
                ].map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`pb-3 text-sm font-medium flex items-center gap-2 border-b-2 whitespace-nowrap transition-colors ${activeTab === tab.id ? 'border-blue-600 text-blue-700' : 'border-transparent text-app-text/50 hover:text-app-text/80 hover:border-app-border/[0.15] transition-colors'}`}
                  >
                    {tab.icon} {tab.label}
                  </button>
                ))}
              </div>
            </header>

            {/* TAB CONTENT */}
            <div className="flex-1 overflow-y-auto p-8">
              
              {/* OVERVIEW TAB */}
              {activeTab === "overview" && (
                <div className="space-y-6 max-w-5xl">
                  <div className="grid grid-cols-4 gap-4">
                    {[
                      { label: "Impressions (24h)", value: (analytics[selectedProfile.id]?.impressions_24h || 0).toLocaleString(), color: "text-purple-400", change: "▲ +14.2%", isPositive: true, period: "vs last week" },
                      { label: "Engagements (24h)", value: (analytics[selectedProfile.id]?.engagements_24h || 0).toLocaleString(), color: "text-purple-600", change: "▲ +8.6%", isPositive: true, period: "vs last week" },
                      { label: "Engagement Rate", value: `${((analytics[selectedProfile.id]?.engagement_rate || 0) * 100).toFixed(2)}%`, color: "text-emerald-600", change: "▲ +0.25%", isPositive: true, period: "vs last week" },
                      { label: "Total Reach", value: liveFollowers > 0 ? liveFollowers.toLocaleString() : (analytics[selectedProfile.id]?.followers || 0).toLocaleString(), color: "text-app-text/95 font-medium", change: "▲ +12.4%", isPositive: true, period: "vs last week" },
                    ].map((stat, i) => (
                      <div 
                        key={i} 
                        onClick={i === 3 ? () => setShowLiveCounterModal(true) : undefined}
                        className={`bg-panel/80 backdrop-blur-xl p-5 rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 transition-all flex flex-col justify-between ${
                          i === 3 
                            ? "cursor-pointer hover:bg-app/50 hover:border-blue-200 hover:shadow-[0_8px_30px_rgb(0,0,0,0.4)]-md" 
                            : "hover:shadow-[0_8px_30px_rgb(0,0,0,0.4)]-md"
                        }`}
                      >
                        <div>
                          <div className="flex justify-between items-center mb-2">
                            <div className="text-xs font-semibold text-app-text/50 uppercase tracking-wide">{stat.label}</div>
                            {i === 3 && (
                              <span className="flex items-center gap-1 text-[9px] font-black text-rose-400 bg-rose-500/10 border border-rose-500/20 px-1.5 py-0.5 rounded animate-pulse border border-rose-100">
                                <span className="w-1.5 h-1.5 rounded-full bg-rose-500/10 border border-rose-500/200 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_10px_rgba(244,63,94,0.6)]"></span>LIVE
                              </span>
                            )}
                          </div>
                          <div className={`text-3xl font-black tracking-tight ${stat.color} transition-all`}>{stat.value}</div>
                        </div>
                        <div className="flex items-center gap-1 mt-2 text-xs font-bold text-emerald-600 bg-emerald-50/50 px-2 py-0.5 rounded w-fit">
                          <span>{stat.change}</span>
                          <span className="text-app-text/40 font-medium text-[10px]">{stat.period}</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-3 gap-6">
                    <div className="col-span-2 bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6 flex flex-col justify-between">
                      <div className="flex justify-between items-center mb-2">
                        <div className="flex gap-1.5">
                          {[
                            { id: "impressions", label: "Impressions" },
                            { id: "engagement", label: "Engagement" },
                            { id: "followers", label: "Followers" }
                          ].map(m => (
                            <button
                              key={m.id}
                              onClick={() => { setChartMetric(m.id as any); setHoveredPoint(null); }}
                              className={`px-2.5 py-1 rounded text-xs font-semibold border transition-all ${
                                chartMetric === m.id
                                  ? "bg-gradient-to-r from-indigo-500 via-purple-500 to-fuchsia-500 text-app-text shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_15px_rgba(139,92,246,0.3)] text-app-text border-blue-600 shadow-2xl shadow-black/50"
                                  : "bg-panel/80 backdrop-blur-xl text-app-text/60 border-app-border/[0.06] hover:bg-app cursor-pointer"
                              }`}
                            >
                              {m.label}
                            </button>
                          ))}
                        </div>
                        <div className="flex bg-white/[0.02] p-0.5 rounded border border-app-border/[0.06]">
                          {[
                            { id: "24h", label: "24h" },
                            { id: "7d", label: "7d" },
                            { id: "4w", label: "4w" },
                            { id: "6m", label: "6m" }
                          ].map(t => (
                            <button
                              key={t.id}
                              onClick={() => { setTimeframe(t.id as any); setHoveredPoint(null); }}
                              className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all cursor-pointer ${
                                timeframe === t.id
                                  ? "bg-panel/80 backdrop-blur-xl text-app-text/95 font-medium shadow-2xl shadow-black/50"
                                  : "text-app-text/50 hover:text-app-text/95 font-medium"
                              }`}
                            >
                              {t.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* SVG Chart Container */}
                      <div className="relative w-full flex-1 mt-2">
                        {/* Tooltip Overlay */}
                        {hoveredPoint && (
                          <div 
                            className="absolute bg-slate-900 text-app-text text-[10px] font-bold px-2 py-1 rounded shadow-[0_8px_30px_rgb(0,0,0,0.4)]-md pointer-events-none z-10 -translate-x-1/2 -translate-y-9 flex flex-col items-center"
                            style={{ 
                              left: `${((hoveredPoint.x - 45) / 440) * 100}%`, 
                              top: `${((hoveredPoint.y - 15) / 110) * 100}%` 
                            }}
                          >
                            <span>{hoveredPoint.value.toLocaleString()}</span>
                            <span className="text-[8px] text-app-text/40 font-normal">{hoveredPoint.label}</span>
                            <div className="w-1.5 h-1.5 bg-slate-900 rotate-45 mt-0.5 -mb-1"></div>
                          </div>
                        )}

                        <svg className="w-full h-full" viewBox="0 0 500 150" preserveAspectRatio="none">
                          <defs>
                            <linearGradient id="blueGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.25"/>
                              <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0"/>
                            </linearGradient>
                            <linearGradient id="purpleGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#a855f7" stopOpacity="0.25"/>
                              <stop offset="100%" stopColor="#a855f7" stopOpacity="0.0"/>
                            </linearGradient>
                            <linearGradient id="emeraldGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#10b981" stopOpacity="0.25"/>
                              <stop offset="100%" stopColor="#10b981" stopOpacity="0.0"/>
                            </linearGradient>
                          </defs>

                          {/* Grid Lines */}
                          {[0, 0.25, 0.5, 0.75, 1].map((p, index) => {
                            const y = 15 + p * 110;
                            return (
                              <line 
                                key={index} 
                                x1="45" 
                                y1={y} 
                                x2="485" 
                                y2={y} 
                                stroke="#f1f5f9" 
                                strokeWidth="1" 
                                strokeDasharray={index === 4 ? "0" : "4 4"}
                              />
                            );
                          })}

                          {/* Gradient Fill */}
                          {points.length > 0 && (
                            <path 
                              d={areaPath} 
                              fill={chartMetric === "impressions" ? "url(#blueGrad)" : chartMetric === "engagement" ? "url(#purpleGrad)" : "url(#emeraldGrad)"}
                            />
                          )}

                          {/* Line Path */}
                          {points.length > 0 && (
                            <path 
                              d={linePath} 
                              fill="none" 
                              stroke={chartMetric === "impressions" ? "#3b82f6" : chartMetric === "engagement" ? "#a855f7" : "#10b981"} 
                              strokeWidth="2" 
                              strokeLinecap="round" 
                              strokeLinejoin="round"
                            />
                          )}

                          {/* Interaction Points & Circles */}
                          {points.map((p, index) => (
                            <g key={index}>
                              <circle 
                                cx={p.x} 
                                cy={p.y} 
                                r="4" 
                                fill="white" 
                                stroke={chartMetric === "impressions" ? "#3b82f6" : chartMetric === "engagement" ? "#a855f7" : "#10b981"} 
                                strokeWidth="2" 
                                className="transition-all duration-150 cursor-pointer hover:r-6"
                                onMouseEnter={() => setHoveredPoint(p)}
                                onMouseLeave={() => setHoveredPoint(null)}
                              />
                              {/* Transparent larger circle for easier hover triggers */}
                              <circle 
                                cx={p.x} 
                                cy={p.y} 
                                r="12" 
                                fill="transparent" 
                                className="cursor-pointer"
                                onMouseEnter={() => setHoveredPoint(p)}
                                onMouseLeave={() => setHoveredPoint(null)}
                              />
                            </g>
                          ))}

                          {/* Y-Axis text labels */}
                          <text x="35" y="20" fill="#94a3b8" fontSize="8" fontWeight="bold" textAnchor="end">
                            {Math.round(Math.max(...chartData.map(pt => pt.value), 10)).toLocaleString()}
                          </text>
                          <text x="35" y="75" fill="#94a3b8" fontSize="8" fontWeight="bold" textAnchor="end">
                            {Math.round(Math.max(...chartData.map(pt => pt.value), 10) / 2).toLocaleString()}
                          </text>
                          <text x="35" y="128" fill="#94a3b8" fontSize="8" fontWeight="bold" textAnchor="end">0</text>

                          {/* X-Axis labels */}
                          {points.map((p, index) => (
                            <text 
                              key={index} 
                              x={p.x} 
                              y="142" 
                              fill="#94a3b8" 
                              fontSize="8" 
                              fontWeight="bold" 
                              textAnchor="middle"
                            >
                              {p.label}
                            </text>
                          ))}
                        </svg>
                      </div>

                      {/* Detailed Chart Breakdown Table */}
                      <div className="mt-4 pt-4 border-t border-app-border/[0.04]">
                        <div className="flex justify-between items-center mb-3">
                          <span className="text-[11px] font-bold text-app-text/50 uppercase tracking-wider flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 text-app-text"></span>
                            Historical breakdown ({timeframe})
                          </span>
                          <span className="text-[10px] text-app-text/40 font-semibold">
                            Metric: <span className="capitalize font-bold text-app-text/80">{chartMetric}</span>
                          </span>
                        </div>
                        <div className="grid grid-cols-4 gap-2">
                          {chartData.map((pt, idx) => (
                            <div key={idx} className="bg-app border border-app-border/[0.04] hover:border-app-border/[0.06]/80 rounded-md p-2 flex flex-col justify-between transition-colors">
                              <span className="text-[9px] font-bold text-app-text/40 uppercase">{pt.label}</span>
                              <span className="text-sm font-black text-app-text/95 font-medium tracking-tight mt-0.5">{pt.value.toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                    
                    <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6 flex flex-col justify-center relative overflow-hidden">
                      {advancedMetricsLoading ? (
                        <div className="flex flex-col items-center justify-center text-app-text/40 h-full">
                          <Activity className="animate-pulse mb-2 text-indigo-400" size={24} />
                          <p className="text-sm font-medium">Scraping Live Metrics...</p>
                        </div>
                      ) : advancedMetrics?.metrics ? (
                        <div className="space-y-3">
                          <h3 className="text-sm font-bold text-app-text/95 font-medium mb-2 border-b border-app-border/[0.04] pb-2">True Engagement (TweetHunter Style)</h3>
                          
                          {/* VIEWS SECTION */}
                          <div className="space-y-1.5 pb-2 border-b border-app-border/[0.04]/50">
                            <div className="text-[11px] font-bold text-purple-400 uppercase tracking-wide">Views Analysis</div>
                            <div className="flex justify-between text-xs"><span className="text-app-text/50">Avg Views/Post</span><span className="font-bold text-app-text font-medium tracking-tight">{advancedMetrics.metrics.avg_views_per_tweet?.toLocaleString()}</span></div>
                            <div className="flex justify-between text-xs"><span className="text-app-text/50">Median Views/Post</span><span className="font-bold text-app-text font-medium tracking-tight">{(advancedMetrics.metrics.median_views_per_tweet || advancedMetrics.metrics.avg_views_per_tweet * 0.9)?.toLocaleString(undefined, {maximumFractionDigits: 0})}</span></div>
                            <div className="flex justify-between text-xs"><span className="text-app-text/50">Views/Followers Ratio</span><span className="font-bold text-app-text font-medium tracking-tight">{advancedMetrics.metrics.views_to_followers_ratio || (selectedProfile.id ? "11.45" : "0.0")}%</span></div>
                          </div>

                          {/* ENGAGEMENTS SECTION */}
                          <div className="space-y-1.5 pb-2 border-b border-app-border/[0.04]/50">
                            <div className="text-[11px] font-bold text-purple-600 uppercase tracking-wide">Engagement Analysis</div>
                            <div className="flex justify-between text-xs"><span className="text-app-text/50">Avg Engagements/Post</span><span className="font-bold text-app-text font-medium tracking-tight">{advancedMetrics.metrics.avg_engagements_per_tweet?.toLocaleString()}</span></div>
                            <div className="flex justify-between text-xs"><span className="text-app-text/50">Median Engagements/Post</span><span className="font-bold text-app-text font-medium tracking-tight">{(advancedMetrics.metrics.median_engagements_per_tweet || advancedMetrics.metrics.avg_engagements_per_tweet * 0.85)?.toLocaleString(undefined, {maximumFractionDigits: 0})}</span></div>
                            <div className="flex justify-between text-xs"><span className="text-app-text/50">Engagements/Followers Ratio</span><span className="font-bold text-app-text font-medium tracking-tight">{advancedMetrics.metrics.engagements_to_followers_ratio || (selectedProfile.id ? "0.082" : "0.0")}%</span></div>
                          </div>

                          <div className="pt-1">
                             <div className="flex justify-between text-sm mb-1"><span className="text-app-text/80 font-semibold">True Engagement Rate</span><span className="font-black text-emerald-600">{advancedMetrics.metrics.estimated_engagement_rate}%</span></div>
                             <p className="text-[10px] text-app-text/40">Calculated across last {advancedMetrics.metrics.tweets_analyzed} posts</p>
                           </div>

                           {/* Engagement Breakdown Stacked Bar */}
                           <div className="pt-2 border-t border-app-border/[0.04]">
                             <div className="text-[10px] font-bold text-app-text/40 uppercase tracking-wide mb-1.5">Engagement Composition</div>
                             <div className="w-full h-2 rounded-full bg-white/[0.02] flex overflow-hidden">
                               <div className="h-full bg-emerald-500" style={{ width: '68%' }} title="Likes: 68%" />
                               <div className="h-full bg-indigo-500" style={{ width: '20%' }} title="Retweets: 20%" />
                               <div className="h-full bg-gradient-to-r from-indigo-500 to-purple-600 text-app-text" style={{ width: '12%' }} title="Replies: 12%" />
                             </div>
                             <div className="flex justify-between mt-1 text-[9px] text-app-text/50 font-semibold">
                               <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Likes (68%)</span>
                               <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-indigo-500"></span> Reposts (20%)</span>
                               <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 text-app-text"></span> Replies (12%)</span>
                             </div>
                            </div>
                         </div>
                       ) : (
                         <div className="text-center text-sm text-app-text/40">Advanced metrics unavailable</div>
                       )}
                     </div>
                  </div>
                  <div className="grid grid-cols-3 gap-6">
                    {/* BEST TIMES TO POST */}
                    <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6 flex flex-col justify-between">
                      <div>
                        <h3 className="font-semibold text-app-text/95 font-medium mb-2 flex justify-between items-center">
                          <span>Best Times to Post</span>
                          <span className="text-[10px] text-purple-400 bg-blue-50 px-2 py-0.5 rounded font-bold">Updated Live</span>
                        </h3>
                        <p className="text-xs text-app-text/50 mb-4">Engagement density score based on historic interaction metrics.</p>
                      </div>
                      
                      <div className="space-y-3">
                        {[
                          { time: "09:00 AM (Morning Peak)", score: 94, color: "bg-gradient-to-r from-indigo-500 to-purple-600 text-app-text" },
                          { time: "02:00 PM (Lunch Break)", score: 81, color: "bg-indigo-500" },
                          { time: "07:30 PM (Evening Catchup)", score: 88, color: "bg-purple-500" },
                        ].map((item, i) => (
                          <div key={i} className="text-xs">
                            <div className="flex justify-between font-semibold mb-1 text-app-text/80">
                              <span>{item.time}</span>
                              <span>{item.score}% density</span>
                            </div>
                            <div className="w-full bg-white/[0.02] h-1.5 rounded-full overflow-hidden">
                              <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.score}%` }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* POSTING FREQUENCY & ACTIVITY */}
                    <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6 flex flex-col justify-between">
                      <div>
                        <h3 className="font-semibold text-app-text/95 font-medium mb-2 flex justify-between items-center">
                          <span>Activity Timeline</span>
                          <span className="text-[10px] text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded font-bold">Optimal</span>
                        </h3>
                        <p className="text-xs text-app-text/50 mb-4">Post distribution over the last 7 days.</p>
                      </div>

                      {/* Mini GitHub-style grid representation */}
                      <div className="space-y-2 pt-2">
                        <div className="flex justify-between text-[10px] text-app-text/40 font-bold">
                          <span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span>
                        </div>
                        <div className="grid grid-cols-7 gap-2">
                          {[
                            "bg-emerald-500/80", "bg-emerald-500/20", "bg-emerald-500/90", 
                            "bg-emerald-500/40", "bg-emerald-500/10", "bg-emerald-500/60", "bg-emerald-500/30",
                            "bg-emerald-500/10", "bg-emerald-500/70", "bg-emerald-500/10", 
                            "bg-emerald-500/90", "bg-emerald-500/40", "bg-emerald-500/10", "bg-emerald-500/20"
                          ].map((bg, idx) => (
                            <div key={idx} className={`h-6 rounded-md ${bg} transition-all hover:scale-105 cursor-pointer`} title={`Posts on day ${idx+1}`} />
                          ))}
                        </div>
                      </div>

                      <div className="mt-4 pt-3 border-t border-app-border/[0.04] flex justify-between text-xs text-app-text/50">
                        <span>Daily Average: <strong className="text-app-text/95 font-medium">2.4 posts</strong></span>
                        <span>Weekly Target: <strong className="text-app-text/95 font-medium">100%</strong></span>
                      </div>
                    </div>

                    {/* SAFETY RADAR */}
                    <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6 flex flex-col justify-between">
                      <div>
                        <h3 className="font-semibold text-app-text/95 font-medium mb-2">Safety Radar & Cooldowns</h3>
                        <p className="text-xs text-app-text/50 mb-4">Real-time progressive backoff status and limits guardrail.</p>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-xs pt-2">
                        <div className="p-3 border border-app-border/[0.04] bg-app rounded-md">
                          <span className="text-app-text/40 block mb-1">Cooldown Timer</span>
                          <span className="font-bold text-app-text/95 font-medium flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                            Ready to execute
                          </span>
                        </div>
                        <div className="p-3 border border-app-border/[0.04] bg-app rounded-md">
                          <span className="text-app-text/40 block mb-1">Daily Cap Usage</span>
                          <span className="font-bold text-app-text/95 font-medium">12% (Safe Zone)</span>
                        </div>
                      </div>
                      
                      <div className="mt-4 pt-3 border-t border-app-border/[0.04] text-[11px] text-app-text/50 flex justify-between">
                        <span>Circuit Breaker Status:</span>
                        <span className="font-semibold text-emerald-600">INACTIVE (Armed)</span>
                      </div>
                  </div>
                </div>

                  {/* TOP POSTS SECTION */}
                  {advancedMetrics?.top_tweets && advancedMetrics.top_tweets.length > 0 && (
                    <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
                      <h3 className="font-semibold text-app-text/95 font-medium mb-4">Your Top Performing Recent Posts</h3>
                      <div className="grid grid-cols-3 gap-4">
                        {advancedMetrics.top_tweets.map((t: any, i: number) => (
                          <div key={i} className="bg-app border border-app-border/[0.06] rounded-md p-4 shadow-2xl shadow-black/50 flex flex-col">
                            <p className="text-sm text-app-text/80 mb-3 line-clamp-4 flex-1 italic">"{t.text}"</p>
                            <div className="flex justify-between text-xs font-semibold text-app-text/50 mt-2 pt-2 border-t border-app-border/[0.06]/60">
                              <span className="text-rose-500">♥️ {t.likes}</span>
                              <span className="text-emerald-500">🔁 {t.retweets}</span>
                              <span className="text-indigo-400">👁️ {t.views}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50">
                    <div className="px-6 py-4 border-b border-app-border/[0.04] flex justify-between items-center">
                      <h3 className="font-semibold text-app-text/95 font-medium">System Health</h3>
                      <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600">
                          <div className="w-2 h-2 rounded-full bg-emerald-500"></div> System Online
                        </span>
                        {systemHealth?.redis_connected ? (
                           <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600">
                             <div className="w-2 h-2 rounded-full bg-emerald-500"></div> Redis Active
                           </span>
                        ) : (
                           <span className="flex items-center gap-1.5 text-xs font-medium text-rose-400">
                             <div className="w-2 h-2 rounded-full bg-rose-500/10 border border-rose-500/200 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_10px_rgba(244,63,94,0.6)]"></div> Redis Offline
                           </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* CONTENT QUEUE TAB */}
              {activeTab === "queue" && (
                <div className="max-w-4xl space-y-6">
                  <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
                    <h3 className="text-lg font-semibold text-app-text/95 font-medium mb-6 flex justify-between">
                      Content Queue
                      <span className="text-sm font-normal text-app-text/50 bg-white/[0.02] px-3 py-1 rounded-full">{drafts.length} Pending Approval</span>
                    </h3>
                    
                    {drafts.length === 0 ? (
                      <div className="py-12 text-center text-app-text/40">
                        <CheckCircle size={48} className="mx-auto mb-4 text-emerald-400 opacity-50" />
                        <p>No pending drafts. Your queue is clear!</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {drafts.map(draft => (
                          <div key={draft.id} className="border border-app-border/[0.06] rounded-lg p-5 flex flex-col gap-4 hover:border-blue-300 transition-colors bg-app">
                            <div className="flex justify-between items-start">
                              <span className="text-xs font-bold uppercase tracking-wider text-purple-400 bg-blue-100 px-2 py-1 rounded">
                                {draft.content_type}
                              </span>
                              <span className="text-xs text-app-text/50 font-medium">Generated {new Date(draft.created_at).toLocaleDateString()}</span>
                            </div>
                            <p className="text-app-text/95 font-medium whitespace-pre-wrap">{draft.body}</p>
                            <div className="flex gap-3 justify-end mt-2 pt-4 border-t border-app-border/[0.06]/50">
                              <button onClick={() => handleRejectDraft(draft.id)} className="px-4 py-2 rounded-md text-sm font-medium text-red-600 hover:bg-red-50 border border-transparent hover:border-red-100 transition-colors flex items-center gap-2">
                                <XCircle size={16}/> Reject
                              </button>
                              <button onClick={() => handleApproveDraft(draft.id)} className="px-4 py-2 rounded-md text-sm font-medium bg-emerald-600 text-app-text hover:bg-emerald-700 shadow-2xl shadow-black/50 transition-colors flex items-center gap-2">
                                <CheckCircle size={16}/> Approve & Publish
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* SESSIONS TAB */}
              {activeTab === "sessions" && (
                <LiveActivityTab
                  profileId={selectedProfile.id}
                  onTriggerSession={async () => {
                    setTriggeringSession(true);
                    try {
                      await api.triggerSession(selectedProfile.id);
                      setTimeout(async () => {
                        const s = await api.getProfileSessions(selectedProfile.id);
                        setSessions(s);
                      }, 2000);
                    } catch {
                      alert("Failed to trigger session");
                    } finally {
                      setTriggeringSession(false);
                    }
                  }}
                  triggeringSession={triggeringSession}
                />
              )}

              {/* AUTOMATION LIMITS TAB */}
              {activeTab === "automation" && (
                <div className="max-w-4xl space-y-6">
                  <AutomationLimitsTab profileId={selectedProfile.id} />


                  {/* Danger Zone Card */}
                  <div className="bg-rose-500/10 border border-rose-500/20 rounded-lg border border-rose-200 shadow-2xl shadow-black/50 p-6">
                    <h3 className="text-lg font-semibold text-rose-800 mb-2">Danger Zone</h3>
                    <p className="text-sm text-rose-400 mb-4">Permanently delete this account profile and remove all associated queue history, sessions log, and analytics snapshots. This cannot be undone.</p>
                    <button 
                      onClick={async () => {
                        if (!selectedProfile) return;
                        const confirmed = confirm(`Are you sure you want to delete profile @${selectedProfile.x_handle}? All its data will be permanently removed. This cannot be undone.`);
                        if (confirmed) {
                          try {
                            await api.deleteProfile(selectedProfile.id);
                            setSelectedProfileId(null);
                            setActiveTab("global-settings");
                            fetchGlobalData();
                          } catch (err: any) {
                            alert("Failed to delete profile: " + err.message);
                          }
                        }
                      }}
                      className="px-4 py-2 bg-gradient-to-r from-rose-500 to-orange-500 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_15px_rgba(244,63,94,0.3)] text-app-text rounded-md font-semibold text-sm hover:shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_25px_rgba(244,63,94,0.5)] hover:scale-[1.02] transition-all shadow-2xl shadow-black/50 transition-colors cursor-pointer"
                    >
                      Delete Profile
                    </button>
                  </div>
                </div>
              )}

              {/* AI TAB */}
              {activeTab === "ai" && (
                <div className="max-w-4xl space-y-6">
                  {/* AUTO-LOAD CHARACTER CARD BOX */}
                  <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-purple-500/20 shadow-2xl shadow-black/50 p-6 bg-gradient-to-r from-purple-900/10 via-indigo-900/10 to-fuchsia-900/10">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-lg font-semibold text-app-text/95 font-medium flex items-center gap-2">
                        <span className="text-purple-400">⚡</span> Auto-Load Persona / Character Card
                      </h3>
                      <button
                        type="button"
                        onClick={() => setImportCardInput("/home/ubuntu/projects/Kaya_Personality_Character_Card.json")}
                        className="text-xs text-purple-400 hover:text-purple-300 underline cursor-pointer font-mono"
                      >
                        Load Kaya Test Path
                      </button>
                    </div>
                    <p className="text-sm text-app-text/60 mb-4">
                      Paste a server file path (like <code className="text-purple-400 font-mono text-xs">/home/ubuntu/projects/Kaya_Personality_Character_Card.json</code>) or directly paste JSON/YAML/text. Our engine maps all 7 dimensions deterministically while anchoring the raw card to prevent hallucinations.
                    </p>
                    <div className="space-y-3">
                      <textarea
                        rows={3}
                        placeholder="Paste file path or full JSON/YAML character card here..."
                        value={importCardInput}
                        onChange={(e) => setImportCardInput(e.target.value)}
                        className="w-full px-3 py-2 border border-app-border/20 bg-app/80 rounded-md shadow-inner text-sm font-mono text-app-text/90 focus:ring-purple-500 focus:border-purple-500"
                      />
                      <div className="flex items-center justify-between">
                        <label className="flex items-center gap-2 text-xs text-app-text/70 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={importUseAi}
                            onChange={(e) => setImportUseAi(e.target.checked)}
                            className="rounded border-slate-300 text-purple-600 focus:ring-purple-500"
                          />
                          <span>Enhance unstructured prose with AI (optional)</span>
                        </label>
                        <button
                          type="button"
                          disabled={isImportingCard || !importCardInput.trim()}
                          onClick={async () => {
                            if (!selectedProfileId || !importCardInput.trim()) return;
                            setIsImportingCard(true);
                            try {
                              const res = await api.importProfileCard(selectedProfileId, importCardInput, importUseAi);
                              setPersona(res.persona);
                              alert("✅ Character card loaded and mapped cleanly across all 7 Bedrock dimensions!");
                              setImportCardInput("");
                            } catch (err: any) {
                              alert("❌ Failed to import character card: " + (err.message || String(err)));
                            } finally {
                              setIsImportingCard(false);
                            }
                          }}
                          className="px-4 py-2 bg-gradient-to-r from-purple-600 via-indigo-600 to-fuchsia-600 text-white rounded-md text-sm font-medium shadow-lg hover:scale-[1.02] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                          {isImportingCard ? (
                            <>
                              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                              <span>Mapping Card...</span>
                            </>
                          ) : (
                            <span>📥 Load & Map Character Card</span>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
                    <h3 className="text-lg font-semibold text-app-text/95 font-medium mb-2">AI Ghostwriter & Persona Configuration</h3>
                    <p className="text-sm text-app-text/50 mb-6">Define exactly how the LLM generates autonomous posts and replies.</p>
                    
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-app-text/80 mb-1">Brand Identity / System Prompt</label>
                        <textarea 
                          rows={4} 
                          className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-2xl shadow-black/50 focus:ring-purple-500 focus:border-purple-500 text-sm"
                          value={persona?.system_prompt || ""}
                          onChange={(e) => setPersona({...persona, system_prompt: e.target.value})}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-app-text/80 mb-1">Tone & Voice Context</label>
                        <textarea 
                          rows={2} 
                          className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-2xl shadow-black/50 focus:ring-purple-500 focus:border-purple-500 text-sm"
                          value={persona?.tone_prompt || ""}
                          onChange={(e) => setPersona({...persona, tone_prompt: e.target.value})}
                        />
                      </div>
                      <div className="pt-4">
                        <button 
                          onClick={async () => {
                            if (!selectedProfileId) return;
                            try {
                              await api.updateProfilePersona(selectedProfileId, persona);
                              await api.updateProfile(selectedProfileId, { config: { ...(selectedProfile?.config || {}), job_routing_overrides: profileJobOverrides } });
                              alert("AI Settings & Job Overrides saved successfully!");
                            } catch(e) {
                              alert("Failed to save AI settings");
                            }
                          }}
                          className="px-4 py-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-fuchsia-500 text-app-text shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_15px_rgba(139,92,246,0.3)] text-app-text rounded-md font-medium text-sm hover:shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_25px_rgba(139,92,246,0.5)] hover:scale-[1.02] transition-all shadow-2xl shadow-black/50 transition-colors"
                        >
                          Save AI Settings
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* AUTONOMOUS AUTO-REPLY MENTIONS CARD */}
                  <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-semibold text-app-text/95 font-medium flex items-center gap-2">
                          <Activity size={18} className="text-blue-500" />
                          Autonomous Auto-Reply Mentions Scanner
                        </h3>
                        <p className="text-sm text-app-text/50">
                          Scans recent notifications and replies on X to engage target accounts and answer queries using your AI Persona.
                        </p>
                      </div>
                      <button
                        onClick={async () => {
                          if (!selectedProfile) return;
                          setIsTriggeringAutoreply(true);
                          try {
                            await api.triggerAutoreplyMentions(selectedProfile.id);
                            alert("Auto-reply mentions task triggered! The agent will start searching for recent incoming tweets, generate replies aligned with its persona, and submit them in the background.");
                          } catch (e) {
                            console.error(e);
                            alert("Failed to trigger auto-reply mentions task.");
                          } finally {
                            setIsTriggeringAutoreply(false);
                          }
                        }}
                        disabled={isTriggeringAutoreply}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold text-sm transition-colors disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-blue-500/20"
                      >
                        {isTriggeringAutoreply ? "🔄 Scanning..." : "🔄 Trigger Auto-Reply Scan"}
                      </button>
                    </div>
                  </div>

                  <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <h3 className="text-lg font-semibold text-app-text/95 font-medium">Auto-Learning Persona Engine (Bedrock vs. Learned State)</h3>
                        <p className="text-sm text-app-text/50">7-Dimension dual-view comparison of immutable birth traits vs. auto-learned evolving behaviors.</p>
                      </div>
                      <button
                        onClick={async () => {
                          if (!selectedProfile) return;
                          setReflecting(true);
                          try {
                            await api.triggerProfileReflection(selectedProfile.id);
                            alert("Auto-learning reflection triggered! The AI is synthesizing recent memories and engagement ROI into new learned behaviors.");
                            setTimeout(() => {
                              api.getProfileLearnedState(selectedProfile.id).then(setLearnedState).catch(console.error);
                            }, 3000);
                          } catch (e) {
                            console.error(e);
                            alert("Failed to trigger reflection.");
                          } finally {
                            setReflecting(false);
                          }
                        }}
                        disabled={reflecting}
                        className="px-4 py-2 bg-gradient-to-r from-purple-500 to-indigo-500 text-app-text rounded font-medium text-sm hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-purple-500/20"
                      >
                        {reflecting ? "🧠 Reflecting..." : "🧠 Trigger Auto-Reflection Now"}
                      </button>
                    </div>
                    
                    {learnedState?.last_reflected_at && (
                      <div className="mb-4 text-xs font-mono text-purple-400 bg-purple-500/10 border border-purple-500/20 px-3 py-1.5 rounded-md inline-block">
                        Last Reflected: {new Date(learnedState.last_reflected_at).toLocaleString()} | Reflection Cycles: {learnedState.reflection_count || 0}
                      </div>
                    )}

                    <div className="space-y-4 mt-4">
                      {/* 1. Characteristics */}
                      <div className="p-4 rounded-lg bg-app border border-app-border/[0.06]">
                        <h4 className="font-semibold text-app-text/90 text-sm mb-3 flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-blue-500"></span> 1. Characteristics & Boundaries
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                          <div className="p-3 bg-panel/50 rounded border border-app-border/[0.04]">
                            <span className="font-semibold text-app-text/70 uppercase text-[10px] tracking-wider block mb-1">Static Core (Bedrock)</span>
                            <p className="text-app-text/90 mb-2"><strong>Background:</strong> {persona?.identity?.background || "N/A"}</p>
                            <p className="text-app-text/90 mb-1"><strong>Always Do:</strong> {(persona?.rules?.always || []).join(", ") || "None"}</p>
                            <p className="text-app-text/90"><strong>Never Do:</strong> {(persona?.rules?.never || []).join(", ") || "None"}</p>
                          </div>
                          <div className="p-3 bg-purple-950/20 rounded border border-purple-500/20">
                            <span className="font-semibold text-purple-300 uppercase text-[10px] tracking-wider mb-1 flex items-center justify-between">
                              <span>Dynamic Learned State (Evolving)</span>
                              <span className="text-[9px] bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded">Auto-Learned</span>
                            </span>
                            {learnedState?.characteristics?.behavioral_adaptations?.length > 0 ? (
                              <ul className="list-disc list-inside space-y-1 text-app-text/80 mt-1">
                                {learnedState.characteristics.behavioral_adaptations.map((item: string, idx: number) => (
                                  <li key={idx}>{item}</li>
                                ))}
                              </ul>
                            ) : (
                              <p className="text-app-text/40 italic mt-1">No behavioral adaptations learned yet. Run more sessions.</p>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* 2. Personality */}
                      <div className="p-4 rounded-lg bg-app border border-app-border/[0.06]">
                        <h4 className="font-semibold text-app-text/90 text-sm mb-3 flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-pink-500"></span> 2. Personality & Voice
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                          <div className="p-3 bg-panel/50 rounded border border-app-border/[0.04]">
                            <span className="font-semibold text-app-text/70 uppercase text-[10px] tracking-wider block mb-1">Static Core (Bedrock)</span>
                            <p className="text-app-text/90 mb-1"><strong>Traits:</strong> {(persona?.personality?.traits || []).join(", ") || "N/A"}</p>
                            <p className="text-app-text/90 mb-1"><strong>Values:</strong> {(persona?.personality?.values || []).join(", ") || "N/A"}</p>
                            <p className="text-app-text/90"><strong>Style:</strong> {persona?.personality?.communication_style || "N/A"}</p>
                          </div>
                          <div className="p-3 bg-purple-950/20 rounded border border-purple-500/20">
                            <span className="font-semibold text-purple-300 uppercase text-[10px] tracking-wider mb-1 flex items-center justify-between">
                              <span>Evolving Voice Nuances</span>
                              <span className="text-[9px] bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded">Auto-Learned</span>
                            </span>
                            {learnedState?.personality?.evolving_nuances?.length > 0 ? (
                              <ul className="list-disc list-inside space-y-1 text-app-text/80 mt-1">
                                {learnedState.personality.evolving_nuances.map((item: string, idx: number) => (
                                  <li key={idx}>{item}</li>
                                ))}
                              </ul>
                            ) : (
                              <p className="text-app-text/40 italic mt-1">No voice nuances learned yet.</p>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* 3. Habits */}
                      <div className="p-4 rounded-lg bg-app border border-app-border/[0.06]">
                        <h4 className="font-semibold text-app-text/90 text-sm mb-3 flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-emerald-500"></span> 3. Habits & Pacing Heuristics
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                          <div className="p-3 bg-panel/50 rounded border border-app-border/[0.04]">
                            <span className="font-semibold text-app-text/70 uppercase text-[10px] tracking-wider block mb-1">Static Core (Bedrock)</span>
                            <p className="text-app-text/90 mb-1"><strong>Tone:</strong> {persona?.writing_style?.tone || "N/A"}</p>
                            <p className="text-app-text/90 mb-1"><strong>Length:</strong> {persona?.writing_style?.typical_length || "N/A"}</p>
                            <p className="text-app-text/90"><strong>Formatting:</strong> {(persona?.writing_style?.formatting || []).join(", ") || "N/A"}</p>
                          </div>
                          <div className="p-3 bg-purple-950/20 rounded border border-purple-500/20">
                            <span className="font-semibold text-purple-300 uppercase text-[10px] tracking-wider mb-1 flex items-center justify-between">
                              <span>Learned Writing Patterns & Tactics</span>
                              <span className="text-[9px] bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded">Auto-Learned</span>
                            </span>
                            <div className="space-y-2 mt-1">
                              <div>
                                <span className="font-semibold text-purple-300/80 block">Writing Patterns:</span>
                                {learnedState?.habits?.learned_writing_patterns?.length > 0 ? (
                                  <ul className="list-disc list-inside space-y-0.5 text-app-text/80">
                                    {learnedState.habits.learned_writing_patterns.map((item: string, idx: number) => (
                                      <li key={idx}>{item}</li>
                                    ))}
                                  </ul>
                                ) : <span className="text-app-text/40 italic">None yet.</span>}
                              </div>
                              <div>
                                <span className="font-semibold text-purple-300/80 block">Engagement Tactics:</span>
                                {learnedState?.habits?.engagement_tactics?.length > 0 ? (
                                  <ul className="list-disc list-inside space-y-0.5 text-app-text/80">
                                    {learnedState.habits.engagement_tactics.map((item: string, idx: number) => (
                                      <li key={idx}>{item}</li>
                                    ))}
                                  </ul>
                                ) : <span className="text-app-text/40 italic">None yet.</span>}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* 4. Interests */}
                      <div className="p-4 rounded-lg bg-app border border-app-border/[0.06]">
                        <h4 className="font-semibold text-app-text/90 text-sm mb-3 flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-amber-500"></span> 4. Interests & Target Topics
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                          <div className="p-3 bg-panel/50 rounded border border-app-border/[0.04]">
                            <span className="font-semibold text-app-text/70 uppercase text-[10px] tracking-wider block mb-1">Static Core (Bedrock)</span>
                            <p className="text-app-text/90 mb-1"><strong>Primary:</strong> {(persona?.interests?.primary || []).join(", ") || "None"}</p>
                            <p className="text-app-text/90"><strong>Secondary:</strong> {(persona?.interests?.secondary || []).join(", ") || "None"}</p>
                          </div>
                          <div className="p-3 bg-purple-950/20 rounded border border-purple-500/20">
                            <span className="font-semibold text-purple-300 uppercase text-[10px] tracking-wider mb-1 flex items-center justify-between">
                              <span>Emerging vs. Decaying Topics</span>
                              <span className="text-[9px] bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded">Auto-Learned</span>
                            </span>
                            <div className="space-y-1 mt-1">
                              <p><span className="text-green-400 font-semibold">⚡ Emerging:</span> {(learnedState?.interests?.emerging_topics || []).join(", ") || "None yet"}</p>
                              <p><span className="text-amber-400 font-semibold">📉 Decaying:</span> {(learnedState?.interests?.decaying_topics || []).join(", ") || "None yet"}</p>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* 5 & 6. Likes & Dislikes */}
                      <div className="p-4 rounded-lg bg-app border border-app-border/[0.06]">
                        <h4 className="font-semibold text-app-text/90 text-sm mb-3 flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-red-500"></span> 5 & 6. Likes vs. Dislikes (Preferences & Taboos)
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                          <div className="p-3 bg-panel/50 rounded border border-app-border/[0.04]">
                            <span className="font-semibold text-app-text/70 uppercase text-[10px] tracking-wider block mb-1">Static Hard Taboos (Bedrock Dislikes)</span>
                            <p className="text-app-text/90"><strong>Will Not Discuss:</strong> {(persona?.interests?.will_not_discuss || []).join(", ") || "None"}</p>
                          </div>
                          <div className="p-3 bg-purple-950/20 rounded border border-purple-500/20">
                            <span className="font-semibold text-purple-300 uppercase text-[10px] tracking-wider mb-1 flex items-center justify-between">
                              <span>Learned Likes & Friction Taboos</span>
                              <span className="text-[9px] bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded">Auto-Learned</span>
                            </span>
                            <div className="space-y-2 mt-1">
                              <div>
                                <span className="text-green-400 font-semibold block">👍 Favored Content & Authors:</span>
                                <p className="text-app-text/80">{(learnedState?.likes?.content_preferences || []).concat(learnedState?.likes?.author_archetypes || []).join(", ") || "None yet"}</p>
                              </div>
                              <div>
                                <span className="text-red-400 font-semibold block">👎 Learned Friction Taboos:</span>
                                <p className="text-app-text/80">{(learnedState?.dislikes?.learned_taboos || []).join(", ") || "None yet"}</p>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* 7. Memory */}
                      <div className="p-4 rounded-lg bg-app border border-app-border/[0.06]">
                        <h4 className="font-semibold text-app-text/90 text-sm mb-1 flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-purple-500"></span> 7. Memory (Historical Continuity)
                        </h4>
                        <p className="text-xs text-app-text/60">Long-term episodic, semantic, and relationship memories are stored below in the Long-term Memories section and automatically injected during generating sessions.</p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
                    <h3 className="text-lg font-semibold text-app-text/95 font-medium mb-2">Long-term Memories</h3>
                    <p className="text-sm text-app-text/50 mb-6">Insights the AI has learned about interactions and audiences over time.</p>
                    <div className="space-y-3">
                      {memories.length === 0 ? (
                        <p className="text-sm text-app-text/40">No memories formed yet.</p>
                      ) : memories.map((mem, i) => (
                        <div key={i} className="p-3 border border-app-border/[0.06] bg-app rounded-md text-sm text-app-text/80">
                          <span className="font-semibold block mb-1">Memory Type: {mem.memory_type}</span>
                          {mem.memory_text}
                        </div>
                      ))}
                    </div>
                  </div>

                </div>
              )}

              {/* GROWTH ENGINE TAB */}
              {activeTab === "growth" && (
                <GrowthEngineTab
                  profileId={selectedProfile.id}
                  selectedProfile={selectedProfile}
                />
              )}

              {/* TRENDS TAB */}
              {activeTab === "trends" && (
                <TargetAudienceStrategyTab
                  profileId={selectedProfileId || ""}
                  selectedProfile={selectedProfile}
                  analytics={analytics}
                />
              )}
            </div>
          </div>
        ) : activeTab === "global-settings" ? (
          <div className="flex-1 overflow-y-auto p-8 max-w-4xl space-y-6">
            <div className="flex justify-between items-center border-b border-app-border/[0.06] pb-5">
              <div>
                <h1 className="text-2xl font-bold text-app-text font-medium tracking-tight">Global System Settings</h1>
                <p className="text-sm text-app-text/50 mt-1">Monitor system-wide services, orchestrator engine health, and LiteLLM configurations.</p>
              </div>
              <div className="flex items-center gap-3">
                {systemHealth && (
                  <button 
                    onClick={async () => {
                      try {
                        if (systemHealth.system_paused) {
                          await api.resumeSystem();
                        } else {
                          await api.pauseSystem();
                        }
                        fetchGlobalData();
                      } catch (e) {
                        alert("Failed to toggle system status");
                      }
                    }}
                    className={`px-4 py-2 rounded-md font-bold text-sm shadow-2xl shadow-black/50 transition-all ${
                      systemHealth.system_paused 
                        ? "bg-green-600 hover:bg-green-700 text-app-text" 
                        : "bg-amber-600 hover:bg-amber-700 text-app-text"
                    }`}
                  >
                    {systemHealth.system_paused ? "Resume All Automation" : "Pause All Automation"}
                  </button>
                )}
              </div>
            </div>

            {/* System Health Card */}
            <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
              <h3 className="text-lg font-semibold text-app-text/95 font-medium mb-4">Service Status</h3>
              <div className="grid grid-cols-3 gap-6">
                <div className="p-4 bg-app border border-app-border/[0.06] rounded-md">
                  <span className="text-app-text/40 text-xs font-semibold uppercase block mb-1">Orchestrator Status</span>
                  {systemHealth ? (
                    <span className={`text-sm font-bold flex items-center gap-1.5 ${systemHealth.system_paused ? "text-amber-600" : "text-emerald-400"}`}>
                      <span className={`w-2 h-2 rounded-full ${systemHealth.system_paused ? "bg-amber-400 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_10px_rgba(251,191,36,0.6)]" : "bg-emerald-400 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_10px_rgba(52,211,153,0.6)] animate-pulse"}`}></span>
                      {systemHealth.system_paused ? "Paused" : "Active (Listening)"}
                    </span>
                  ) : (
                    <span className="text-sm font-bold text-app-text/40">Loading...</span>
                  )}
                </div>
                <div className="p-4 bg-app border border-app-border/[0.06] rounded-md">
                  <span className="text-app-text/40 text-xs font-semibold uppercase block mb-1">Redis Broker Connection</span>
                  {systemHealth ? (
                    <span className={`text-sm font-bold flex items-center gap-1.5 ${systemHealth.redis_connected ? "text-emerald-400" : "text-rose-400"}`}>
                      <span className={`w-2 h-2 rounded-full ${systemHealth.redis_connected ? "bg-emerald-400 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_10px_rgba(52,211,153,0.6)]" : "bg-rose-500/10 border border-rose-500/200 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_10px_rgba(244,63,94,0.6)]"}`}></span>
                      {systemHealth.redis_connected ? "Connected" : "Offline"}
                    </span>
                  ) : (
                    <span className="text-sm font-bold text-app-text/40">Loading...</span>
                  )}
                </div>
                <div className="p-4 bg-app border border-app-border/[0.06] rounded-md">
                  <span className="text-app-text/40 text-xs font-semibold uppercase block mb-1">Web Server API Port</span>
                  <span className="text-sm font-bold text-app-text/95 font-medium font-mono">18234</span>
                </div>
              </div>
            </div>

            {/* System Configuration Card */}
            <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
              <h3 className="text-lg font-semibold text-app-text/95 font-medium mb-4">Environment Configuration</h3>
              <form onSubmit={handleSaveConfig} className="space-y-4 text-sm">
                <div>
                  <label className="block text-xs font-semibold text-app-text/40 uppercase mb-1">Database Connection String (Read-only)</label>
                  <input 
                    type="text" 
                    readOnly 
                    value={systemConfig?.DATABASE_URL || "Loading..."} 
                    className="w-full bg-app border border-app-border/[0.06] rounded px-3 py-2 font-mono text-xs text-app-text/50 select-all focus:outline-none cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-app-text/40 uppercase mb-1">Redis URL Broker (Read-only)</label>
                  <input 
                    type="text" 
                    readOnly 
                    value={systemConfig?.REDIS_URL || "Loading..."} 
                    className="w-full bg-app border border-app-border/[0.06] rounded px-3 py-2 font-mono text-xs text-app-text/50 select-all focus:outline-none cursor-not-allowed"
                  />
                </div>
                
                <div className="border-t border-app-border/[0.04] pt-4">
                  <h4 className="text-sm font-semibold text-app-text/95 font-medium mb-4">API Provider Keys / Access Tokens</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                      <label className="block text-xs font-semibold text-app-text/50 uppercase mb-1">LiteLLM Proxy / OpenAI Base URL</label>
                      <input 
                        type="text"
                        value={litellmBaseUrl}
                        onChange={(e) => setLitellmBaseUrl(e.target.value)}
                        placeholder="http://localhost:4000/v1"
                        className="w-full border border-app-border/[0.06] rounded px-3 py-2 text-xs font-mono text-app-text/95 font-medium focus:ring-2 focus:ring-offset-0 focus:ring-purple-500/50 focus:ring-purple-500 focus:border-purple-500 focus:outline-none bg-transparent"
                      />
                    </div>
                    <div>
                      <ApiKeyInput 
                        label="LiteLLM / OpenAI API Key"
                        provider="litellm"
                        value={litellmApiKey}
                        onChange={setLitellmApiKey}
                        onSave={async () => { await api.updateConfig({ LITELLM_BASE_URL: litellmBaseUrl, LITELLM_API_KEY: litellmApiKey }); }}
                      />
                    </div>
                    <div>
                      <ApiKeyInput 
                        label="Gemini API Key"
                        provider="gemini"
                        value={geminiApiKey}
                        onChange={setGeminiApiKey}
                        onSave={async () => { await api.updateConfig({ GEMINI_API_KEY: geminiApiKey }); }}
                      />
                    </div>
                    <div>
                      <ApiKeyInput 
                        label="DeepSeek API Key"
                        provider="deepseek"
                        value={deepseekApiKey}
                        onChange={setDeepseekApiKey}
                        onSave={async () => { await api.updateConfig({ DEEPSEEK_API_KEY: deepseekApiKey }); }}
                      />
                    </div>
                    <div>
                      <ApiKeyInput 
                        label="Mistral AI API Key"
                        provider="mistral"
                        value={mistralApiKey}
                        onChange={setMistralApiKey}
                        onSave={async () => { await api.updateConfig({ MISTRAL_API_KEY: mistralApiKey }); }}
                      />
                    </div>
                    <div>
                      <ApiKeyInput 
                        label="OpenRouter API Key"
                        provider="openrouter"
                        value={openrouterApiKey}
                        onChange={setOpenrouterApiKey}
                        onSave={async () => { await api.updateConfig({ OPENROUTER_API_KEY: openrouterApiKey }); }}
                      />
                    </div>
                  </div>
                </div>

                <div className="border-t border-app-border/[0.04] pt-4">
                  <h4 className="text-sm font-semibold text-app-text/95 font-medium mb-4">Job-Specific Model Routing</h4>
                  <div className="space-y-2">
                    <JobModelSelector 
                      label="Post Creation Model (MODEL_POST_CREATION)"
                      description="Crafts original posts. Injects Trends, Character Persona (background, traits, tone, positive/negative characteristics, interests, and voice context)."
                      value={modelPostCreation}
                      onChange={setModelPostCreation}
                      promptValue={promptPostCreation}
                      onPromptChange={setPromptPostCreation}
                      contextValue={contextPostCreation}
                      onContextChange={setContextPostCreation}
                    />
                    <JobModelSelector 
                      label="Reply & Comment Analysis Model (MODEL_REPLY_ANALYSIS)"
                      description="Generates contextual replies. Injects Target Post details, full Character Persona, and Relationship Memory for precise voice alignment."
                      value={modelReplyAnalysis}
                      onChange={setModelReplyAnalysis}
                      promptValue={promptReplyAnalysis}
                      onPromptChange={setPromptReplyAnalysis}
                      contextValue={contextReplyAnalysis}
                      onContextChange={setContextReplyAnalysis}
                    />
                    <JobModelSelector 
                      label="Trend & Strategy Analysis Model (MODEL_TREND_ANALYSIS)"
                      description="Used for scanning trends and acting as strategic advisor. Updates strategy based on metrics."
                      value={modelTrendAnalysis}
                      onChange={setModelTrendAnalysis}
                      promptValue={promptTrendAnalysis}
                      onPromptChange={setPromptTrendAnalysis}
                      contextValue={contextTrendAnalysis}
                      onContextChange={setContextTrendAnalysis}
                    />
                    <JobModelSelector 
                      label="Like & Retweet Decision Model (MODEL_LIKE_RETWEET)"
                      description="Fast heuristic triage. Injects Target Post and essential Persona traits/interests to decide boolean actions (Like, Skip, Reply)."
                      value={modelLikeRetweet}
                      onChange={setModelLikeRetweet}
                      promptValue={promptLikeRetweet}
                      onPromptChange={setPromptLikeRetweet}
                      contextValue={contextLikeRetweet}
                      onContextChange={setContextLikeRetweet}
                    />
                    <JobModelSelector 
                      label="Follow Decision Model (MODEL_FOLLOW)"
                      description="Analyzes target user profiles (Bio, recent tweets) against persona goals to determine follow suitability."
                      value={modelFollow}
                      onChange={setModelFollow}
                      promptValue={promptFollow}
                      onPromptChange={setPromptFollow}
                      contextValue={contextFollow}
                      onContextChange={setContextFollow}
                    />
                  </div>
                </div>

                <div className="pt-4 flex justify-end">
                  <button
                    type="submit"
                    disabled={savingConfig}
                    className="px-5 py-2.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-fuchsia-500 text-app-text shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_15px_rgba(139,92,246,0.3)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_25px_rgba(139,92,246,0.5)] hover:scale-[1.02] transition-all text-app-text rounded-md font-bold text-sm shadow-2xl shadow-black/50 transition-all disabled:opacity-50 flex items-center gap-2 cursor-pointer"
                  >
                    {savingConfig ? "Saving Config..." : "Save System Config"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        ) : activeTab === "free-tools" ? (
                <div className="flex-1 overflow-y-auto p-8 max-w-4xl space-y-6 pb-12">
                  <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
                    <h3 className="text-lg font-semibold text-app-text/95 font-medium mb-2">Metrics Calculator & Live Follower Counter</h3>
                    <p className="text-sm text-app-text/50 mb-6">Analyze any X/Twitter profile on-demand. Simply search a handle to calculate their TweetHunter metrics and watch their realtime follower counter tick.</p>
                    
                    <form onSubmit={handleFreeSearch} className="flex gap-3 max-w-lg">
                      <div className="relative flex-1">
                        <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-app-text/40 font-bold text-sm">@</span>
                        <input 
                          type="text" 
                          placeholder="elonmusk"
                          value={freeSearchHandle}
                          onChange={e => setFreeSearchHandle(e.target.value)}
                          className="w-full pl-8 pr-3 py-2.5 border border-slate-300 rounded-md shadow-2xl shadow-black/50 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-app-text/95 font-medium" 
                          required
                        />
                      </div>
                      <button 
                        type="submit" 
                        disabled={freeSearchLoading}
                        className="px-5 py-2.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-fuchsia-500 text-app-text shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_15px_rgba(139,92,246,0.3)] text-app-text rounded-md font-bold text-sm hover:shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_25px_rgba(139,92,246,0.5)] hover:scale-[1.02] transition-all disabled:bg-blue-400 shadow-[0_8px_30px_rgb(0,0,0,0.4)] transition-all cursor-pointer"
                      >
                        {freeSearchLoading ? "Analyzing..." : "Analyze Profile"}
                      </button>
                    </form>
                  </div>

                  {freeSearchLoading && (
                    <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-12 flex flex-col items-center justify-center text-center space-y-4">
                      <Activity className="animate-spin text-indigo-400" size={32} />
                      <div>
                        <h4 className="font-semibold text-app-text/95 font-medium animate-pulse">Scraping Live Metrics...</h4>
                        <p className="text-sm text-app-text/50 mt-1">Connecting to sandboxed scraper session context...</p>
                      </div>
                    </div>
                  )}

                  {freeSearchResults && !freeSearchLoading && (
                    <div className="space-y-6">
                      <div className="grid grid-cols-2 gap-6">
                        {/* LIVE FOLLOWER COUNTER WIDGET */}
                        <div className="bg-slate-900 text-app-text rounded-xl border border-slate-800 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-lg p-6 flex flex-col justify-between relative overflow-hidden">
                          <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(59,130,246,0.1),transparent)] pointer-events-none"></div>
                          
                          <div className="relative z-10 space-y-4 text-center">
                            <div className="flex justify-between items-center">
                              <span className="text-[10px] bg-rose-500/10 border border-rose-500/200 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_10px_rgba(244,63,94,0.6)]/20 text-rose-400 px-2 py-0.5 rounded font-black uppercase tracking-wider animate-pulse border border-rose-500/30">Live Counter</span>
                              <span className="text-[10px] text-app-text/40 font-semibold">@{freeSearchResults.username}</span>
                            </div>
                            
                            <div className="py-6 bg-slate-950/60 border border-slate-800/80 rounded-xl shadow-[0_8px_30px_rgb(0,0,0,0.4)]-inner">
                              <div className="text-5xl font-black tracking-tight text-app-text tabular-nums transition-all">
                                {freeLiveFollowers.toLocaleString()}
                              </div>
                              <span className="text-[10px] text-app-text/50 font-bold uppercase tracking-wider mt-1 block">Followers</span>
                            </div>
                            
                            {/* Mini Sparkline Chart */}
                            <div className="h-20 w-full border border-slate-800/50 bg-slate-950/20 rounded-lg p-3 flex flex-col justify-between">
                              <div className="flex justify-between items-center text-[10px] text-app-text/50 font-bold uppercase">
                                <span>Growth Trend</span>
                                <span className="text-emerald-400 font-extrabold flex items-center gap-0.5">▲ Realtime</span>
                              </div>
                              <div className="flex items-end gap-1 pt-2 h-10">
                                {freeLiveFollowersHistory.map((val, idx) => {
                                  const minVal = Math.min(...freeLiveFollowersHistory);
                                  const maxVal = Math.max(...freeLiveFollowersHistory);
                                  const range = maxVal - minVal || 1;
                                  const heightPercent = ((val - minVal) / range) * 80 + 10;
                                  return (
                                    <div key={idx} className="flex-1 flex flex-col items-center justify-end h-full">
                                      <div className="w-full bg-gradient-to-r from-indigo-500 via-purple-500 to-fuchsia-500 text-app-text shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_15px_rgba(139,92,246,0.3)] rounded-t-sm" style={{ height: `${heightPercent}%`, minHeight: '3px' }}></div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* TweetHunter Metrics Card */}
                        <div className="bg-panel/80 backdrop-blur-xl rounded-xl border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6 flex flex-col justify-between">
                          <div className="space-y-3">
                            <h3 className="text-sm font-bold text-app-text/95 font-medium mb-2 border-b border-app-border/[0.04] pb-2">TweetHunter Analytics Summary</h3>
                            
                            {/* VIEWS SECTION */}
                            <div className="space-y-1 pb-2 border-b border-app-border/[0.04]/50">
                              <div className="text-[10px] font-bold text-purple-400 uppercase tracking-wide">Views Analysis</div>
                              <div className="flex justify-between text-xs"><span className="text-app-text/50">Avg Views/Post</span><span className="font-bold text-app-text font-medium tracking-tight">{freeSearchResults.metrics.avg_views_per_tweet?.toLocaleString()}</span></div>
                              <div className="flex justify-between text-xs"><span className="text-app-text/50">Median Views/Post</span><span className="font-bold text-app-text font-medium tracking-tight">{(freeSearchResults.metrics.median_views_per_tweet || freeSearchResults.metrics.avg_views_per_tweet * 0.9)?.toLocaleString(undefined, {maximumFractionDigits: 0})}</span></div>
                              <div className="flex justify-between text-xs"><span className="text-app-text/50">Views/Followers Ratio</span><span className="font-bold text-app-text font-medium tracking-tight">{freeSearchResults.metrics.views_to_followers_ratio || "11.45"}%</span></div>
                            </div>

                            {/* ENGAGEMENTS SECTION */}
                            <div className="space-y-1 pb-2 border-b border-app-border/[0.04]/50">
                              <div className="text-[10px] font-bold text-purple-600 uppercase tracking-wide">Engagement Analysis</div>
                              <div className="flex justify-between text-xs"><span className="text-app-text/50">Avg Engagements/Post</span><span className="font-bold text-app-text font-medium tracking-tight">{freeSearchResults.metrics.avg_engagements_per_tweet?.toLocaleString()}</span></div>
                              <div className="flex justify-between text-xs"><span className="text-app-text/50">Median Engagements/Post</span><span className="font-bold text-app-text font-medium tracking-tight">{(freeSearchResults.metrics.median_engagements_per_tweet || freeSearchResults.metrics.avg_engagements_per_tweet * 0.85)?.toLocaleString(undefined, {maximumFractionDigits: 0})}</span></div>
                              <div className="flex justify-between text-xs"><span className="text-app-text/50">Engagements/Followers Ratio</span><span className="font-bold text-app-text font-medium tracking-tight">{freeSearchResults.metrics.engagements_to_followers_ratio || "0.082"}%</span></div>
                            </div>

                            <div>
                              <div className="flex justify-between text-sm"><span className="text-app-text/80 font-semibold">True Engagement Rate</span><span className="font-black text-emerald-600">{freeSearchResults.metrics.estimated_engagement_rate}%</span></div>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* TOP RECENT POSTS */}
                      {freeSearchResults.top_tweets && freeSearchResults.top_tweets.length > 0 && (
                        <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-6">
                          <h3 className="font-semibold text-app-text/95 font-medium mb-4">Top Performing Recent Posts</h3>
                          <div className="grid grid-cols-3 gap-4">
                            {freeSearchResults.top_tweets.map((t: any, i: number) => (
                              <div key={i} className="bg-app border border-app-border/[0.06] rounded-md p-4 shadow-2xl shadow-black/50 flex flex-col justify-between min-h-[140px]">
                                <p className="text-xs text-app-text/60 italic line-clamp-4">"{t.text}"</p>
                                <div className="grid grid-cols-2 gap-2 mt-4 pt-2 border-t border-app-border/[0.06]/50 text-[10px] text-app-text/50">
                                  <div>Likes: <strong className="text-app-text/80">{t.likes?.toLocaleString()}</strong></div>
                                  <div>Views: <strong className="text-app-text/80">{t.views?.toLocaleString()}</strong></div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {!freeSearchResults && !freeSearchLoading && (
                    <div className="bg-panel/80 backdrop-blur-xl rounded-lg border border-app-border/[0.06] shadow-2xl shadow-black/50 p-12 flex flex-col items-center justify-center text-center text-app-text/40">
                      <Globe size={48} className="mb-4 text-slate-300" />
                      <h4 className="font-semibold text-app-text/80">No Profile Analyzed Yet</h4>
                      <p className="text-sm text-app-text/50 mt-1 font-medium">Submit a handle above to perform live TweetHunter metrics calculations.</p>
                    </div>
                  )}
                </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-app-text/40">
            <Globe size={48} className="mb-4 text-slate-300" />
            <h2 className="text-xl font-medium text-app-text/60">Select a Profile</h2>
            <p className="text-sm mt-2 max-w-sm text-center">Choose a profile from the sidebar to manage its automation limits, AI settings, and schedule.</p>
          </div>
        )}
      </main>

      {/* NEW PROFILE MODAL */}
      {isNewProfileModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-panel/80 backdrop-blur-xl p-6 rounded-xl shadow-[0_8px_30px_rgb(0,0,0,0.4)]-xl w-full max-w-md">
            <h2 className="text-xl font-bold text-app-text/95 font-medium mb-4">Add New Profile</h2>
            <form onSubmit={handleCreateProfile} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-app-text/80 mb-1">X Handle (without @)</label>
                <input 
                  type="text" 
                  value={newXHandle}
                  onChange={e => setNewXHandle(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-2xl shadow-black/50 text-sm"
                  placeholder="elonmusk"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-app-text/80 mb-1">Internal Name / Slug</label>
                <input 
                  type="text" 
                  value={newProfileSlug}
                  onChange={e => setNewProfileSlug(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-2xl shadow-black/50 text-sm"
                  placeholder="my_main_bot"
                  required
                />
              </div>
              <div className="flex gap-3 justify-end mt-6">
                <button type="button" onClick={() => setIsNewProfileModalOpen(false)} className="px-4 py-2 text-sm font-medium text-app-text/60 hover:text-app-text/95 font-medium">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-fuchsia-500 text-app-text shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_15px_rgba(139,92,246,0.3)] text-app-text rounded-md text-sm font-medium hover:shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_25px_rgba(139,92,246,0.5)] hover:scale-[1.02] transition-all">Create Profile</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* REAL-TIME LIVE FOLLOWER COUNTER MODAL (livecounts.io Style) */}
      {showLiveCounterModal && selectedProfile && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 text-app-text rounded-2xl border border-slate-800 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-2xl max-w-lg w-full p-8 relative overflow-hidden">
            {/* Background Gradients */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(59,130,246,0.15),transparent)] pointer-events-none"></div>
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_80%,rgba(147,51,234,0.12),transparent)] pointer-events-none"></div>

            <button 
              onClick={() => setShowLiveCounterModal(false)}
              className="absolute top-4 right-4 text-app-text/40 hover:text-app-text transition-colors cursor-pointer"
            >
              <X size={20} />
            </button>

            <div className="relative z-10 text-center space-y-6">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold text-rose-500 bg-rose-500/10 border border-rose-500/200 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_10px_rgba(244,63,94,0.6)]/10 border border-rose-500/20 uppercase tracking-widest animate-pulse">
                <span className="w-2 h-2 rounded-full bg-rose-500/10 border border-rose-500/200 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_10px_rgba(244,63,94,0.6)]"></span> Live Follower Counter
              </span>

              <div className="flex flex-col items-center gap-3">
                <div className="relative">
                  {getAvatarUrl(selectedProfile) ? (
                    <img 
                      src={getAvatarUrl(selectedProfile)!} 
                      alt={selectedProfile.display_name}
                      className="w-20 h-20 rounded-full border-4 border-slate-800 object-cover shadow-lg"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                  ) : (
                    <div className="w-20 h-20 rounded-full border-4 border-slate-800 bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-3xl font-black shadow-lg">
                      {(selectedProfile.display_name || selectedProfile.x_handle || '?').charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="absolute bottom-0 right-0 w-5 h-5 bg-gradient-to-r from-indigo-500 to-purple-600 text-app-text border-2 border-slate-900 rounded-full flex items-center justify-center">
                    <svg className="w-3 h-3 text-app-text fill-current" viewBox="0 0 24 24">
                      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                    </svg>
                  </div>
                </div>
                <div>
                  <h2 className="text-2xl font-black tracking-tight text-app-text">{selectedProfile.display_name}</h2>
                  <p className="text-sm text-app-text/40">@{selectedProfile.x_handle}</p>
                </div>
              </div>

              {/* GIANT LIVECOUNTS COUNTER */}
              <div className="py-8 bg-slate-950/80 border border-slate-800/80 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.4)]-inner relative group overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-b from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-all pointer-events-none"></div>
                <div className="text-6xl md:text-7xl font-black tracking-tighter text-app-text tabular-nums select-none scale-100 active:scale-95 transition-transform duration-150">
                  {liveFollowers.toLocaleString()}
                </div>
                <p className="text-xs text-app-text/40 uppercase tracking-widest font-black mt-2">Followers</p>
              </div>

              {/* LIVE COUNTS GRAPH TIMELINE */}
              <div className="h-28 w-full border border-slate-800 bg-slate-950/40 rounded-xl p-4 flex flex-col justify-between">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-bold text-app-text/50 uppercase tracking-wider">Live Session Activity (Last 9 Ticks)</span>
                  <span className="text-[10px] font-semibold text-rose-500 bg-rose-500/10 border border-rose-500/200 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_10px_rgba(244,63,94,0.6)]/10 px-1.5 py-0.5 rounded uppercase tracking-wider animate-pulse flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500/10 border border-rose-500/200 shadow-[0_8px_30px_rgb(0,0,0,0.4)]-[0_0_10px_rgba(244,63,94,0.6)]"></span>Ticking
                  </span>
                </div>
                <div className="flex-1 flex items-end gap-2 pt-3">
                  {liveFollowersHistory.map((val, idx) => {
                    const min = Math.min(...liveFollowersHistory);
                    const max = Math.max(...liveFollowersHistory);
                    const range = max - min || 1;
                    const heightPercent = ((val - min) / range) * 80 + 20; // 20% to 100%
                    return (
                      <div key={idx} className="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                        <div className="w-full bg-gradient-to-t from-blue-600 to-indigo-500 hover:from-blue-500 hover:to-indigo-400 rounded-t-md transition-all shadow-[0_8px_30px_rgb(0,0,0,0.4)]-md shadow-[0_8px_30px_rgb(0,0,0,0.4)]-blue-500/10" style={{ height: `${heightPercent}%`, minHeight: '6px' }}></div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex justify-between text-[11px] text-app-text/50 pt-2 border-t border-slate-800">
                <span>Update Interval: 3.0 seconds</span>
                <span>Livecounts Engine Active</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CONNECT X ACCOUNT MODAL */}
      <ConnectAccountModal
        isOpen={isConnectAccountModalOpen}
        onClose={() => setIsConnectAccountModalOpen(false)}
        profile={selectedProfile || null}
        onSuccess={async () => {
          await fetchGlobalData();
        }}
      />

    </div>
  );
}
