import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { FIELD_CHROME_CLASSNAME } from "../components/fieldChrome";
import { PrimaryButton } from "../components/PrimaryButton";
import { SecondaryButton } from "../components/SecondaryButton";
import { useAccounts } from "../features/accounts/hooks";
import { useCategories } from "../features/categories/hooks";
import { SwipeableTransactionRow } from "../features/transactions/SwipeableTransactionRow";
import {
  useDeleteTransactionMutation,
  useTransactions,
  useUpdateTransactionMutation,
} from "../features/transactions/hooks";
import type { TransactionFilters } from "../features/transactions/types";

const EMPTY_FILTERS: TransactionFilters = {};

export function TransactionsPage() {
  const { t } = useTranslation();
  const accounts = useAccounts();
  const categories = useCategories();
  const deleteTransaction = useDeleteTransactionMutation();
  const updateTransaction = useUpdateTransactionMutation();

  const [filters, setFilters] = useState<TransactionFilters>(EMPTY_FILTERS);
  const [cursorStack, setCursorStack] = useState<string[]>([]);
  const [cursor, setCursor] = useState<string | undefined>(undefined);

  const transactions = useTransactions({ ...filters, cursor, limit: 25 });

  const accountNameById = new Map((accounts.data ?? []).map((a) => [a.id, a.name]));
  const categoryById = new Map((categories.data ?? []).map((c) => [c.id, c]));

  function updateFilters(patch: Partial<TransactionFilters>) {
    setFilters({ ...filters, ...patch });
    setCursorStack([]);
    setCursor(undefined);
  }

  function handleNextPage() {
    if (!transactions.data?.next_cursor) return;
    setCursorStack([...cursorStack, cursor ?? ""]);
    setCursor(transactions.data.next_cursor);
  }

  function handlePreviousPage() {
    const stack = [...cursorStack];
    const previous = stack.pop();
    setCursorStack(stack);
    setCursor(previous || undefined);
  }

  async function handleDelete(id: string) {
    if (!window.confirm(t("transactions.confirmDelete"))) return;
    await deleteTransaction.mutateAsync(id);
  }

  async function handleConfirmedDelete(id: string) {
    await deleteTransaction.mutateAsync(id);
  }

  async function handleSetCategory(id: string, categoryId: string) {
    await updateTransaction.mutateAsync({ id, payload: { category_id: categoryId } });
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-semibold">{t("transactions.title")}</h2>
        <Link to="/transactions/new">
          <PrimaryButton type="button" className="px-4 py-2">
            {t("transactions.addButton")}
          </PrimaryButton>
        </Link>
      </div>

      <Card size="form" className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-text-primary/80">
            {t("transactions.dateFromLabel")}
          </label>
          <input
            type="date"
            value={filters.date_from ?? ""}
            onChange={(e) => updateFilters({ date_from: e.target.value || undefined })}
            className={FIELD_CHROME_CLASSNAME}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-text-primary/80">
            {t("transactions.dateToLabel")}
          </label>
          <input
            type="date"
            value={filters.date_to ?? ""}
            onChange={(e) => updateFilters({ date_to: e.target.value || undefined })}
            className={FIELD_CHROME_CLASSNAME}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-text-primary/80">
            {t("transactions.accountLabel")}
          </label>
          <select
            value={filters.account_id ?? ""}
            onChange={(e) => updateFilters({ account_id: e.target.value || undefined })}
            className={FIELD_CHROME_CLASSNAME}
          >
            <option value="">{t("transactions.allAccounts")}</option>
            {(accounts.data ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-text-primary/80">
            {t("transactions.categoryLabel")}
          </label>
          <select
            value={filters.uncategorized ? "__uncategorized__" : (filters.category_id ?? "")}
            onChange={(e) => {
              const value = e.target.value;
              if (value === "__uncategorized__") {
                updateFilters({ uncategorized: true, category_id: undefined });
              } else {
                updateFilters({ uncategorized: false, category_id: value || undefined });
              }
            }}
            className={FIELD_CHROME_CLASSNAME}
          >
            <option value="">{t("transactions.allCategories")}</option>
            <option value="__uncategorized__">{t("transactions.uncategorizedOnly")}</option>
            {(categories.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <label className="text-sm font-medium text-text-primary/80">
            {t("transactions.searchLabel")}
          </label>
          <input
            type="search"
            value={filters.search ?? ""}
            onChange={(e) => updateFilters({ search: e.target.value || undefined })}
            placeholder={t("transactions.searchPlaceholder")}
            className={FIELD_CHROME_CLASSNAME}
          />
        </div>
      </Card>

      <ul className="flex flex-col gap-2">
        {transactions.data?.items.map((transaction) => {
          const category = transaction.category_id
            ? categoryById.get(transaction.category_id)
            : undefined;
          return (
            <li key={transaction.id}>
              <SwipeableTransactionRow
                transaction={transaction}
                accountName={
                  accountNameById.get(transaction.account_id) ?? t("transactions.unknownAccount")
                }
                category={category}
                categories={categories.data ?? []}
                onDelete={handleDelete}
                onConfirmedDelete={handleConfirmedDelete}
                onSetCategory={handleSetCategory}
              />
            </li>
          );
        })}
      </ul>
      {transactions.data?.items.length === 0 ? (
        <EmptyState message={t("transactions.empty")} />
      ) : null}

      <div className="flex justify-between">
        <SecondaryButton onClick={handlePreviousPage} disabled={cursorStack.length === 0}>
          {t("transactions.previousPage")}
        </SecondaryButton>
        <SecondaryButton onClick={handleNextPage} disabled={!transactions.data?.next_cursor}>
          {t("transactions.nextPage")}
        </SecondaryButton>
      </div>
    </div>
  );
}
