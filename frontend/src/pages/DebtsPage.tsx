import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Card } from "../components/Card";
import { DebtPayoffAnimation } from "../components/board/DebtPayoffAnimation";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { MoneyDisplay } from "../components/MoneyDisplay";
import { PrimaryButton } from "../components/PrimaryButton";
import { ProgressBar } from "../components/ProgressBar";
import { PropertyCard } from "../components/PropertyCard";
import { RowActionLink } from "../components/RowActionLink";
import { SecondaryButton } from "../components/SecondaryButton";
import { SelectField } from "../components/SelectField";
import { useReducedMotion } from "../design-system/useReducedMotion";
import { useAccounts } from "../features/accounts/hooks";
import {
  useArchiveDebtMutation,
  useCreateDebtMutation,
  useDebts,
  useLogDebtPaymentMutation,
  useUpdateDebtMutation,
} from "../features/debts/hooks";
import { DEBT_TYPES } from "../features/debts/types";
import type { Debt, DebtType } from "../features/debts/types";
import { errorMessage } from "../lib/errors";
import { formatBpsAsPercentDisplay, formatCentsAsDollarsInput, parseDollarsToCents } from "../lib/money";

interface DebtFormState {
  name: string;
  type: DebtType;
  originalBalanceDollars: string;
  currentBalanceDollars: string;
  aprPercent: string;
  minPaymentDollars: string;
  dueDay: string;
  icon: string;
  color: string;
}

// Property-card defaults for the Monopoly board's mortgage/railroad tiles --
// purely cosmetic, matching Goal's icon/color pattern but optional here
// since existing debts predate these fields.
const EMPTY_FORM: DebtFormState = {
  name: "",
  type: "credit_card",
  originalBalanceDollars: "0.00",
  currentBalanceDollars: "0.00",
  aprPercent: "0",
  minPaymentDollars: "0.00",
  dueDay: "1",
  icon: "💳",
  color: "#2c3463",
};

function toFormState(debt: Debt): DebtFormState {
  return {
    name: debt.name,
    type: debt.type,
    originalBalanceDollars: formatCentsAsDollarsInput(debt.original_balance_cents),
    currentBalanceDollars: formatCentsAsDollarsInput(debt.current_balance_cents),
    aprPercent: (debt.apr_bps / 100).toString(),
    minPaymentDollars: formatCentsAsDollarsInput(debt.min_payment_cents),
    dueDay: String(debt.due_day),
    icon: debt.icon ?? EMPTY_FORM.icon,
    color: debt.color ?? EMPTY_FORM.color,
  };
}

