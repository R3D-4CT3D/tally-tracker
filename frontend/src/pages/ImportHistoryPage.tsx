import { useTranslation } from "react-i18next";

import { useImportBatches, useUndoImportBatchMutation } from "../features/imports/hooks";

export function ImportHistoryPage() {
  const { t } = useTranslation();
  const batches = useImportBatches();
  const undoBatch = useUndoImportBatchMutation();

  async function handleUndo(batchId: string) {
    if (!window.confirm(t("imports.confirmUndo"))) return;
    await undoBatch.mutateAsync(batchId);
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <h2 className="font-display text-xl font-semibold">{t("imports.historyTitle")}</h2>

      <ul className="flex flex-col gap-3">
        {(batches.data ?? []).map((batch) => (
          <li
            key={batch.id}
            className="flex items-center justify-between rounded-xl border border-charcoal/10 bg-white/60 px-4 py-3 dark:border-linen/10 dark:bg-white/[0.03]"
          >
            <div>
              <p className="font-medium">{batch.filename ?? t("imports.pastedData")}</p>
              <p className="text-xs text-charcoal/60 dark:text-linen/60">
                {t("imports.batchSummary", {
                  imported: batch.imported_count,
                  skipped: batch.skipped_dupes,
                  total: batch.row_count,
                })}
                {" · "}
                {new Date(batch.created_at).toLocaleString()}
              </p>
            </div>
            {batch.undoable ? (
              <button
                type="button"
                onClick={() => handleUndo(batch.id)}
                className="text-sm text-charcoal/70 underline-offset-2 hover:underline dark:text-linen/70"
              >
                {t("imports.undoButton")}
              </button>
            ) : (
              <span className="text-xs text-charcoal/40 dark:text-linen/40">
                {t("imports.undoExpired")}
              </span>
            )}
          </li>
        ))}
        {(batches.data ?? []).length === 0 ? (
          <p className="py-8 text-center text-sm text-charcoal/60 dark:text-linen/60">
            {t("imports.noBatches")}
          </p>
        ) : null}
      </ul>
    </div>
  );
}
