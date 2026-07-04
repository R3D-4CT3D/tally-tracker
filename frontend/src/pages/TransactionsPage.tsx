import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { useAccounts } from "../features/accounts/hooks";
import { useCategories } from "../features/categories/hooks";
import { useDeleteTransactionMutation, useTransactions } from "../features/transactions/hooks";
import type { TransactionFilters } from "../features/transactions/types";
import { formatCentsDisplay } from "../lib/money";

const EMPTY_FILTERS: TransactionFilters = {};

export function TransactionsPage() {
  const { t } = useTranslation();
  const accounts = useAccounts();
  const categories = useCategories();
  const deleteTransaction = useDeleteTransactionMutation();

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

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-semibold">{t("transactions.title")}</h2>
        <Link
          to="/transactions/new"
          className="rounded-lg bg-ember px-4 py-2 text-sm font-medium text-charcoal transition-colors hover:bg-ember/90"
        >
          {t("transactions.addButton")}
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-4 rounded-2xl border border-charcoal/10 bg-white/60 p-4 dark:border-linen/10 dark:bg-white/[0.03] sm:grid-cols-3">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-charcoal/80 dark:text-linen/80">
            {t("transactions.dateFromLabel")}
          </label>
          <input
            type="date"
            value={filters.date_from ?? ""}
            onChange={(e) => updateFilters({ date_from: e.target.value || undefined })}
            className="rounded-lg border border-charcoal/15 bg-white/50 px-3 py-2 text-sm dark:border-linen/15 dark:bg-black/20 dark:text-linen"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-charcoal/80 dark:text-linen/80">
            {t("transactions.dateToLabel")}
          </label>
          <input
            type="date"
            value={filters.date_to ?? ""}
            onChange={(e) => updateFilters({ date_to: e.target.value || undefined })}
            className="rounded-lg border border-charcoal/15 bg-white/50 px-3 py-2 text-sm dark:border-linen/15 dark:bg-black/20 dark:text-linen"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-charcoal/80 dark:text-linen/80">
            {t("transactions.accountLabel")}
          </label>
          <select
            value={filters.account_id ?? ""}
            onChange={(e) => updateFilters({ account_id: e.target.value || undefined })}
            className="rounded-lg border border-charcoal/15 bg-white/50 px-3 py-2 text-sm dark:border-linen/15 dark:bg-black/20 dark:text-linen"
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
          <label className="text-sm font-medium text-charcoal/80 dark:text-linen/80">
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
            className="rounded-lg border border-charcoal/15 bg-white/50 px-3 py-2 text-sm dark:border-linen/15 dark:bg-black/20 dark:text-linen"
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
          <label className="text-sm font-medium text-charcoal/80 dark:text-linen/80">
            {t("transactions.searchLabel")}
          </label>
          <input
            type="search"
            value={filters.search ?? ""}
            onChange={(e) => updateFilters({ search: e.target.value || undefined })}
            placeholder={t("transactions.searchPlaceholder")}
            className="rounded-lg border border-charcoal/15 bg-white/50 px-3 py-2 text-sm dark:border-linen/15 dark:bg-black/20 dark:text-linen"
          />
        </div>
      </div>

      <ul className="flex flex-col gap-2">
        {transactions.data?.items.map((transaction) => {
          const category = transaction.category_id
            ? categoryById.get(transaction.category_id)
            : undefined;
          return (
            <li
              key={transaction.id}
              className="flex items-center justify-between rounded-xl border border-charcoal/10 bg-white/60 px-4 py-3 dark:border-linen/10 dark:bg-white/[0.03]"
            >
              <div className="flex items-center gap-3">
                <span className="w-24 shrink-0 text-xs text-charcoal/60 dark:text-linen/60">
                  {transaction.date}
                </span>
                <div>
                  <p className="font-medium">{transaction.description_display}</p>
                  <p className="text-xs text-charcoal/60 dark:text-linen/60">
                    {accountNameById.get(transaction.account_id) ??
                      t("transactions.unknownAccount")}
                    {category
                      ? ` · ${category.icon} ${category.name}`
                      : ` · ${t("transactions.uncategorizedOnly")}`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span
                  className={`font-medium ${
                    transaction.amount_cents < 0
                      ? "text-red-600 dark:text-red-400"
                      : "text-green-600 dark:text-green-400"
                  }`}
                >
                  {formatCentsDisplay(transaction.amount_cents)}
                </span>
                <Link
                  to={`/transactions/${transaction.id}/edit`}
                  className="text-sm text-charcoal/70 underline-offset-2 hover:underline dark:text-linen/70"
                >
                  {t("common.edit")}
                </Link>
                <button
                  type="button"
                  onClick={() => handleDelete(transaction.id)}
                  className="text-sm text-charcoal/70 underline-offset-2 hover:underline dark:text-linen/70"
                >
                  {t("common.delete")}
                </button>
              </div>
            </li>
          );
        })}
        {transactions.data?.items.length === 0 ? (
          <p className="py-8 text-center text-sm text-charcoal/60 dark:text-linen/60">
            {t("transactions.empty")}
          </p>
        ) : null}
      </ul>

      <div className="flex justify-between">
        <button
          type="button"
          onClick={handlePreviousPage}
          disabled={cursorStack.length === 0}
          className="rounded-lg border border-charcoal/20 px-4 py-2 text-sm font-medium disabled:opacity-40 dark:border-linen/20"
        >
          {t("transactions.previousPage")}
        </button>
        <button
          type="button"
          onClick={handleNextPage}
          disabled={!transactions.data?.next_cursor}
          className="rounded-lg border border-charcoal/20 px-4 py-2 text-sm font-medium disabled:opacity-40 dark:border-linen/20"
        >
          {t("transactions.nextPage")}
        </button>
      </div>
    </div>
  );
}
