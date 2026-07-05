import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { PrimaryButton } from "../components/PrimaryButton";
import { SelectField } from "../components/SelectField";
import { useAccounts } from "../features/accounts/hooks";
import {
  useArchiveBillMutation,
  useBills,
  useCreateBillMutation,
  useMarkBillPaidMutation,
  useUpdateBillMutation,
} from "../features/bills/hooks";
import { BILL_FREQUENCIES } from "../features/bills/types";
import type { Bill, BillFrequency } from "../features/bills/types";
import { useCategories } from "../features/categories/hooks";
import { useTransactions } from "../features/transactions/hooks";
import { errorMessage } from "../lib/errors";
import { formatCentsAsDollarsInput, formatCentsDisplay, parseDollarsToCents } from "../lib/money";

interface BillFormState {
  name: string;
  amountDollars: string;
  isVariable: boolean;
  frequency: BillFrequency;
  dueDay: string;
  customIntervalDays: string;
  accountId: string;
  categoryId: string;
  autopay: boolean;
  nextDueDate: string;
}

function today(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const EMPTY_FORM: BillFormState = {
  name: "",
  amountDollars: "0.00",
  isVariable: false,
  frequency: "monthly",
  dueDay: "1",
  customIntervalDays: "",
  accountId: "",
  categoryId: "",
  autopay: false,
  nextDueDate: today(),
};

function toFormState(bill: Bill): BillFormState {
  return {
    name: bill.name,
    amountDollars: formatCentsAsDollarsInput(bill.amount_cents ?? 0),
    isVariable: bill.is_variable,
    frequency: bill.frequency,
    dueDay: String(bill.due_day),
    customIntervalDays: bill.custom_interval_days ? String(bill.custom_interval_days) : "",
    accountId: bill.account_id ?? "",
    categoryId: bill.category_id ?? "",
    autopay: bill.autopay,
    nextDueDate: bill.next_due_date,
  };
}

type MarkPaidMode = "quick_create" | "link_existing";

interface MarkPaidFormState {
  mode: MarkPaidMode;
  accountId: string;
  amountDollars: string;
  date: string;
  transactionId: string;
}

const EMPTY_MARK_PAID_FORM: MarkPaidFormState = {
  mode: "quick_create",
  accountId: "",
  amountDollars: "",
  date: today(),
  transactionId: "",
};

export function BillsPage() {
  const { t } = useTranslation();
  const [includeArchived, setIncludeArchived] = useState(false);
  const bills = useBills(includeArchived);
  const accounts = useAccounts();
  const categories = useCategories();
  const createBill = useCreateBillMutation();
  const updateBill = useUpdateBillMutation();
  const archiveBill = useArchiveBillMutation();
  const markPaid = useMarkBillPaidMutation();

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<BillFormState>(EMPTY_FORM);

  const [markPayingId, setMarkPayingId] = useState<string | null>(null);
  const [markPaidForm, setMarkPaidForm] = useState<MarkPaidFormState>(EMPTY_MARK_PAID_FORM);

  // Small, fixed-size fetch to populate the "link existing transaction"
  // picker below -- there's no dedicated transaction-search endpoint yet, so
  // this reuses the plain recent-transactions list.
  const recentTransactions = useTransactions({ limit: 25 });

  const activeMutation = editingId ? updateBill : createBill;

  function openCreateForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setIsFormOpen(true);
  }

  function openEditForm(bill: Bill) {
    setEditingId(bill.id);
    setForm(toFormState(bill));
    setIsFormOpen(true);
  }

  function closeForm() {
    setIsFormOpen(false);
    setEditingId(null);
    createBill.reset();
    updateBill.reset();
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const payload = {
      name: form.name,
      amount_cents: form.isVariable ? null : parseDollarsToCents(form.amountDollars),
      is_variable: form.isVariable,
      frequency: form.frequency,
      due_day: Number(form.dueDay),
      custom_interval_days:
        form.frequency === "custom" && form.customIntervalDays
          ? Number(form.customIntervalDays)
          : null,
      account_id: form.accountId || null,
      category_id: form.categoryId || null,
      autopay: form.autopay,
      next_due_date: form.nextDueDate,
    };
    try {
      if (editingId) {
        await updateBill.mutateAsync({ id: editingId, payload });
      } else {
        await createBill.mutateAsync(payload);
      }
      closeForm();
    } catch {
      // surfaced via activeMutation.error below
    }
  }

  async function handleArchive(id: string) {
    await archiveBill.mutateAsync(id);
  }

  function openMarkPaidForm(bill: Bill) {
    setMarkPayingId(bill.id);
    setMarkPaidForm({
      ...EMPTY_MARK_PAID_FORM,
      accountId: bill.account_id ?? "",
      amountDollars: bill.amount_cents !== null ? formatCentsAsDollarsInput(bill.amount_cents) : "",
    });
    markPaid.reset();
  }

  function closeMarkPaidForm() {
    setMarkPayingId(null);
    markPaid.reset();
  }

  async function handleMarkPaid(event: FormEvent, billId: string) {
    event.preventDefault();
    try {
      if (markPaidForm.mode === "link_existing") {
        await markPaid.mutateAsync({
          id: billId,
          payload: { transaction_id: markPaidForm.transactionId },
        });
      } else {
        await markPaid.mutateAsync({
          id: billId,
          payload: {
            account_id: markPaidForm.accountId,
            amount_cents: -Math.abs(parseDollarsToCents(markPaidForm.amountDollars)),
            date: markPaidForm.date,
          },
        });
      }
      closeMarkPaidForm();
    } catch {
      // surfaced via markPaid.error below
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-semibold">{t("bills.title")}</h2>
        <PrimaryButton type="button" className="w-auto px-4 py-2" onClick={openCreateForm}>
          {t("bills.addButton")}
        </PrimaryButton>
      </div>

      {isFormOpen ? (
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 rounded-2xl border border-charcoal/10 bg-white/60 p-6 dark:border-linen/10 dark:bg-white/[0.03]"
        >
          <FormField
            label={t("bills.nameLabel")}
            name="name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <label className="flex items-center gap-2 text-sm text-charcoal/70 dark:text-linen/70">
            <input
              type="checkbox"
              checked={form.isVariable}
              onChange={(e) => setForm({ ...form, isVariable: e.target.checked })}
            />
            {t("bills.isVariableLabel")}
          </label>
          {!form.isVariable ? (
            <FormField
              label={t("bills.amountLabel")}
              name="amount"
              inputMode="decimal"
              value={form.amountDollars}
              onChange={(e) => setForm({ ...form, amountDollars: e.target.value })}
            />
          ) : null}
          <div className="grid grid-cols-2 gap-4">
            <SelectField
              label={t("bills.frequencyLabel")}
              name="frequency"
              value={form.frequency}
              onChange={(e) => setForm({ ...form, frequency: e.target.value as BillFrequency })}
            >
              {BILL_FREQUENCIES.map((freq) => (
                <option key={freq} value={freq}>
                  {t(`bills.frequencies.${freq}`)}
                </option>
              ))}
            </SelectField>
            <FormField
              label={t("bills.dueDayLabel")}
              name="due_day"
              type="number"
              min={1}
              max={31}
              required
              value={form.dueDay}
              onChange={(e) => setForm({ ...form, dueDay: e.target.value })}
            />
          </div>
          {form.frequency === "custom" ? (
            <FormField
              label={t("bills.customIntervalDaysLabel")}
              name="custom_interval_days"
              type="number"
              min={1}
              required
              value={form.customIntervalDays}
              onChange={(e) => setForm({ ...form, customIntervalDays: e.target.value })}
            />
          ) : null}
          <FormField
            label={t("bills.nextDueDateLabel")}
            name="next_due_date"
            type="date"
            required
            value={form.nextDueDate}
            onChange={(e) => setForm({ ...form, nextDueDate: e.target.value })}
          />
          <SelectField
            label={t("bills.accountLabel")}
            name="account_id"
            value={form.accountId}
            onChange={(e) => setForm({ ...form, accountId: e.target.value })}
          >
            <option value="">{t("bills.noAccount")}</option>
            {(accounts.data ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </SelectField>
          <SelectField
            label={t("bills.categoryLabel")}
            name="category_id"
            value={form.categoryId}
            onChange={(e) => setForm({ ...form, categoryId: e.target.value })}
          >
            <option value="">{t("bills.noCategory")}</option>
            {(categories.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.icon} {c.name}
              </option>
            ))}
          </SelectField>
          <label className="flex items-center gap-2 text-sm text-charcoal/70 dark:text-linen/70">
            <input
              type="checkbox"
              checked={form.autopay}
              onChange={(e) => setForm({ ...form, autopay: e.target.checked })}
            />
            {t("bills.autopayLabel")}
          </label>
          <ErrorBanner message={errorMessage(activeMutation.error, t("common.genericError"))} />
          <div className="flex gap-3">
            <PrimaryButton type="submit" disabled={activeMutation.isPending} className="w-auto px-4">
              {editingId ? t("bills.saveButton") : t("bills.createButton")}
            </PrimaryButton>
            <button
              type="button"
              onClick={closeForm}
              className="rounded-lg border border-charcoal/20 px-4 py-2.5 text-sm font-medium dark:border-linen/20"
            >
              {t("common.cancel")}
            </button>
          </div>
        </form>
      ) : null}

      <label className="flex items-center gap-2 text-sm text-charcoal/70 dark:text-linen/70">
        <input
          type="checkbox"
          checked={includeArchived}
          onChange={(e) => setIncludeArchived(e.target.checked)}
        />
        {t("bills.showArchived")}
      </label>

      <ul className="flex flex-col gap-3">
        {bills.data?.map((bill) => (
          <li
            key={bill.id}
            className="flex flex-col gap-3 rounded-xl border border-charcoal/10 bg-white/60 px-4 py-3 dark:border-linen/10 dark:bg-white/[0.03]"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">
                  {bill.name}
                  {bill.archived ? (
                    <span className="ml-2 text-xs text-charcoal/50 dark:text-linen/50">
                      {t("bills.archivedBadge")}
                    </span>
                  ) : null}
                </p>
                <p className="text-xs text-charcoal/60 dark:text-linen/60">
                  {t(`bills.frequencies.${bill.frequency}`)} ·{" "}
                  {t("bills.nextDueValue", { date: bill.next_due_date })}
                </p>
              </div>
              <div className="flex items-center gap-4">
                <span className="font-medium">
                  {bill.amount_cents !== null ? formatCentsDisplay(bill.amount_cents) : "—"}
                </span>
                {!bill.archived ? (
                  <button
                    type="button"
                    onClick={() => openMarkPaidForm(bill)}
                    className="text-sm text-charcoal/70 underline-offset-2 hover:underline dark:text-linen/70"
                  >
                    {t("bills.markPaidButton")}
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => openEditForm(bill)}
                  className="text-sm text-charcoal/70 underline-offset-2 hover:underline dark:text-linen/70"
                >
                  {t("common.edit")}
                </button>
                {!bill.archived ? (
                  <button
                    type="button"
                    onClick={() => handleArchive(bill.id)}
                    className="text-sm text-charcoal/70 underline-offset-2 hover:underline dark:text-linen/70"
                  >
                    {t("common.archive")}
                  </button>
                ) : null}
              </div>
            </div>

            {markPayingId === bill.id ? (
              <form
                onSubmit={(e) => handleMarkPaid(e, bill.id)}
                className="flex flex-col gap-3 rounded-lg border border-charcoal/10 p-3 dark:border-linen/10"
              >
                <div className="flex gap-4 text-sm">
                  <label className="flex items-center gap-1.5">
                    <input
                      type="radio"
                      checked={markPaidForm.mode === "quick_create"}
                      onChange={() => setMarkPaidForm({ ...markPaidForm, mode: "quick_create" })}
                    />
                    {t("bills.quickCreateMode")}
                  </label>
                  <label className="flex items-center gap-1.5">
                    <input
                      type="radio"
                      checked={markPaidForm.mode === "link_existing"}
                      onChange={() => setMarkPaidForm({ ...markPaidForm, mode: "link_existing" })}
                    />
                    {t("bills.linkExistingMode")}
                  </label>
                </div>

                {markPaidForm.mode === "quick_create" ? (
                  <>
                    <SelectField
                      label={t("bills.paymentAccountLabel")}
                      name="mark_paid_account_id"
                      required
                      value={markPaidForm.accountId}
                      onChange={(e) => setMarkPaidForm({ ...markPaidForm, accountId: e.target.value })}
                    >
                      <option value="" disabled>
                        {t("bills.selectAccount")}
                      </option>
                      {(accounts.data ?? []).map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                    </SelectField>
                    <div className="grid grid-cols-2 gap-3">
                      <FormField
                        label={t("bills.paymentAmountLabel")}
                        name="mark_paid_amount"
                        inputMode="decimal"
                        required
                        value={markPaidForm.amountDollars}
                        onChange={(e) =>
                          setMarkPaidForm({ ...markPaidForm, amountDollars: e.target.value })
                        }
                      />
                      <FormField
                        label={t("bills.paymentDateLabel")}
                        name="mark_paid_date"
                        type="date"
                        required
                        value={markPaidForm.date}
                        onChange={(e) => setMarkPaidForm({ ...markPaidForm, date: e.target.value })}
                      />
                    </div>
                  </>
                ) : (
                  <SelectField
                    label={t("bills.linkTransactionLabel")}
                    name="mark_paid_transaction_id"
                    required
                    value={markPaidForm.transactionId}
                    onChange={(e) =>
                      setMarkPaidForm({ ...markPaidForm, transactionId: e.target.value })
                    }
                  >
                    <option value="" disabled>
                      {t("bills.selectTransaction")}
                    </option>
                    {(recentTransactions.data?.items ?? []).map((txn) => (
                      <option key={txn.id} value={txn.id}>
                        {txn.date} · {txn.description_display} · {formatCentsDisplay(txn.amount_cents)}
                      </option>
                    ))}
                  </SelectField>
                )}

                <ErrorBanner message={errorMessage(markPaid.error, t("common.genericError"))} />
                <div className="flex gap-3">
                  <PrimaryButton type="submit" disabled={markPaid.isPending} className="w-auto px-4">
                    {t("bills.submitMarkPaidButton")}
                  </PrimaryButton>
                  <button
                    type="button"
                    onClick={closeMarkPaidForm}
                    className="rounded-lg border border-charcoal/20 px-4 py-2.5 text-sm font-medium dark:border-linen/20"
                  >
                    {t("common.cancel")}
                  </button>
                </div>
              </form>
            ) : null}
          </li>
        ))}
        {bills.data?.length === 0 ? (
          <p className="py-8 text-center text-sm text-charcoal/60 dark:text-linen/60">
            {t("bills.empty")}
          </p>
        ) : null}
      </ul>
    </div>
  );
}
