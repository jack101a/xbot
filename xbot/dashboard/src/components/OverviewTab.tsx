"use client";

import React, { useState, useRef } from "react";
import {
  Play,
  RefreshCw,
  Pause,
  CheckCircle2,
  AlertCircle,
  Clock,
  TrendingUp,
  Users,
  Eye,
  Brain,
  ExternalLink,
  Shield,
  Zap,
  ArrowRight,
  Flame,
  Layers,
  Image as ImageIcon,
  Send,
  Smile,
  X,
  Upload,
  Trophy,
  BarChart3,
  Award
} from "lucide-react";
import { Profile, Session, RateLimit, api } from "@/lib/api";
import { formatISTDateTime, formatISTTime } from "@/lib/time";

interface OverviewTabProps {
  profile: Profile;
  sessions: Session[];
  rateLimits: RateLimit[];
  onRefresh: () => void;
  onNavigateToTab: (tab: "growth" | "activity" | "persona" | "limits") => void;
  onSelectSession?: (sessionId: string) => void;
}

export function OverviewTab({
  profile,
  sessions,
  rateLimits,
  onRefresh,
  onNavigateToTab,
  onSelectSession
}: OverviewTabProps) {
  const [triggering, setTriggering] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [actionMsg, setActionMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [drafts, setDrafts] = useState<any[]>([]);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [deepAnalytics, setDeepAnalytics] = useState<any | null>(null);
  const [syncingAnalytics, setSyncingAnalytics] = useState(false);

  // Quick Composer State
  const [quickPostText, setQuickPostText] = useState("");
  const [selectedImageFile, setSelectedImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [publishingQuickPost, setPublishingQuickPost] = useState(false);
  const [quickPostMsg, setQuickPostMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    loadDrafts();
    loadDeepAnalytics();
  }, [profile.id]);

  const loadDrafts = async () => {
    try {
      const res = await api.getDrafts(profile.id);
      setDrafts(res || []);
    } catch (e) {
      console.error("Could not load drafts:", e);
    }
  };

  const loadDeepAnalytics = async () => {
    try {
      const res = await api.getDeepAnalytics(profile.id);
      setDeepAnalytics(res);
    } catch (e) {
      console.error("Could not load deep analytics:", e);
    }
  };

  const handleSyncLiveAnalytics = async () => {
    setSyncingAnalytics(true);
    setActionMsg(null);
    try {
      const res = await api.syncLiveAnalytics(profile.id);
      setActionMsg({ type: "success", text: res.message || "Live metrics synced successfully!" });
      loadDeepAnalytics();
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to sync live analytics." });
    } finally {
      setSyncingAnalytics(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedImageFile(file);
      setImagePreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleRemoveImage = () => {
    setSelectedImageFile(null);
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl);
      setImagePreviewUrl(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleInsertEmoji = (emoji: string) => {
    setQuickPostText((prev) => prev + (prev.endsWith(" ") || prev === "" ? "" : " ") + emoji);
  };

  const handlePublishQuickPost = async () => {
    if (!quickPostText.trim() && !selectedImageFile) return;
    setPublishingQuickPost(true);
    setQuickPostMsg(null);
    try {
      let uploadedMediaPath: string | undefined = undefined;
      if (selectedImageFile) {
        const uploadRes = await api.uploadMedia(profile.id, selectedImageFile);
        uploadedMediaPath = uploadRes.file_path;
      }

      await api.publishLivePost(
        profile.id,
        quickPostText.trim(),
        uploadedMediaPath ? [uploadedMediaPath] : undefined
      );

      setQuickPostMsg({ type: "success", text: "Published live post to X timeline!" });
      setQuickPostText("");
      handleRemoveImage();
      onRefresh();
    } catch (err: any) {
      setQuickPostMsg({ type: "error", text: err.message || "Failed to publish live post." });
    } finally {
      setPublishingQuickPost(false);
    }
  };

  const handleApproveDraft = async (draftId: string) => {
    setApprovingId(draftId);
    try {
      await api.approveDraft(profile.id, draftId);
      setActionMsg({ type: "success", text: "Draft approved and published live to X!" });
      loadDrafts();
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to publish draft." });
    } finally {
      setApprovingId(null);
    }
  };

  const handleDismissDraft = async (draftId: string) => {
    try {
      await api.dismissDraft(profile.id, draftId);
      setActionMsg({ type: "success", text: "Draft dismissed." });
      loadDrafts();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to dismiss draft." });
    }
  };

  const handleApproveAllDrafts = async () => {
    try {
      const res = await api.approveAllDrafts(profile.id);
      setActionMsg({ type: "success", text: res.message || "All drafts approved for autonomous publishing!" });
      loadDrafts();
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to approve drafts." });
    }
  };

  const handleDismissAllDrafts = async () => {
    if (!confirm(`Are you sure you want to discard all ${drafts.length} pending draft posts?`)) return;
    try {
      const res = await api.dismissAllDrafts(profile.id);
      setActionMsg({ type: "success", text: res.message || "All pending drafts discarded." });
      loadDrafts();
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to discard all drafts." });
    }
  };

  const handleRunSession = async () => {
    setTriggering(true);
    setActionMsg(null);
    try {
      const res = await api.triggerProfileSession(profile.id);
      setActionMsg({ type: "success", text: "Autonomous session queued! Check Live Activity tab to watch in real-time." });
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to trigger session." });
    } finally {
      setTriggering(false);
    }
  };

  const handleSyncFromX = async () => {
    setSyncing(true);
    setActionMsg(null);
    try {
      const res = await api.syncProfileFromX(profile.id);
      setActionMsg({ type: "success", text: "Profile stats and recent tweets synchronized from X!" });
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to sync profile from X." });
    } finally {
      setSyncing(false);
    }
  };

  const handleTogglePause = async () => {
    setActionMsg(null);
    try {
      if (profile.status === "active") {
        await api.pauseProfile(profile.id);
        setActionMsg({ type: "success", text: "Profile automation paused." });
      } else {
        await api.resumeProfile(profile.id);
        setActionMsg({ type: "success", text: "Profile automation resumed." });
      }
      onRefresh();
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message || "Failed to update status." });
    }
  };

  // Find rate limit stats for this profile
  const profileLimits = rateLimits.filter(
    (l) => l.profile_id === profile.id || l.profile_slug === profile.profile_slug
  );

  const postLimit = profileLimits.find((l) => l.action_type === "post")?.count_today || 0;
  const replyLimit = profileLimits.find((l) => l.action_type === "reply")?.count_today || 0;
  const likeLimit = profileLimits.find((l) => l.action_type === "like")?.count_today || 0;

  const maxPosts = profile.config?.limits?.max_posts_per_day || profile.config?.max_posts_per_day || 15;
  const maxReplies = profile.config?.limits?.max_replies_per_day || profile.config?.max_replies_per_day || 35;
  const maxLikes = profile.config?.limits?.max_likes_per_day || profile.config?.max_likes_per_day || 50;

  return (
    <div className="space-y-6">
      {/* Alert Banner */}
      {actionMsg && (
        <div
          className={`p-4 rounded-xl flex items-center justify-between border ${
            actionMsg.type === "success"
              ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
              : "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300"
          }`}
        >
          <div className="flex items-center gap-3">
            {actionMsg.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
            )}
            <span className="text-sm font-medium">{actionMsg.text}</span>
          </div>
          <button
            onClick={() => setActionMsg(null)}
            className="text-xs font-semibold underline hover:opacity-75"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Hero Profile Card */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-gradient-to-br from-white via-indigo-50/30 to-purple-50/20 dark:from-slate-900 dark:via-slate-900/90 dark:to-indigo-950/30 p-4 sm:p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5 sm:gap-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3.5 sm:gap-4">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-tr from-indigo-500 to-violet-600 overflow-hidden flex-shrink-0 flex items-center justify-center text-white text-xl sm:text-2xl font-bold border-2 border-white dark:border-slate-800 shadow-md">
              {profile.avatar_url || profile.avatar ? (
                <img src={profile.avatar_url || profile.avatar} alt="" className="w-full h-full object-cover" />
              ) : (
                profile.display_name.charAt(0).toUpperCase()
              )}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-lg sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight truncate">
                  {profile.display_name}
                </h1>
                <a
                  href={`https://x.com/${profile.x_handle.replace(/^@/, "")}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs sm:text-sm font-semibold text-sky-600 dark:text-sky-400 hover:underline"
                >
                  <span>@{profile.x_handle.replace(/^@/, "")}</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
                <span
                  className={`text-[11px] sm:text-xs font-semibold px-2 sm:px-2.5 py-0.5 rounded-full capitalize ${
                    profile.status === "active"
                      ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                      : "bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
                  }`}
                >
                  {profile.status}
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 mt-1 line-clamp-2 max-w-xl">
                {profile.persona_summary?.identity?.background ||
                  profile.persona_summary?.bio ||
                  "Autonomous AI creator voice configured for organic audience growth."}
              </p>
            </div>
          </div>

          {/* Quick Trigger CTAs */}
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:flex items-center gap-2.5 w-full lg:w-auto">
            <button
              onClick={handleSyncFromX}
              disabled={syncing}
              className="flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-750 transition shadow-sm disabled:opacity-50 w-full lg:w-auto"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`} />
              <span>{syncing ? "Syncing..." : "Sync from X"}</span>
            </button>

            <button
              onClick={handleTogglePause}
              className={`flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold border transition shadow-sm w-full lg:w-auto ${
                profile.status === "active"
                  ? "border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 hover:bg-amber-100/60"
                  : "border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100/60"
              }`}
            >
              {profile.status === "active" ? (
                <>
                  <Pause className="w-3.5 h-3.5" />
                  <span>Pause Bot</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5" />
                  <span>Resume Bot</span>
                </>
              )}
            </button>

            <button
              onClick={handleRunSession}
              disabled={triggering}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white shadow-lg shadow-indigo-500/25 transition disabled:opacity-50 w-full lg:w-auto"
            >
              <Zap className={`w-4 h-4 ${triggering ? "animate-bounce" : ""}`} />
              <span>{triggering ? "Queuing..." : "Run Session Now"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          QUICK LIVE COMPOSER (Text, Photos & Natural Emojis)
      ───────────────────────────────────────────────────────────── */}
      <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Send className="w-4 h-4 text-indigo-500" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Quick Live Post Composer
            </h3>
          </div>
          <span className="text-[11px] text-slate-500 font-mono">
            {quickPostText.length}/280 chars
          </span>
        </div>

        {quickPostMsg && (
          <div
            className={`p-3 rounded-xl text-xs font-semibold border ${
              quickPostMsg.type === "success"
                ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300"
                : "bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300"
            }`}
          >
            {quickPostMsg.text}
          </div>
        )}

        <textarea
          rows={3}
          value={quickPostText}
          onChange={(e) => setQuickPostText(e.target.value)}
          placeholder={`What's happening? Share a thought, Delhi lifestyle take, or attach an image as @${profile.x_handle.replace(/^@+/, '')}...`}
          className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white resize-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition"
        />

        {/* Attached Image Thumbnail Preview */}
        {imagePreviewUrl && (
          <div className="relative inline-block mt-1 group">
            <img
              src={imagePreviewUrl}
              alt="Attached Media"
              className="h-24 w-auto rounded-xl object-cover border border-slate-200 dark:border-slate-700 shadow-sm"
            />
            <button
              onClick={handleRemoveImage}
              className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-slate-900/90 text-white flex items-center justify-center hover:bg-rose-600 transition shadow"
              title="Remove image"
            >
              <X className="w-3 h-3" />
            </button>
            <span className="block text-[10px] text-slate-500 mt-1 truncate max-w-[150px]">
              {selectedImageFile?.name}
            </span>
          </div>
        )}

        {/* Emoji Bar & Attachment Controls */}
        <div className="flex items-center justify-between flex-wrap gap-2 pt-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1 mr-1">
              <Smile className="w-3 h-3" /> Emojis:
            </span>
            {["✨", "💅", "☕", "💀", "😂", "👀", "🤌", "💯", "🔥", "🧵"].map((emoji) => (
              <button
                key={emoji}
                type="button"
                onClick={() => handleInsertEmoji(emoji)}
                className="w-7 h-7 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/80 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 hover:border-indigo-300 dark:hover:border-indigo-700 text-xs flex items-center justify-center transition"
              >
                {emoji}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="image/*"
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/60 text-slate-700 dark:text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition shadow-sm"
            >
              <ImageIcon className="w-3.5 h-3.5 text-indigo-500" />
              <span>{selectedImageFile ? "Change Photo" : "Attach Photo"}</span>
            </button>

            <button
              type="button"
              onClick={handlePublishQuickPost}
              disabled={publishingQuickPost || (!quickPostText.trim() && !selectedImageFile)}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center gap-1.5 transition shadow-md shadow-indigo-500/20 disabled:opacity-50"
            >
              {publishingQuickPost ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
              <span>{publishingQuickPost ? "Posting..." : "Publish Live to X"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Pending Post & Poll Approvals (Human-in-the-Loop) */}
      {drafts.length > 0 && (
        <div className="p-4 sm:p-5 rounded-2xl border-2 border-amber-300/80 dark:border-amber-700/80 bg-amber-50/50 dark:bg-amber-950/20 backdrop-blur-md shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
              </span>
              <h2 className="text-sm font-bold text-amber-900 dark:text-amber-200">
                Pending Posts Staged for Your Approval ({drafts.length})
              </h2>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={handleApproveAllDrafts}
                className="px-3 py-1 rounded-lg text-xs font-bold text-emerald-800 dark:text-emerald-200 bg-emerald-100 dark:bg-emerald-950/80 hover:bg-emerald-200 dark:hover:bg-emerald-900 border border-emerald-300 dark:border-emerald-700 transition flex items-center gap-1 shadow-sm"
              >
                <span>⚡ Publish All Now ({drafts.length})</span>
              </button>
              <button
                onClick={handleDismissAllDrafts}
                className="px-3 py-1 rounded-lg text-xs font-bold text-rose-700 dark:text-rose-300 bg-rose-100 dark:bg-rose-950/60 hover:bg-rose-200 dark:hover:bg-rose-900/80 border border-rose-300 dark:border-rose-800 transition"
              >
                Discard All
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            {drafts.map((d) => (
              <div
                key={d.id}
                className="p-4 rounded-xl border border-amber-200 dark:border-amber-800/60 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-2">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className={`px-2 py-0.5 rounded-md uppercase tracking-wider text-[10px] font-bold ${
                        d.content_type === "thread"
                          ? "bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300"
                          : d.content_type === "poll"
                          ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                      }`}>
                        {d.content_type === "thread" ? `🧵 THREAD (${d.thread_items?.length || d.ai_metadata?.tweets?.length || "multi"})` : d.content_type}
                      </span>
                      {d.ai_metadata?.visual_spec && (
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                          🖼️ 4:5 MEME ({d.ai_metadata.visual_spec.format_type || "visual"})
                        </span>
                      )}
                      {d.ai_metadata?.gif_query && (
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-pink-100 dark:bg-pink-950 text-pink-700 dark:text-pink-300 border border-pink-200 dark:border-pink-800">
                          🎬 GIF: "{d.ai_metadata.gif_query}"
                        </span>
                      )}
                    </div>
                    <span>{d.created_at ? formatISTTime(d.created_at) : "Just now"}</span>
                  </div>

                  {d.content_type === "thread" && (d.thread_items?.length > 0 || d.ai_metadata?.tweets?.length > 0) ? (
                    <div className="space-y-2.5 my-2">
                      {(d.thread_items && d.thread_items.length > 0 ? d.thread_items : (d.ai_metadata?.tweets || []).map((t: string, i: number) => ({ id: `idx-${i}`, position: i, item_type: i === 0 ? "hook" : i === d.ai_metadata.tweets.length - 1 ? "closer" : "body", text: t }))).map((item: any, idx: number, arr: any[]) => (
                        <div key={item.id || idx} className="relative pl-6">
                          {idx < arr.length - 1 && (
                            <div className="absolute left-[9px] top-4 bottom-[-10px] w-0.5 bg-purple-200 dark:bg-purple-800/60" />
                          )}
                          <div className="absolute left-0 top-0.5 w-[19px] h-[19px] rounded-full bg-purple-100 dark:bg-purple-900 border-2 border-purple-400 dark:border-purple-600 flex items-center justify-center text-[9px] font-bold text-purple-700 dark:text-purple-300">
                            {idx + 1}
                          </div>
                          <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/70 border border-slate-200/80 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-200">
                            <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1 font-mono">
                              <span className="capitalize">{item.item_type || "part"}</span>
                              <span>{item.text?.length || 0}/280</span>
                            </div>
                            <p className="whitespace-pre-wrap font-medium">{item.text}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs sm:text-sm text-slate-800 dark:text-slate-100 whitespace-pre-wrap font-medium">
                      {d.body}
                    </p>
                  )}

                  {d.ai_metadata?.visual_spec && (
                    <div className="p-2.5 rounded-lg bg-indigo-50/70 dark:bg-indigo-950/40 border border-indigo-200/80 dark:border-indigo-800/70 my-2 space-y-1">
                      <div className="flex items-center justify-between text-[10px] font-bold text-indigo-700 dark:text-indigo-300">
                        <span>📸 Visual Scene Punchline ({d.ai_metadata.visual_spec.aspect_ratio || "4:5"} Mobile Takeover)</span>
                        <span className="capitalize">{d.ai_metadata.visual_spec.format_type?.replace(/_/g, " ")}</span>
                      </div>
                      <p className="text-[11px] text-slate-700 dark:text-slate-300 font-medium">
                        {d.ai_metadata.visual_spec.visual_description}
                      </p>
                    </div>
                  )}

                  {d.ai_metadata?.media_paths && d.ai_metadata.media_paths.length > 0 && (
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-[11px] font-semibold text-indigo-700 dark:text-indigo-300 my-2">
                      <ImageIcon className="w-3.5 h-3.5" />
                      <span>Attached Photo ({d.ai_metadata.media_paths[0].split('/').pop()})</span>
                    </div>
                  )}

                  {d.ai_metadata?.reasoning && (
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 italic mt-2">
                      💡 {d.ai_metadata.reasoning}
                    </p>
                  )}
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <button
                    onClick={() => handleDismissDraft(d.id)}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                  >
                    Dismiss
                  </button>
                  <button
                    onClick={() => handleApproveDraft(d.id)}
                    disabled={approvingId === d.id}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{approvingId === d.id ? "Publishing..." : d.content_type === "thread" ? "Approve & Post Thread" : "Approve & Post"}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Official Creator Studio Monetization Milestones & 28-Day Deep Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Official Creator Studio Milestones (500 Verified Followers & 500K Home Impressions) */}
        <div className="lg:col-span-7 p-5 rounded-2xl border-2 border-indigo-200/80 dark:border-indigo-800/60 bg-gradient-to-br from-indigo-50/70 via-white/80 to-purple-50/50 dark:from-indigo-950/30 dark:via-slate-900/60 dark:to-purple-950/20 backdrop-blur-md shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-sm">
                <Trophy className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                  Official Creator Studio Monetization
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300">
                    Live X Sync
                  </span>
                </h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Target milestones to qualify for Original Content Rewards on X
                </p>
              </div>
            </div>
            <button
              onClick={handleSyncLiveAnalytics}
              disabled={syncingAnalytics}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 shadow-sm transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncingAnalytics ? "animate-spin text-indigo-600" : ""}`} />
              <span>{syncingAnalytics ? "Syncing..." : "Sync Live Stats"}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-1">
            {/* Milestone 1: 500 Verified Followers */}
            <div className="p-4 rounded-xl border border-indigo-100 dark:border-indigo-900/60 bg-white/90 dark:bg-slate-900/90 shadow-sm space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <Award className="w-3.5 h-3.5 text-blue-500" />
                  Verified Followers
                </span>
                <span className="font-bold text-indigo-600 dark:text-indigo-400">
                  {deepAnalytics?.monetization_milestones?.verified_followers?.current || 16} / 500
                </span>
              </div>
              <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-blue-500 to-indigo-600 h-2.5 rounded-full transition-all duration-700"
                  style={{ width: `${Math.max(3, deepAnalytics?.monetization_milestones?.verified_followers?.percentage || 3.2)}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400">
                <span>{deepAnalytics?.monetization_milestones?.verified_followers?.percentage || 3.2}% Complete</span>
                <span>{deepAnalytics?.monetization_milestones?.verified_followers?.remaining || 484} remaining</span>
              </div>
            </div>

            {/* Milestone 2: 500K Verified Home Timeline Impressions */}
            <div className="p-4 rounded-xl border border-purple-100 dark:border-purple-900/60 bg-white/90 dark:bg-slate-900/90 shadow-sm space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <Flame className="w-3.5 h-3.5 text-purple-500" />
                  90d Verified Impressions
                </span>
                <span className="font-bold text-purple-600 dark:text-purple-400">
                  {(deepAnalytics?.monetization_milestones?.verified_impressions_90d?.current || 0).toLocaleString()} / 500K
                </span>
              </div>
              <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-purple-500 to-pink-500 h-2.5 rounded-full transition-all duration-700"
                  style={{ width: `${Math.max(1, deepAnalytics?.monetization_milestones?.verified_impressions_90d?.percentage || 0)}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400">
                <span>{deepAnalytics?.monetization_milestones?.verified_impressions_90d?.percentage || 0.0}% Complete</span>
                <span>Home Timeline (Excludes replies)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Rolling 28-Day Deep Metrics Overview */}
        <div className="lg:col-span-5 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md shadow-sm flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-sm">
                <BarChart3 className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Rolling 28-Day Deep Analytics
                </h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Total organic impressions & engagement velocity
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2.5 pt-1 text-center">
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/60">
              <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 block">28d Impressions</span>
              <span className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white mt-0.5 block">
                {(deepAnalytics?.rolling_28d?.total_impressions || 0).toLocaleString()}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/60">
              <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 block">28d Engagements</span>
              <span className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white mt-0.5 block">
                {(deepAnalytics?.rolling_28d?.total_engagements || 0).toLocaleString()}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/60">
              <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 block">Velocity Rate</span>
              <span className="text-base sm:text-lg font-extrabold text-emerald-600 dark:text-emerald-400 mt-0.5 block">
                {deepAnalytics?.rolling_28d?.engagement_rate || 0.0}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 6 Real-Time Metric Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        {/* Total Posts / Tweets */}
        <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Total Posts</span>
            <div className="w-7 h-7 rounded-xl bg-indigo-100 dark:bg-indigo-950 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <Layers className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {(deepAnalytics?.rolling_28d?.total_posts ?? profile.posts_count ?? 0).toLocaleString()}
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1">Live on @{profile.x_handle.replace(/^@+/, '')}</p>
        </div>

        {/* Total Followers */}
        <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Followers</span>
            <div className="w-7 h-7 rounded-xl bg-sky-100 dark:bg-sky-950 flex items-center justify-center text-sky-600 dark:text-sky-400">
              <Users className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {(profile.followers_count ?? 0).toLocaleString()}
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1">Organic audience</p>
        </div>

        {/* Total Following */}
        <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Following</span>
            <div className="w-7 h-7 rounded-xl bg-violet-100 dark:bg-violet-950 flex items-center justify-center text-violet-600 dark:text-violet-400">
              <Eye className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {(profile.following_count ?? 0).toLocaleString()}
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1">Curated accounts</p>
        </div>

        {/* 24h / 28d Impressions */}
        <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Impressions</span>
            <div className="w-7 h-7 rounded-xl bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <TrendingUp className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {(deepAnalytics?.rolling_28d?.total_impressions ?? profile.impressions_24h ?? 0).toLocaleString()}
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1">Total post views</p>
        </div>

        {/* Total Engagements */}
        <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Engagements</span>
            <div className="w-7 h-7 rounded-xl bg-rose-100 dark:bg-rose-950 flex items-center justify-center text-rose-600 dark:text-rose-400">
              <Flame className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {(deepAnalytics?.rolling_28d?.total_engagements ?? profile.engagements_24h ?? 0).toLocaleString()}
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1">Likes & reposts</p>
        </div>

        {/* Sessions Completed */}
        <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Sessions</span>
            <div className="w-7 h-7 rounded-xl bg-amber-100 dark:bg-amber-950 flex items-center justify-center text-amber-600 dark:text-amber-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {sessions.length.toLocaleString()}
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1">Autonomous runs</p>
        </div>
      </div>

      {/* Grid: 24h Action Limits & Recent Sessions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* 24-Hour Limits Progress */}
        <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-4 sm:space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-indigo-500" />
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">24h Rate Limit Safety</h3>
            </div>
            <button
              onClick={() => onNavigateToTab("limits")}
              className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:underline"
            >
              Edit Caps
            </button>
          </div>

          <div className="space-y-4">
            {/* Posts */}
            <div>
              <div className="flex items-center justify-between text-xs font-medium mb-1.5">
                <span className="text-slate-600 dark:text-slate-400">Posts Today</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {postLimit} / {maxPosts}
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-violet-500 to-indigo-600 transition-all duration-300"
                  style={{ width: `${Math.min(100, (postLimit / (maxPosts || 1)) * 100)}%` }}
                />
              </div>
            </div>

            {/* Replies */}
            <div>
              <div className="flex items-center justify-between text-xs font-medium mb-1.5">
                <span className="text-slate-600 dark:text-slate-400">Sniper Replies Today</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {replyLimit} / {maxReplies}
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-sky-500 to-indigo-600 transition-all duration-300"
                  style={{ width: `${Math.min(100, (replyLimit / (maxReplies || 1)) * 100)}%` }}
                />
              </div>
            </div>

            {/* Likes */}
            <div>
              <div className="flex items-center justify-between text-xs font-medium mb-1.5">
                <span className="text-slate-600 dark:text-slate-400">Organic Likes Today</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {likeLimit} / {maxLikes}
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-rose-500 to-pink-600 transition-all duration-300"
                  style={{ width: `${Math.min(100, (likeLimit / (maxLikes || 1)) * 100)}%` }}
                />
              </div>
            </div>
          </div>

          <p className="text-[11px] text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800/80 pt-3">
            Anti-ban safety prevents account flagging by strictly enforcing sliding-window rate limits.
          </p>
        </div>

        {/* Recent Execution Sessions */}
        <div className="lg:col-span-2 p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-500" />
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">Recent Automation Sessions</h3>
            </div>
            <button
              onClick={() => onNavigateToTab("activity")}
              className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:underline flex items-center gap-1"
            >
              <span>Live Terminal</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {sessions.length > 0 ? (
            <div className="divide-y divide-slate-100 dark:divide-slate-800/80">
              {sessions.slice(0, 5).map((s) => (
                <div
                  key={s.id}
                  onClick={() => {
                    if (onSelectSession) onSelectSession(s.id);
                    onNavigateToTab("activity");
                  }}
                  className="py-3 flex items-center justify-between gap-4 hover:bg-slate-50/50 dark:hover:bg-slate-800/30 px-2 rounded-xl transition cursor-pointer group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                        s.status === "completed"
                          ? "bg-emerald-500"
                          : s.status === "running"
                          ? "bg-sky-500 animate-ping"
                          : s.status === "failed"
                          ? "bg-rose-500"
                          : "bg-amber-500"
                      }`}
                    />
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate flex items-center gap-2">
                        <span>Session {s.id.slice(0, 8)}...</span>
                        <span
                          className={`text-[10px] uppercase font-bold px-1.5 py-0.2 rounded capitalize ${
                            s.status === "completed"
                              ? "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400"
                              : s.status === "running"
                              ? "bg-sky-100 dark:bg-sky-950/60 text-sky-700 dark:text-sky-400"
                              : "bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400"
                          }`}
                        >
                          {s.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        {formatISTDateTime(s.started_at)} &bull; {s.actions_completed || 0} /{" "}
                        {s.actions_planned || 0} actions completed
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 transition group-hover:translate-x-0.5 flex-shrink-0" />
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-slate-500 text-xs space-y-2">
              <p>No recent sessions recorded yet.</p>
              <button
                onClick={handleRunSession}
                className="px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition"
              >
                Run First Session Now
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Live Account Posts & Activity Log */}
      {profile.recent_tweets && profile.recent_tweets.length > 0 && (
        <div className="p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-md shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-500" />
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">Live Profile Posts & Engagement</h3>
            </div>
            <span className="text-xs text-slate-400 font-medium">
              Synced from X (@{profile.x_handle.replace(/^@+/, '')})
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {profile.recent_tweets.slice(0, 6).map((tw, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-slate-50/60 dark:bg-slate-800/40 flex flex-col justify-between space-y-3"
              >
                <p className="text-xs text-slate-800 dark:text-slate-200 line-clamp-3 leading-relaxed">
                  "{tw.body}"
                </p>
                <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 border-t border-slate-200/60 dark:border-slate-700/50 pt-2">
                  <span className="flex items-center gap-1">
                    <Eye className="w-3 h-3 text-sky-500" /> {tw.views || 0} views
                  </span>
                  <span className="flex items-center gap-1">
                    <Flame className="w-3 h-3 text-rose-500" /> {tw.likes || 0} likes
                  </span>
                  <span className="flex items-center gap-1">
                    <RefreshCw className="w-3 h-3 text-emerald-500" /> {tw.retweets || 0} reposts
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
