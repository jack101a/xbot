import React, { RefObject } from "react";
import { Send, X, Smile, Image as ImageIcon, RefreshCw } from "lucide-react";
import { Profile } from "@/lib/api";

interface QuickLiveComposerProps {
  profile: Profile;
  quickPostText: string;
  setQuickPostText: (val: string) => void;
  selectedImageFile: File | null;
  imagePreviewUrl: string | null;
  publishingQuickPost: boolean;
  quickPostMsg: { type: "success" | "error"; text: string } | null;
  fileInputRef: RefObject<HTMLInputElement>;
  handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleRemoveImage: () => void;
  handleInsertEmoji: (emoji: string) => void;
  handlePublishQuickPost: () => void;
}

export function QuickLiveComposer({
  profile,
  quickPostText,
  setQuickPostText,
  selectedImageFile,
  imagePreviewUrl,
  publishingQuickPost,
  quickPostMsg,
  fileInputRef,
  handleFileChange,
  handleRemoveImage,
  handleInsertEmoji,
  handlePublishQuickPost
}: QuickLiveComposerProps) {
  return (
    <div className="p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/70 shadow-sm flex flex-col justify-between gap-2.5 h-full">
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <Send className="w-3.5 h-3.5 text-indigo-500" />
            <h3 className="text-xs font-bold text-slate-900 dark:text-white">
              Quick Live Post Composer
            </h3>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">
            {quickPostText.length}/280
          </span>
        </div>

        {quickPostMsg && (
          <div
            className={`p-2 rounded-xl text-[11px] font-semibold border mb-2 ${
              quickPostMsg.type === "success"
                ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300"
                : "bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300"
            }`}
          >
            {quickPostMsg.text}
          </div>
        )}

        <textarea
          rows={2}
          value={quickPostText}
          onChange={(e) => setQuickPostText(e.target.value)}
          placeholder={`What's happening as @${profile.x_handle.replace(/^@+/, '')}?`}
          className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white resize-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition"
        />

        {imagePreviewUrl && (
          <div className="relative inline-block mt-1 group">
            <img
              src={imagePreviewUrl}
              alt="Attached Media"
              className="h-14 w-auto rounded-lg object-cover border border-slate-200 dark:border-slate-700 shadow-sm"
            />
            <button
              onClick={handleRemoveImage}
              className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-slate-900/90 text-white flex items-center justify-center hover:bg-rose-600 transition shadow"
              title="Remove image"
            >
              <X className="w-2.5 h-2.5" />
            </button>
            <span className="block text-[9px] text-slate-500 mt-0.5 truncate max-w-[120px]">
              {selectedImageFile?.name}
            </span>
          </div>
        )}
      </div>

      <div>
        <div className="flex items-center gap-1 overflow-x-auto py-0.5 scrollbar-none">
          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-0.5 mr-0.5 flex-shrink-0">
            <Smile className="w-2.5 h-2.5" />
          </span>
          {["✨", "💅", "☕", "💀", "😂", "👀", "🤌", "💯", "🔥", "🧵"].map((emoji) => (
            <button
              key={emoji}
              type="button"
              onClick={() => handleInsertEmoji(emoji)}
              className="w-6 h-6 flex-shrink-0 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/80 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 hover:border-indigo-300 dark:hover:border-indigo-700 text-[11px] flex items-center justify-center transition"
            >
              {emoji}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 justify-end pt-2 border-t border-slate-100 dark:border-slate-800/80 mt-1.5">
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
            className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/60 text-slate-700 dark:text-slate-200 text-xs font-semibold flex items-center gap-1 transition shadow-sm"
          >
            <ImageIcon className="w-3 h-3 text-indigo-500" />
            <span>{selectedImageFile ? "Change" : "Photo"}</span>
          </button>

          <button
            type="button"
            onClick={handlePublishQuickPost}
            disabled={publishingQuickPost || (!quickPostText.trim() && !selectedImageFile)}
            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center gap-1 transition shadow-sm disabled:opacity-50"
          >
            {publishingQuickPost ? (
              <RefreshCw className="w-3 h-3 animate-spin" />
            ) : (
              <Send className="w-3 h-3" />
            )}
            <span>{publishingQuickPost ? "Posting..." : "Publish"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
