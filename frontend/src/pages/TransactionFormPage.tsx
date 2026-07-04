import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { PrimaryButton } from "../components/PrimaryButton";
import { SelectField } from "../components/SelectField";
import { useAccounts } from "../features/accounts/hooks";
import { useCategories } from "../features/categories/hooks";
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
};

export function TransactionFormPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { transactionId } = useParams<{ transactionId: string }>();
  const isEditing = transactionId !== undefined;

  const accounts = useAccounts();
  const categories = useCategories();
  const existing = useTransaction(transactionId);
  const createTransaction = useCreateTransactionMutation();
  const updateTransaction = useUpdateTransactionMutation();

  const [form, setForm] = useState<TransactionFormState>(EMPTY_FORM);
  const [hasHydrated, setHasHydrated] = useState(false);

  useEffect(() => {
    if (isEditing && existing.data && !hasHydrated) {
      setForm({
        accountId: existing.data.account_id,
        date: existing.data.date,
        amountDollars: formatCentsAsDollarsInput(existing.data.amount_cents),
        description: existing.data.description_display,
        categoryId: existing.data.category_id ?? "",
        notes: existing.data.notes ?? "",
      });
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
    };
    try {
      if (isEditing && transactionId) {
        await updateTransaction.mutateAsync({ id: transactionId, payload });
      } else {
        await createTransaction.mutateAsync(payload);
      }
      navigate("/transactions");
    } catch {
      // surfaced via activeMutation.error below
    }
  }

  if (isEditing && existing.isLoading) {
    return <p className="text-sm text-charcoal/60 dark:text-linen/60">{t("common.loading")}</p>;
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
        <FormField
          label={t("transactions.notesLabel")}
          name="notes"
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
        />
        <ErrorBanner message={errorMessage(activeMutation.error, t("common.genericError"))} />
        <div className="flex gap-3">
          <PrimaryButton
            type="submit"
            disabled={activeMutation.isPending}
            className="w-auto px-4"
          >
            {isEditing ? t("transactions.saveButton") : t("transactions.createButton")}
          </PrimaryButton>
          <button
            type="button"
            onClick={() => navigate("/transactions")}
            className="rounded-lg border border-charcoal/20 px-4 py-2.5 text-sm font-medium dark:border-linen/20"
          >
            {t("common.cancel")}
          </button>
        </div>
      </form>
    </div>
  );
}
