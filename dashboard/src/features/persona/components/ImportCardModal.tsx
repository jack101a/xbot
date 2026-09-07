import React from "react";

export function ImportCardModal({
  showCardModal,
  setShowCardModal,
  cardJson,
  setCardJson,
  importingCard,
  handleImportCard
}: {
  showCardModal: boolean;
  setShowCardModal: (v: boolean) => void;
  cardJson: string;
  setCardJson: (v: string) => void;
  importingCard: boolean;
  handleImportCard: () => void;
}) {
  if (!showCardModal) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-3 sm:p-4 z-50 animate-in fade-in duration-200">
      <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 sm:p-6 shadow-2xl space-y-4">
        <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white">Import Character Card / JSON</h3>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Paste your persona character card JSON (e.g. SillyTavern format or custom YAML/JSON) to automatically parse voice, style, and identity.
        </p>

        <textarea
          rows={7}
          value={cardJson}
          onChange={(e) => setCardJson(e.target.value)}
          placeholder="Paste JSON or character card text here..."
          className="w-full p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />

        <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-end gap-2 sm:gap-3 pt-2">
          <button
            onClick={() => setShowCardModal(false)}
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl text-xs font-semibold border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 text-center"
          >
            Cancel
          </button>
          <button
            onClick={handleImportCard}
            disabled={importingCard}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white transition disabled:opacity-50 text-center"
          >
            {importingCard ? "Importing..." : "Parse & Import"}
          </button>
        </div>
      </div>
    </div>
  );
}
