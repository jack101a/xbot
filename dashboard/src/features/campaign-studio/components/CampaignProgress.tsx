import React from "react";
import { Search } from "lucide-react";
import { CampaignStatus } from "../types";

interface CampaignProgressProps {
  campaignStatus: CampaignStatus | null;
  isGenerating: boolean;
}

export function CampaignProgress({ campaignStatus, isGenerating }: CampaignProgressProps) {
  if (!isGenerating && !campaignStatus) return null;

  return (
    <div className="bg-slate-900 border border-indigo-500/30 p-4 rounded-xl space-y-3 shadow-sm mb-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-ping" />
          <span className="text-xs font-bold text-slate-200">
            {campaignStatus?.status === "ready"
              ? "Campaign Ready for Publishing"
              : "Live Campaign Pipeline in Progress"}
          </span>
        </div>
        <span className="text-[11px] font-mono font-bold text-indigo-400 bg-indigo-950/80 px-2 py-0.5 rounded-full border border-indigo-800/60">
          {campaignStatus?.progress_percent || 0}%
        </span>
      </div>

      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-500 transition-all duration-500 ease-out"
          style={{ width: `${campaignStatus?.progress_percent || 5}%` }}
        />
      </div>

      <div className="text-[11px] text-slate-300 font-mono flex items-center gap-2 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
        <Search className="w-3.5 h-3.5 text-sky-400 animate-pulse flex-shrink-0" />
        <span className="truncate">
          {campaignStatus?.current_step || "Initializing research..."}
        </span>
      </div>

      {campaignStatus?.plan && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2 border-t border-slate-800">
          <div className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/50">
            <div className="text-[10px] uppercase font-bold text-slate-400">Campaign Title</div>
            <div className="text-xs font-semibold text-slate-200 truncate mt-0.5">
              {campaignStatus.plan.campaign_title}
            </div>
          </div>
          <div className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/50">
            <div className="text-[10px] uppercase font-bold text-slate-400">Theme</div>
            <div className="text-xs font-semibold text-slate-200 truncate mt-0.5">
              {campaignStatus.plan.theme}
            </div>
          </div>
          <div className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/50">
            <div className="text-[10px] uppercase font-bold text-slate-400">Deliverables</div>
            <div className="text-xs font-semibold text-indigo-300 mt-0.5">
              {campaignStatus.plan.deliverables?.length || 0} Assets Planned
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
