import { useTranslation } from "react-i18next";

import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { RowActionLink } from "../components/RowActionLink";
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
          <li key={batch.id}>
            <Card size="row" className="flex items-center justify-between">
              <div>
                <p className="font-medium">{batch.filename ?? t("imports.pastedData")}</p>
                <p className="text-xs text-text-primary/60">
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
                <RowActionLink onClick={() => handleUndo(batch.id)}>
                  {t("imports.undoButton")}
                </RowActionLink>
              ) : (
                <span className="text-xs text-text-primary/40">{t("imports.undoExpired")}</span>
              )}
            </Card>
          </li>
        ))}
      </ul>
      {(batches.data ?? []).length === 0 ? <EmptyState message={t("imports.noBatches")} /> : null}
    </div>
  );
}
