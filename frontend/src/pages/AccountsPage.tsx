import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { PrimaryButton } from "../components/PrimaryButton";
import { SelectField } from "../components/SelectField";
import {
  useAccounts,
  useArchiveAccountMutation,
  useCreateAccountMutation,
  useUpdateAccountMutation,
} from "../features/accounts/hooks";
import { ACCOUNT_TYPES } from "../features/accounts/types";
import type { Account, AccountType } from "../features/accounts/types";
import { errorMessage } from "../lib/errors";
import { formatCentsAsDollarsInput, formatCentsDisplay, parseDollarsToCents } from "../lib/money";

interface AccountFormState {
  name: string;
  type: AccountType;
  institution: string;
  balanceDollars: string;
  color: string;
  icon: string;
}

const EMPTY_FORM: AccountFormState = {
  name: "",
  type: "checking",
  institution: "",
  balanceDollars: "0.00",
  color: "#3B82F6",
  icon: "wallet",
};

function toFormState(account: Account): AccountFormState {
  return {
    name: account.name,
    type: account.type,
    institution: account.institution ?? "",
    balanceDollars: formatCentsAsDollarsInput(account.balance_cents),
    color: account.color,
    icon: account.icon,
  };
}

export function AccountsPage() {
  const { t } = useTranslation();
  const [includeArchived, setIncludeArchived] = useState(false);
  const accounts = useAccounts(includeArchived);
  const createAccount = useCreateAccountMutation();
  const updateAccount = useUpdateAccountMutation();
  const archiveAccount = useArchiveAccountMutation();

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<AccountFormState>(EMPTY_FORM);

  const activeMutation = editingId ? updateAccount : createAccount;

  function openCreateForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setIsFormOpen(true);
  }

  function openEditForm(account: Account) {
    setEditingId(account.id);
    setForm(toFormState(account));
    setIsFormOpen(true);
  }

  function closeForm() {
    setIsFormOpen(false);
    setEditingId(null);
    createAccount.reset();
    updateAccount.reset();
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const payload = {
      name: form.name,
      type: form.type,
      institution: form.institution || null,
      balance_cents: parseDollarsToCents(form.balanceDollars),
      color: form.color,
      icon: form.icon,
    };
    try {
      if (editingId) {
        await updateAccount.mutateAsync({ id: editingId, payload });
      } else {
        await createAccount.mutateAsync(payload);
      }
      closeForm();
    } catch {
      // surfaced via activeMutation.error below
    }
  }

  async function handleArchive(id: string) {
    await archiveAccount.mutateAsync(id);
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-semibold">{t("accounts.title")}</h2>
        <PrimaryButton type="button" className="w-auto px-4 py-2" onClick={openCreateForm}>
          {t("accounts.addButton")}
        </PrimaryButton>
      </div>

      {isFormOpen ? (
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 rounded-2xl border border-charcoal/10 bg-white/60 p-6 dark:border-linen/10 dark:bg-white/[0.03]"
        >
          <FormField
            label={t("accounts.nameLabel")}
            name="name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <SelectField
            label={t("accounts.typeLabel")}
            name="type"
            value={form.type}
            onChange={(e) => setForm({ ...form, type: e.target.value as AccountType })}
          >
            {ACCOUNT_TYPES.map((type) => (
              <option key={type} value={type}>
                {t(`accounts.types.${type}`)}
              </option>
            ))}
          </SelectField>
          <FormField
            label={t("accounts.institutionLabel")}
            name="institution"
            value={form.institution}
            onChange={(e) => setForm({ ...form, institution: e.target.value })}
          />
          <FormField
            label={t("accounts.balanceLabel")}
            name="balance"
            inputMode="decimal"
            value={form.balanceDollars}
            onChange={(e) => setForm({ ...form, balanceDollars: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-4">
            <FormField
              label={t("accounts.colorLabel")}
              name="color"
              type="color"
              value={form.color}
              onChange={(e) => setForm({ ...form, color: e.target.value })}
            />
            <FormField
              label={t("accounts.iconLabel")}
              name="icon"
              required
              value={form.icon}
              onChange={(e) => setForm({ ...form, icon: e.target.value })}
            />
          </div>
          <ErrorBanner message={errorMessage(activeMutation.error, t("common.genericError"))} />
          <div className="flex gap-3">
            <PrimaryButton type="submit" disabled={activeMutation.isPending} className="w-auto px-4">
              {editingId ? t("accounts.saveButton") : t("accounts.createButton")}
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
        {t("accounts.showArchived")}
      </label>

      <ul className="flex flex-col gap-3">
        {accounts.data?.map((account) => (
          <li
            key={account.id}
            className="flex items-center justify-between rounded-xl border border-charcoal/10 bg-white/60 px-4 py-3 dark:border-linen/10 dark:bg-white/[0.03]"
          >
            <div className="flex items-center gap-3">
              <span
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: account.color }}
                aria-hidden
              />
              <div>
                <p className="font-medium">
                  {account.name}
                  {account.archived ? (
                    <span className="ml-2 text-xs text-charcoal/50 dark:text-linen/50">
                      {t("accounts.archivedBadge")}
                    </span>
                  ) : null}
                </p>
                <p className="text-xs text-charcoal/60 dark:text-linen/60">
                  {t(`accounts.types.${account.type}`)}
                  {account.institution ? ` · ${account.institution}` : ""}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="font-medium">{formatCentsDisplay(account.balance_cents)}</span>
              <button
                type="button"
                onClick={() => openEditForm(account)}
                className="text-sm text-charcoal/70 underline-offset-2 hover:underline dark:text-linen/70"
              >
                {t("common.edit")}
              </button>
              {!account.archived ? (
                <button
                  type="button"
                  onClick={() => handleArchive(account.id)}
                  className="text-sm text-charcoal/70 underline-offset-2 hover:underline dark:text-linen/70"
                >
                  {t("common.archive")}
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
