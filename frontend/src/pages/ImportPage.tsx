import { useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Card } from "../components/Card";
import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { PrimaryButton } from "../components/PrimaryButton";
import { SecondaryButton } from "../components/SecondaryButton";
import { SelectField } from "../components/SelectField";
import { useAccounts } from "../features/accounts/hooks";
import { useCategories } from "../features/categories/hooks";
import { useImportProfiles } from "../features/importProfiles/hooks";
import {
  useCommitImportMutation,
  usePasteImportMutation,
  usePreviewImportMutation,
  useUploadCsvMutation,
} from "../features/imports/hooks";
import type {
  ColumnMapping,
  DateFormat,
  ImportBatch,
  ImportPreviewResponse,
  ImportUploadResponse,
} from "../features/imports/types";
import { errorMessage } from "../lib/errors";
import { formatCentsDisplay } from "../lib/money";

type Step = "select" | "mapping" | "preview" | "done";

const EMPTY_MAPPING: ColumnMapping = { date: "", description: "", amount: "" };

export function ImportPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const accounts = useAccounts();
  const categories = useCategories();
  const profiles = useImportProfiles();

  const uploadCsv = useUploadCsvMutation();
  const pasteImport = usePasteImportMutation();
  const previewImport = usePreviewImportMutation();
  const commitImport = useCommitImportMutation();

  const [step, setStep] = useState<Step>("select");
  const [sourceMode, setSourceMode] = useState<"csv" | "paste">("csv");
  const [pasteText, setPasteText] = useState("");
  const [selectedProfileId, setSelectedProfileId] = useState("");

  const [uploadResult, setUploadResult] = useState<ImportUploadResponse | null>(null);
  const [accountId, setAccountId] = useState("");
  const [mapping, setMapping] = useState<ColumnMapping>(EMPTY_MAPPING);
  const [dateFormat, setDateFormat] = useState<DateFormat>("MDY");
  const [dateFormatConfirmed, setDateFormatConfirmed] = useState(true);

  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [rowDecisions, setRowDecisions] = useState<Record<number, boolean>>({});
  const [saveProfileName, setSaveProfileName] = useState("");
  const [result, setResult] = useState<ImportBatch | null>(null);

  const categoryById = new Map((categories.data ?? []).map((c) => [c.id, c]));

  function applyUploadResult(response: ImportUploadResponse) {
    setUploadResult(response);
    setMapping(response.suggested_mapping ?? EMPTY_MAPPING);
    setDateFormat(response.date_format_suggestion);
    setDateFormatConfirmed(!response.date_format_ambiguous);
    setStep("mapping");
  }

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const response = await uploadCsv.mutateAsync({
        file,
        profileId: selectedProfileId || undefined,
      });
      applyUploadResult(response);
    } catch {
      // surfaced via uploadCsv.error below
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handlePasteSubmit() {
    try {
      const response = await pasteImport.mutateAsync({
        text: pasteText,
        profileId: selectedProfileId || undefined,
      });
      applyUploadResult(response);
    } catch {
      // surfaced via pasteImport.error below
    }
  }

  async function handlePreview() {
    if (!uploadResult) return;
    try {
      const response = await previewImport.mutateAsync({
        sessionId: uploadResult.import_session_id,
        columnMapping: mapping,
        dateFormat,
        accountId,
      });
      setPreview(response);
      const decisions: Record<number, boolean> = {};
      for (const row of response.rows) decisions[row.row_index] = row.will_import;
      setRowDecisions(decisions);
      setStep("preview");
    } catch {
      // surfaced via previewImport.error below
    }
  }

  function toggleRow(rowIndex: number) {
    setRowDecisions((prev) => ({ ...prev, [rowIndex]: !prev[rowIndex] }));
  }

  async function handleCommit() {
    if (!uploadResult || !preview) return;
    const overrides: Record<string, boolean> = {};
    for (const row of preview.rows) {
      if (rowDecisions[row.row_index] !== row.will_import) {
        overrides[String(row.row_index)] = rowDecisions[row.row_index];
      }
    }
    try {
      const batch = await commitImport.mutateAsync({
        sessionId: uploadResult.import_session_id,
        columnMapping: mapping,
        dateFormat,
        accountId,
        overrides,
        saveProfileName: saveProfileName || undefined,
      });
      setResult(batch);
      setStep("done");
    } catch {
      // surfaced via commitImport.error below
    }
  }

  function resetWizard() {
    setStep("select");
    setUploadResult(null);
    setPreview(null);
    setRowDecisions({});
    setResult(null);
    setSaveProfileName("");
    setPasteText("");
  }

  const mappingComplete = Boolean(mapping.date && mapping.description && mapping.amount);
  const canPreview = mappingComplete && Boolean(accountId) && dateFormatConfirmed;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-semibold">{t("imports.title")}</h2>
        <Link
          to="/import/history"
          className="text-sm text-text-primary/70 underline-offset-2 hover:underline"
        >
          {t("imports.viewHistory")}
        </Link>
      </div>

      {step === "select" ? (
        <Card size="form" className="flex flex-col gap-4">
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setSourceMode("csv")}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                sourceMode === "csv"
                  ? "bg-ember-500 text-charcoal-950"
                  : "border border-border/20"
              }`}
            >
              {t("imports.uploadCsv")}
            </button>
            <button
              type="button"
              onClick={() => setSourceMode("paste")}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                sourceMode === "paste"
                  ? "bg-ember-500 text-charcoal-950"
                  : "border border-border/20"
              }`}
            >
              {t("imports.pasteData")}
            </button>
          </div>

          {(profiles.data ?? []).length > 0 ? (
            <SelectField
              label={t("imports.useProfile")}
              name="profile"
              value={selectedProfileId}
              onChange={(e) => setSelectedProfileId(e.target.value)}
            >
              <option value="">{t("imports.noProfile")}</option>
              {(profiles.data ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </SelectField>
          ) : null}

          {sourceMode === "csv" ? (
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-text-primary/80">
                {t("imports.csvFileLabel")}
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                onChange={handleFileChange}
                className="text-sm"
              />
              <ErrorBanner message={errorMessage(uploadCsv.error, t("common.genericError"))} />
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <label className="text-sm font-medium text-text-primary/80">
                {t("imports.pasteLabel")}
              </label>
              <textarea
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                rows={8}
                placeholder={t("imports.pastePlaceholder")}
                className="rounded-lg border border-border/15 bg-surface-subtle px-3 py-2 text-sm font-mono"
              />
              <ErrorBanner message={errorMessage(pasteImport.error, t("common.genericError"))} />
              <PrimaryButton
                type="button"
                className="w-auto px-4"
                disabled={!pasteText.trim() || pasteImport.isPending}
                onClick={handlePasteSubmit}
              >
                {t("imports.parseButton")}
              </PrimaryButton>
            </div>
          )}
        </Card>
      ) : null}

      {step === "mapping" && uploadResult ? (
        <Card size="form" className="flex flex-col gap-4">
          <p className="text-sm text-text-primary/60">
            {t("imports.rowsDetected", { count: uploadResult.row_count })}
          </p>

          <SelectField
            label={t("transactions.accountLabel")}
            name="account_id"
            required
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
          >
            <option value="" disabled>
              {t("transactions.selectAccount")}
            </option>
            {(accounts.data ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </SelectField>

          <div className="grid grid-cols-3 gap-4">
            <SelectField
              label={t("imports.dateColumn")}
              name="date_column"
              value={mapping.date}
              onChange={(e) => setMapping({ ...mapping, date: e.target.value })}
            >
              <option value="">{t("imports.selectColumn")}</option>
              {uploadResult.header.map((h) => (
                <option key={h} value={h}>
                  {h}
                </option>
              ))}
            </SelectField>
            <SelectField
              label={t("imports.descriptionColumn")}
              name="description_column"
              value={mapping.description}
              onChange={(e) => setMapping({ ...mapping, description: e.target.value })}
            >
              <option value="">{t("imports.selectColumn")}</option>
              {uploadResult.header.map((h) => (
                <option key={h} value={h}>
                  {h}
                </option>
              ))}
            </SelectField>
            <SelectField
              label={t("imports.amountColumn")}
              name="amount_column"
              value={mapping.amount}
              onChange={(e) => setMapping({ ...mapping, amount: e.target.value })}
            >
              <option value="">{t("imports.selectColumn")}</option>
              {uploadResult.header.map((h) => (
                <option key={h} value={h}>
                  {h}
                </option>
              ))}
            </SelectField>
          </div>

          <SelectField
            label={t("imports.dateFormatLabel")}
            name="date_format"
            value={dateFormat}
            onChange={(e) => {
              setDateFormat(e.target.value as DateFormat);
              setDateFormatConfirmed(true);
            }}
          >
            <option value="MDY">{t("imports.dateFormatMdy")}</option>
            <option value="DMY">{t("imports.dateFormatDmy")}</option>
            <option value="YMD">{t("imports.dateFormatYmd")}</option>
          </SelectField>

          {!dateFormatConfirmed ? (
            <div
              role="alert"
              className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-300"
            >
              {t("imports.dateFormatAmbiguousWarning")}
              <button
                type="button"
                onClick={() => setDateFormatConfirmed(true)}
                className="ml-2 underline"
              >
                {t("imports.confirmDateFormat")}
              </button>
            </div>
          ) : null}

          {uploadResult.sample_rows.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border border-border/10">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border/10">
                    {uploadResult.header.map((h) => (
                      <th key={h} className="px-2 py-1 text-left font-medium">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {uploadResult.sample_rows.slice(0, 5).map((row, i) => (
                    <tr key={i}>
                      {row.map((cell, j) => (
                        <td key={j} className="px-2 py-1">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          <ErrorBanner message={errorMessage(previewImport.error, t("common.genericError"))} />
          <div className="flex gap-3">
            <PrimaryButton
              type="button"
              className="px-4"
              disabled={!canPreview || previewImport.isPending}
              onClick={handlePreview}
            >
              {t("imports.previewButton")}
            </PrimaryButton>
            <SecondaryButton onClick={resetWizard}>{t("common.cancel")}</SecondaryButton>
          </div>
        </Card>
      ) : null}

      {step === "preview" && preview ? (
        <div className="flex flex-col gap-4">
          <div className="flex gap-4 text-sm text-text-primary/70">
            <span>{t("imports.validCount", { count: preview.valid_count })}</span>
            <span>{t("imports.errorCount", { count: preview.error_count })}</span>
            <span>{t("imports.exactDuplicateCount", { count: preview.exact_duplicate_count })}</span>
            <span>{t("imports.fuzzyDuplicateCount", { count: preview.fuzzy_duplicate_count })}</span>
          </div>

          <div className="max-h-96 overflow-y-auto rounded-lg border border-border/10">
            <table className="w-full text-sm">
              <tbody>
                {preview.rows.map((row) => {
                  const category = row.category_id ? categoryById.get(row.category_id) : undefined;
                  return (
                    <tr key={row.row_index} className="border-b border-border/10 last:border-0">
                      <td className="px-2 py-2">
                        <input
                          type="checkbox"
                          checked={rowDecisions[row.row_index] ?? false}
                          disabled={row.error !== null}
                          onChange={() => toggleRow(row.row_index)}
                        />
                      </td>
                      <td className="px-2 py-2 text-xs">{row.date ?? "—"}</td>
                      <td className="px-2 py-2">{row.description ?? "—"}</td>
                      <td className="px-2 py-2 text-right">
                        {row.amount_cents !== null ? formatCentsDisplay(row.amount_cents) : "—"}
                      </td>
                      <td className="px-2 py-2 text-xs">
                        {category ? `${category.icon} ${category.name}` : ""}
                      </td>
                      <td className="px-2 py-2 text-xs">
                        {row.error ? (
                          <span className="text-danger-600 dark:text-danger-400">{row.error}</span>
                        ) : row.duplicate === "exact" ? (
                          <span className="text-amber-700 dark:text-amber-400">
                            {t("imports.exactDuplicateBadge")}
                          </span>
                        ) : row.duplicate === "fuzzy" ? (
                          <span className="text-amber-600 dark:text-amber-300">
                            {t("imports.fuzzyDuplicateBadge")}
                          </span>
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <FormField
            label={t("imports.saveProfileLabel")}
            name="save_profile_name"
            value={saveProfileName}
            onChange={(e) => setSaveProfileName(e.target.value)}
            placeholder={t("imports.saveProfilePlaceholder")}
          />

          <ErrorBanner message={errorMessage(commitImport.error, t("common.genericError"))} />
          <div className="flex gap-3">
            <PrimaryButton
              type="button"
              className="px-4"
              disabled={commitImport.isPending}
              onClick={handleCommit}
            >
              {t("imports.commitButton")}
            </PrimaryButton>
            <SecondaryButton onClick={() => setStep("mapping")}>{t("common.back")}</SecondaryButton>
          </div>
        </div>
      ) : null}

      {step === "done" && result ? (
        <Card size="form" className="flex flex-col gap-4">
          <p className="font-medium">{t("imports.commitSuccess")}</p>
          <p className="text-sm text-text-primary/70">
            {t("imports.commitSummary", {
              imported: result.imported_count,
              skipped: result.skipped_dupes,
            })}
          </p>
          <div className="flex gap-3">
            <PrimaryButton type="button" className="px-4" onClick={() => navigate("/transactions")}>
              {t("imports.viewTransactions")}
            </PrimaryButton>
            <SecondaryButton onClick={resetWizard}>{t("imports.importAnother")}</SecondaryButton>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