function today(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

interface PaymentFormState {
  accountId: string;
  amountDollars: string;
  date: string;
}

const EMPTY_PAYMENT_FORM: PaymentFormState = { accountId: "", amountDollars: "", date: today() };

// Fallback property-card look for debts predating icon/color -- Debt's
// fields are nullable (unlike Goal's), so PropertyCard always needs a value.
const FALLBACK_DEBT_ICON = "🏦";
const FALLBACK_DEBT_COLOR = "#2c3463";

export function DebtsPage() {
  const { t } = useTranslation();
  const prefersReducedMotion = useReducedMotion();
  const [includeArchived, setIncludeArchived] = useState(false);
  const debts = useDebts(includeArchived);
  const accounts = useAccounts();
  const createDebt = useCreateDebtMutation();
  const updateDebt = useUpdateDebtMutation();
  const archiveDebt = useArchiveDebtMutation();
  const logPayment = useLogDebtPaymentMutation();

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<DebtFormState>(EMPTY_FORM);

  const [payingId, setPayingId] = useState<string | null>(null);
  const [paymentForm, setPaymentForm] = useState<PaymentFormState>(EMPTY_PAYMENT_FORM);
  const [payoffCelebration, setPayoffCelebration] = useState<string | null>(null);

  const activeMutation = editingId ? updateDebt : createDebt;

  function openCreateForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setIsFormOpen(true);
  }

  function openEditForm(debt: Debt) {
    setEditingId(debt.id);
    setForm(toFormState(debt));
    setIsFormOpen(true);
  }

  function closeForm() {
    setIsFormOpen(false);
    setEditingId(null);
    createDebt.reset();
    updateDebt.reset();
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const payload = {
      name: form.name,
      type: form.type,
      original_balance_cents: parseDollarsToCents(form.originalBalanceDollars),
      current_balance_cents: parseDollarsToCents(form.currentBalanceDollars),
      apr_bps: Math.round(Number(form.aprPercent) * 100),
      min_payment_cents: parseDollarsToCents(form.minPaymentDollars),
      due_day: Number(form.dueDay),
      icon: form.icon,
      color: form.color,
    };
    try {
      if (editingId) {
        await updateDebt.mutateAsync({ id: editingId, payload });
      } else {
        await createDebt.mutateAsync(payload);
      }
      closeForm();
    } catch {
      // surfaced via activeMutation.error below
    }
  }

  async function handleArchive(id: string) {
    await archiveDebt.mutateAsync(id);
  }

  function openPaymentForm(debtId: string) {
    setPayingId(debtId);
    setPaymentForm(EMPTY_PAYMENT_FORM);
    logPayment.reset();
  }

  function closePaymentForm() {
    setPayingId(null);
    logPayment.reset();
  }

  async function handleLogPayment(event: FormEvent, debtId: string) {
    event.preventDefault();
    const amountCents = -Math.abs(parseDollarsToCents(paymentForm.amountDollars));
    const debt = debts.data?.find((d) => d.id === debtId);
    // Computed client-side from the same balance math the backend applies
    // (current_balance_cents += delta_cents) rather than waiting on the
    // debts query to refetch after invalidation -- avoids a race between
    // the mutation resolving and the list actually reflecting paid_off_at.
    const willPayOff =
      debt !== undefined &&
      debt.paid_off_at === null &&
      debt.current_balance_cents + amountCents <= 0;
    try {
      await logPayment.mutateAsync({
        debt_id: debtId,
        account_id: paymentForm.accountId,
        // Payments are logged as negative -- the amount typed in is the
        // payment size, applied as a balance-reducing (negative) transaction.
        amount_cents: amountCents,
        date: paymentForm.date,
      });
      closePaymentForm();
      if (willPayOff && debt) {
        setPayoffCelebration(debt.name);
      }
    } catch {
      // surfaced via logPayment.error below
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-semibold">{t("debts.title")}</h2>
        <PrimaryButton type="button" className="px-4 py-2" onClick={openCreateForm}>
          {t("debts.addButton")}
        </PrimaryButton>
      </div>

      {isFormOpen ? (
        <Card size="form">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <FormField
              label={t("debts.nameLabel")}
              name="name"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <SelectField
              label={t("debts.typeLabel")}
              name="type"
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value as DebtType })}
            >
              {DEBT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`debts.types.${type}`)}
                </option>
              ))}
            </SelectField>
            <div className="grid grid-cols-2 gap-4">
              <FormField
                label={t("debts.originalBalanceLabel")}
                name="original_balance"
                inputMode="decimal"
                value={form.originalBalanceDollars}
                onChange={(e) => setForm({ ...form, originalBalanceDollars: e.target.value })}
              />
              <FormField
                label={t("debts.currentBalanceLabel")}
                name="current_balance"
                inputMode="decimal"
                value={form.currentBalanceDollars}
                onChange={(e) => setForm({ ...form, currentBalanceDollars: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <FormField
                label={t("debts.aprLabel")}
                name="apr"
                inputMode="decimal"
                value={form.aprPercent}
                onChange={(e) => setForm({ ...form, aprPercent: e.target.value })}
              />
              <FormField
                label={t("debts.minPaymentLabel")}
                name="min_payment"
                inputMode="decimal"
                value={form.minPaymentDollars}
                onChange={(e) => setForm({ ...form, minPaymentDollars: e.target.value })}
              />
            </div>
            <FormField
              label={t("debts.dueDayLabel")}
              name="due_day"
              type="number"
              inputMode="numeric"
              min={1}
              max={31}
              required
              value={form.dueDay}
              onChange={(e) => setForm({ ...form, dueDay: e.target.value })}
            />
            <div className="grid grid-cols-2 gap-4">
              <FormField
                label={t("debts.iconLabel")}
                name="icon"
                value={form.icon}
                onChange={(e) => setForm({ ...form, icon: e.target.value })}
              />
              <FormField
                label={t("debts.colorLabel")}
                name="color"
                type="color"
                value={form.color}
                onChange={(e) => setForm({ ...form, color: e.target.value })}
              />
            </div>
            <ErrorBanner message={errorMessage(activeMutation.error, t("common.genericError"))} />
            <div className="flex gap-3">
              <PrimaryButton type="submit" disabled={activeMutation.isPending} className="px-4">
                {editingId ? t("debts.saveButton") : t("debts.createButton")}
              </PrimaryButton>
              <SecondaryButton onClick={closeForm}>{t("common.cancel")}</SecondaryButton>
            </div>
          </form>
        </Card>
      ) : null}

      <label className="flex items-center gap-2 text-sm text-text-primary/70">
        <input
          type="checkbox"
          checked={includeArchived}
          onChange={(e) => setIncludeArchived(e.target.checked)}
        />
        {t("debts.showArchived")}
      </label>

      <ul className="flex flex-col gap-3">
        {debts.data?.map((debt) => {
          const pct =
            debt.original_balance_cents > 0
              ? (debt.current_balance_cents / debt.original_balance_cents) * 100
              : 0;
          return (
            <li key={debt.id}>
              <PropertyCard
                color={debt.color ?? FALLBACK_DEBT_COLOR}
                icon={debt.icon ?? FALLBACK_DEBT_ICON}
                name={debt.name}
                owned={debt.paid_off_at !== null}
                ownedLabel={t("debts.paidOffBadge")}
                amount={<MoneyDisplay cents={debt.current_balance_cents} />}
              >
                <p className="text-xs text-text-primary/60">
                  {t(`debts.types.${debt.type}`)} · {formatBpsAsPercentDisplay(debt.apr_bps)}{" "}
                  {t("debts.aprSuffix")} · {t("debts.dueDayValue", { day: debt.due_day })}
                  {debt.archived ? (
                    <span className="ml-2 text-text-primary/50">{t("debts.archivedBadge")}</span>
                  ) : null}
                </p>
                <ProgressBar pct={pct} variant="boss" reduceMotion={prefersReducedMotion} />
                <div className="flex items-center gap-4">
                  {!debt.archived ? (
                    <RowActionLink onClick={() => openPaymentForm(debt.id)}>
                      {t("debts.logPaymentButton")}
                    </RowActionLink>
                  ) : null}
                  <RowActionLink onClick={() => openEditForm(debt)}>
                    {t("common.edit")}
                  </RowActionLink>
                  {!debt.archived ? (
                    <RowActionLink onClick={() => handleArchive(debt.id)}>
                      {t("common.archive")}
                    </RowActionLink>
                  ) : null}
                </div>

                {payingId === debt.id ? (
                  <form
                    onSubmit={(e) => handleLogPayment(e, debt.id)}
                    className="flex flex-col gap-3 rounded-lg border border-border/10 p-3"
                  >
                    <SelectField
                      label={t("debts.paymentAccountLabel")}
                      name="payment_account_id"
                      required
                      value={paymentForm.accountId}
                      onChange={(e) => setPaymentForm({ ...paymentForm, accountId: e.target.value })}
                    >
                      <option value="" disabled>
                        {t("debts.selectAccount")}
                      </option>
                      {(accounts.data ?? []).map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                    </SelectField>
                    <div className="grid grid-cols-2 gap-3">
                      <FormField
                        label={t("debts.paymentAmountLabel")}
                        name="payment_amount"
                        inputMode="decimal"
                        required
                        placeholder="100.00"
                        value={paymentForm.amountDollars}
                        onChange={(e) =>
                          setPaymentForm({ ...paymentForm, amountDollars: e.target.value })
                        }
                      />
                      <FormField
                        label={t("debts.paymentDateLabel")}
                        name="payment_date"
                        type="date"
                        required
                        value={paymentForm.date}
                        onChange={(e) => setPaymentForm({ ...paymentForm, date: e.target.value })}
                      />
                    </div>
                    <ErrorBanner message={errorMessage(logPayment.error, t("common.genericError"))} />
                    <div className="flex gap-3">
                      <PrimaryButton
                        type="submit"
                        disabled={logPayment.isPending}
                        className="px-4"
                      >
                        {t("debts.submitPaymentButton")}
                      </PrimaryButton>
                      <SecondaryButton onClick={closePaymentForm}>
                        {t("common.cancel")}
                      </SecondaryButton>
                    </div>
                  </form>
                ) : null}
              </PropertyCard>
            </li>
          );
        })}
      </ul>
      {debts.data?.length === 0 ? <EmptyState message={t("debts.empty")} /> : null}
      <DebtPayoffAnimation
        open={payoffCelebration !== null}
        debtName={payoffCelebration ?? ""}
        onDismiss={() => setPayoffCelebration(null)}
      />
    </div>
  );
}
