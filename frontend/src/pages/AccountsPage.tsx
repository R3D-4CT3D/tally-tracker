import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { MoneyDisplay } from "../components/MoneyDisplay";
import { PrimaryButton } from "../components/PrimaryButton";
import { RowActionLink } from "../components/RowActionLink";
import { SecondaryButton } from "../components/SecondaryButton";
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
import { formatCentsAsDollarsInput, parseDollarsToCents } from "../lib/money";

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
        <PrimaryButton type="button" className="px-4 py-2" onClick={openCreateForm}>
          {t("accounts.addButton")}
        </PrimaryButton>
      </div>

      {isFormOpen ? (
        <Card size="form" className="flex flex-col gap-4">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
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
              <PrimaryButton type="submit" disabled={activeMutation.isPending} className="px-4">
                {editingId ? t("accounts.saveButton") : t("accounts.createButton")}
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
        {t("accounts.showArchived")}
      </label>

      <ul className="flex flex-col gap-3">
        {accounts.data?.map((account) => (
          <li key={account.id}>
            <Card size="row" className="flex items-center justify-between">
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
                      <span className="ml-2 text-xs text-text-primary/50">
                        {t("accounts.archivedBadge")}
                      </span>
                    ) : null}
                  </p>
                  <p className="text-xs text-text-primary/60">
                    {t(`accounts.types.${account.type}`)}
                    {account.institution ? ` · ${account.institution}` : ""}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <MoneyDisplay cents={account.balance_cents} />
                <RowActionLink onClick={() => openEditForm(account)}>
                  {t("common.edit")}
                </RowActionLink>
                {!account.archived ? (
                  <RowActionLink onClick={() => handleArchive(account.id)}>
                    {t("common.archive")}
                  </RowActionLink>
                ) : null}
              </div>
            </Card>
          </li>
        ))}
      </ul>
      {accounts.data?.length === 0 ? (
        <EmptyState message={t("accounts.empty")} />
      ) : null}
    </div>
  );
}
