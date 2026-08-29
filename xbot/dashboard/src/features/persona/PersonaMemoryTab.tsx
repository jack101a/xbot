"use client";

import React from "react";
import { Brain, Save, CheckCircle2, AlertCircle, Upload } from "lucide-react";
import { PersonaMemoryTabProps } from "./types";
import { usePersonaMemory } from "./hooks/usePersonaMemory";
import { PersonaCardEditor } from "./components/PersonaCardEditor";
import { TopicsEditor } from "./components/TopicsEditor";
import { DiaryTimeline } from "./components/DiaryTimeline";
import { MemoryBankViewer } from "./components/MemoryBankViewer";
import { ImportCardModal } from "./components/ImportCardModal";

export function PersonaMemoryTab({ profileId, selectedProfile, onRefresh }: PersonaMemoryTabProps) {
  const {
    subSection, setSubSection,
    persona, setPersona,
    learnedState,
    diaryList,
    selectedDiaryDate, setSelectedDiaryDate,
    diaryContent, setDiaryContent,
    saving, reflecting, msg, setMsg,
    showCardModal, setShowCardModal,
    cardJson, setCardJson,
    importingCard, handleImportCard,
    handleSavePersona, handleTriggerReflection,
    newPrimaryTopic, setNewPrimaryTopic,
    newAntiTopic, setNewAntiTopic,
    handleAddPrimaryTopic, handleRemovePrimaryTopic,
    handleAddAntiTopic, handleRemoveAntiTopic
  } = usePersonaMemory(profileId, onRefresh);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Brain className="w-5 h-5 text-indigo-500" />
            <span>AI Persona & Cognitive Memory</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Configure authentic tone of voice, niche boundary guardrails, daily diary logs, and auto-learned heuristics.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={() => setShowCardModal(true)}
            className="flex items-center justify-center gap-1.5 px-3.5 py-2.5 rounded-xl text-xs font-semibold border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 transition shadow-sm w-full sm:w-auto"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Import Character Card</span>
          </button>

          <button
            onClick={handleSavePersona}
            disabled={saving}
            className="flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-600/20 transition disabled:opacity-50 w-full sm:w-auto"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? "Saving..." : "Save Persona"}</span>
          </button>
        </div>
      </div>

      {msg && (
        <div
          className={`p-4 rounded-xl flex items-center justify-between border ${
            msg.type === "success"
              ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
              : "bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300"
          }`}
        >
          <div className="flex items-center gap-3">
            {msg.type === "success" ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 flex-shrink-0" />}
            <span className="text-sm font-medium">{msg.text}</span>
          </div>
          <button onClick={() => setMsg(null)} className="text-xs font-semibold underline hover:opacity-75">
            Dismiss
          </button>
        </div>
      )}

      <div className="overflow-x-auto no-scrollbar flex gap-1 p-1 rounded-xl bg-slate-100 dark:bg-slate-800/60 w-full sm:max-w-xl">
        {(["identity", "topics", "diary", "learned"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setSubSection(tab)}
            className={`whitespace-nowrap flex-shrink-0 flex-1 min-w-[95px] py-2 px-3 rounded-lg text-xs font-semibold transition text-center ${
              subSection === tab
                ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            {tab === "identity" ? "Identity & Voice" : tab === "topics" ? "Topic Boundaries" : tab === "diary" ? "Daily Diary" : "Learned Memory"}
          </button>
        ))}
      </div>

      {subSection === "identity" && <PersonaCardEditor persona={persona} setPersona={setPersona} />}
      {subSection === "topics" && <TopicsEditor persona={persona} setPersona={setPersona} newPrimaryTopic={newPrimaryTopic} setNewPrimaryTopic={setNewPrimaryTopic} newAntiTopic={newAntiTopic} setNewAntiTopic={setNewAntiTopic} handleAddPrimaryTopic={handleAddPrimaryTopic} handleRemovePrimaryTopic={handleRemovePrimaryTopic} handleAddAntiTopic={handleAddAntiTopic} handleRemoveAntiTopic={handleRemoveAntiTopic} />}
      {subSection === "diary" && <DiaryTimeline diaryList={diaryList} selectedDiaryDate={selectedDiaryDate} setSelectedDiaryDate={setSelectedDiaryDate} diaryContent={diaryContent} setDiaryContent={setDiaryContent} />}
      {subSection === "learned" && <MemoryBankViewer learnedState={learnedState} reflecting={reflecting} handleTriggerReflection={handleTriggerReflection} />}

      <ImportCardModal showCardModal={showCardModal} setShowCardModal={setShowCardModal} cardJson={cardJson} setCardJson={setCardJson} importingCard={importingCard} handleImportCard={handleImportCard} />
    </div>
  );
}
