import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Card } from "../components/Card";
import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { PrimaryButton } from "../components/PrimaryButton";
import { SecondaryButton } from "../components/SecondaryButton";
import { SelectField } from "../components/SelectField";
import { useAccounts } from "../features/accounts/hooks";
import { useCategories } from "../features/categories/hooks";
import { useDebts } from "../features/debts/hooks";
import { useCreateRuleMutation } from "../features/rules/hooks";
import {
  useCreateTransactionMutation,
  useTransaction,
  useUpdateTransactionMutation,
} from "../features/transactions/hooks";
import { errorMessage } from "../lib/errors";
import { formatCentsAsDollarsInput, parseDollarsToCents } from "../lib/money";

interface TransactionFormState {
  accountId: string;
  date: string;
  amountDollars: string;
  description: string;
  categoryId: string;
  notes: string;
  debtId: string;
  flaggedUnexpected: boolean;
}

function today(): string {
  // Local date components, not toISOString() -- that converts to UTC, which
  // silently rolls the default date forward to tomorrow for anyone west of
  // UTC in the evening (verified live: a WSL2 container came out a day
  // ahead of the host's local date this way during browser verification).
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const EMPTY_FORM: TransactionFormState = {
  accountId: "",
  date: today(),
  amountDollars: "",
  description: "",
  categoryId: "",
  notes: "",
  debtId: "",
  flaggedUnexpected: false,
};

export function TransactionFormPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { transactionId } = useParams<{ transactionId: string }>();
  const isEditing = transactionId !== undefined;

  const accounts = useAccounts();
  const categories = useCategories();
  const debts = useDebts();
  const existing = useTransaction(transactionId);
  const createTransaction = useCreateTransactionMutation();
  const updateTransaction = useUpdateTransactionMutation();
  const createRule = useCreateRuleMutation();

  const [form, setForm] = useState<TransactionFormState>(EMPTY_FORM);
  const [hasHydrated, setHasHydrated] = useState(false);
  const [originalCategoryId, setOriginalCategoryId] = useState<string>("");
  const [rulePrompt, setRulePrompt] = useState<{ description: string; categoryId: string } | null>(
    null,
  );

  useEffect(() => {
    if (isEditing && existing.data && !hasHydrated) {
      setForm({
        accountId: existing.data.account_id,
        date: existing.data.date,
        amountDollars: formatCentsAsDollarsInput(existing.data.amount_cents),
        description: existing.data.description_display,
        categoryId: existing.data.category_id ?? "",
        notes: existing.data.notes ?? "",
        debtId: existing.data.debt_id ?? "",
        flaggedUnexpected: existing.data.flagged_unexpected,
      });
      setOriginalCategoryId(existing.data.category_id ?? "");
      setHasHydrated(true);
    }
  }, [isEditing, existing.data, hasHydrated]);

  const activeMutation = isEditing ? updateTransaction : createTransaction;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const payload = {
      account_id: form.accountId,
      date: form.date,
      amount_cents: parseDollarsToCents(form.amountDollars),
      description: form.description,
      category_id: form.categoryId || null,
      notes: form.notes || null,
      debt_id: form.debtId || null,
      flagged_unexpected: form.flaggedUnexpected,
    };
    try {
      if (isEditing && transactionId) {
        await updateTransaction.mutateAsync({ id: transactionId, payload });
        // A manual recategorization is exactly the moment to offer "create a
        // rule from this" -- only when the category actually changed to a
        // real value, not on every save.
        if (form.categoryId && form.categoryId !== originalCategoryId) {
          setRulePrompt({ description: form.description, categoryId: form.categoryId });
          return;
        }
      } else {
        await createTransaction.mutateAsync(payload);
      }
      navigate("/transactions");
    } catch {
      // surfaced via activeMutation.error below
    }
  }

  async function handleCreateRuleFromCorrection() {
    if (!rulePrompt) return;
    try {
      await createRule.mutateAsync({
        match_type: "contains",
        match_value: rulePrompt.description,
        set_category_id: rulePrompt.categoryId,
      });
    } finally {
      navigate("/transactions");
    }
  }

  if (rulePrompt) {
    return (
      <Card size="form" className="mx-auto max-w-xl">
        <h2 className="font-display text-lg font-semibold">
          {t("rules.createFromCorrectionTitle")}
        </h2>
        <p className="mt-2 text-sm text-text-primary/70">
          {t("rules.createFromCorrectionBody", { description: rulePrompt.description })}
        </p>
        <ErrorBanner message={errorMessage(createRule.error, t("common.genericError"))} />
        <div className="mt-4 flex gap-3">
          <PrimaryButton
            type="button"
            className="px-4"
            disabled={createRule.isPending}
            onClick={handleCreateRuleFromCorrection}
          >
            {t("rules.createFromCorrectionConfirm")}
          </PrimaryButton>
          <SecondaryButton onClick={() => navigate("/transactions")}>
            {t("rules.createFromCorrectionSkip")}
          </SecondaryButton>
        </div>
      </Card>
    );
  }

  if (isEditing && existing.isLoading) {
    return <p className="text-sm text-text-primary/60">{t("common.loading")}</p>;
  }

  return (
    <div className="mx-auto max-w-xl">
      <h2 className="font-display text-xl font-semibold">
        {isEditing ? t("transactions.editTitle") : t("transactions.newTitle")}
      </h2>
      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4" noValidate>
        <SelectField
          label={t("transactions.accountLabel")}
          name="account_id"
          required
          value={form.accountId}
          onChange={(e) => setForm({ ...form, accountId: e.target.value })}
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
        <FormField
          label={t("transactions.dateLabel")}
          name="date"
          type="date"
          required
          value={form.date}
          onChange={(e) => setForm({ ...form, date: e.target.value })}
        />
        <FormField
          label={t("transactions.amountLabel")}
          name="amount"
          inputMode="decimal"
          required
          placeholder="-12.50"
          value={form.amountDollars}
          onChange={(e) => setForm({ ...form, amountDollars: e.target.value })}
        />
        <FormField
          label={t("transactions.descriptionLabel")}
          name="description"
          required
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        <SelectField
          label={t("transactions.categoryLabel")}
          name="category_id"
          value={form.categoryId}
          onChange={(e) => setForm({ ...form, categoryId: e.target.value })}
        >
          <option value="">{t("transactions.noCategory")}</option>
          {(categories.data ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.icon} {c.name}
            </option>
          ))}
        </SelectField>
        <SelectField
          label={t("transactions.debtLabel")}
          name="debt_id"
          value={form.debtId}
          onChange={(e) => setForm({ ...form, debtId: e.target.value })}
        >
          <option value="">{t("transactions.noDebt")}</option>
          {(debts.data ?? []).map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </SelectField>
        <FormField
          label={t("transactions.notesLabel")}
          name="notes"
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
        />
        <label className="flex min-h-11 items-center gap-2 text-sm text-text-primary/80">
          <input
            type="checkbox"
            checked={form.flaggedUnexpected}
            onChange={(e) => setForm({ ...form, flaggedUnexpected: e.target.checked })}
          />
          {t("transactions.flagUnexpectedLabel")}
        </label>
        <ErrorBanner message={errorMessage(activeMutation.error, t("common.genericError"))} />
        <div className="flex gap-3">
          <PrimaryButton type="submit" disabled={activeMutation.isPending} className="px-4">
            {isEditing ? t("transactions.saveButton") : t("transactions.createButton")}
          </PrimaryButton>
          <SecondaryButton onClick={() => navigate("/transactions")}>
            {t("common.cancel")}
          </SecondaryButton>
        </div>
      </form>
    </div>
  );
}
