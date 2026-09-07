import React from "react";
import { Layers, Send, Calendar } from "lucide-react";
import { DeliverableCard } from "./DeliverableCard";
import { CampaignStatus, Deliverable } from "../types";

interface DeliverablesBoardProps {
  campaignStatus: CampaignStatus;
  selectedDeliverableIds: string[];
  toggleSelectDeliverable: (contentId: string) => void;
  selectAllDeliverables: () => void;
  deselectAllDeliverables: () => void;
  scheduleInterval: number;
  setScheduleInterval: (interval: number) => void;
  isPublishing: boolean;
  handlePublishDeliverables: (mode: "instant" | "schedule") => void;
  handlePublishSingleDeliverable: (contentId: string, mode: "instant" | "schedule") => void;
  publishingItemIds: string[];
  publishedStatus: Record<string, string>;
}

export function DeliverablesBoard({
  campaignStatus,
  selectedDeliverableIds,
  toggleSelectDeliverable,
  selectAllDeliverables,
  deselectAllDeliverables,
  scheduleInterval,
  setScheduleInterval,
  isPublishing,
  handlePublishDeliverables,
  handlePublishSingleDeliverable,
  publishingItemIds,
  publishedStatus,
}: DeliverablesBoardProps) {
  if (!campaignStatus?.deliverables || campaignStatus.deliverables.length === 0) return null;

  return (
    <div className="space-y-4 flex-1 flex flex-col">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100 dark:border-slate-800">
        <div>
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-500" />
            Generated Deliverables ({campaignStatus.deliverables.length})
          </h2>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Select items to publish instantly or schedule with custom spacing.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={selectAllDeliverables}
            className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/40 transition cursor-pointer"
          >
            Select All
          </button>
          <button
            onClick={deselectAllDeliverables}
            className="text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/40 transition cursor-pointer"
          >
            Clear
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {campaignStatus.deliverables.map((item: Deliverable, idx: number) => {
          const isSelected = selectedDeliverableIds.includes(item.content_id);
          return (
            <DeliverableCard
              key={idx}
              item={item}
              idx={idx}
              isSelected={isSelected}
              toggleSelectDeliverable={toggleSelectDeliverable}
              handlePublishSingleDeliverable={handlePublishSingleDeliverable}
              publishingItemIds={publishingItemIds}
              publishedStatus={publishedStatus}
            />
          );
        })}
      </div>

      <div className="sticky bottom-0 z-20 mt-4 bg-white dark:bg-slate-900 border border-indigo-500/40 p-3 rounded-xl shadow-lg flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
            {selectedDeliverableIds.length} of {campaignStatus.deliverables.length} Selected
          </span>
          <div className="h-4 w-px bg-slate-300 dark:bg-slate-700 hidden sm:block" />
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <span>Spacing:</span>
            <select
              value={scheduleInterval}
              onChange={(e) => setScheduleInterval(Number(e.target.value))}
              className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value={30}>30 mins</option>
              <option value={60}>60 mins (Recommended)</option>
              <option value={120}>2 hours</option>
              <option value={240}>4 hours</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={() => handlePublishDeliverables("instant")}
            disabled={isPublishing || selectedDeliverableIds.length === 0}
            className="flex-1 sm:flex-initial px-3.5 py-1.5 rounded-lg text-xs font-bold bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 flex items-center justify-center gap-1.5 transition disabled:opacity-50 cursor-pointer"
          >
            <Send className="w-3.5 h-3.5 text-sky-500" />
            Publish Selected Now
          </button>

          <button
            onClick={() => handlePublishDeliverables("schedule")}
            disabled={isPublishing || selectedDeliverableIds.length === 0}
            className="flex-1 sm:flex-initial px-4 py-1.5 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-500/20 flex items-center justify-center gap-1.5 transition disabled:opacity-50 cursor-pointer"
          >
            <Calendar className="w-3.5 h-3.5" />
            Auto-Schedule ({scheduleInterval}m)
          </button>
        </div>
      </div>
    </div>
  );
}
