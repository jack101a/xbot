import React from "react";
import { BookOpen, ArrowRight, FileText } from "lucide-react";
import { DiaryEntry } from "../types";

export function DiaryTimeline({
  diaryList,
  selectedDiaryDate,
  setSelectedDiaryDate,
  diaryContent,
  setDiaryContent
}: {
  diaryList: DiaryEntry[];
  selectedDiaryDate: string | null;
  setSelectedDiaryDate: (d: string) => void;
  diaryContent: string;
  setDiaryContent: (c: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
      <div className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-2">
        <h3 className="font-bold text-xs uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-3">
          Diary Entries Log
        </h3>
        {diaryList.length > 0 ? (
          <div className="space-y-1 max-h-60 lg:max-h-[420px] overflow-y-auto pr-1">
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

      <div className="lg:col-span-2 p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
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
  );
}
