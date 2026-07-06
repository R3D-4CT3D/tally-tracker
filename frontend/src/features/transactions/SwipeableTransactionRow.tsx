import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";

import { Card } from "../../components/Card";
import { MoneyDisplay } from "../../components/MoneyDisplay";
import { RowActionLink } from "../../components/RowActionLink";
import { SecondaryButton } from "../../components/SecondaryButton";
import { useIsMobile } from "../../design-system/useIsMobile";
import { useReducedMotion } from "../../design-system/useReducedMotion";
import type { Category } from "../categories/types";
import type { Transaction } from "./types";

const SWIPE_THRESHOLD = 72;

interface SwipeableTransactionRowProps {
  transaction: Transaction;
  accountName: string;
  category: Category | undefined;
  categories: Category[];
  /** Desktop/idle-state row action -- shows its own native confirm dialog. */
  onDelete: (id: string) => void;
  /** Swipe-revealed inline confirm's "Confirm" button -- the inline UI
   * already *is* the confirmation, so this must delete directly rather
   * than stacking a second, native confirm() on top of it. */
  onConfirmedDelete: (id: string) => void;
  onSetCategory: (id: string, categoryId: string) => void;
}

// Wraps the existing desktop row (unchanged: Card + RowActionLink/Link)
// in a drag-to-reveal layer, active only on mobile (see useIsMobile) --
// desktop mouse users keep the plain buttons, never the drag gesture.
// Swipe left reveals "categorize" (an inline picker, not an immediate
// guess), swipe right reveals "delete" (an inline confirm, not a jarring
// native window.confirm() mid-gesture).
export function SwipeableTransactionRow({
  transaction,
  accountName,
  category,
  categories,
  onDelete,
  onConfirmedDelete,
  onSetCategory,
}: SwipeableTransactionRowProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const prefersReducedMotion = useReducedMotion();
  const [mode, setMode] = useState<"idle" | "categorize" | "confirmDelete">("idle");

  const rowContent = (
    <Card size="row" className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="w-24 shrink-0 text-xs text-text-primary/60">{transaction.date}</span>
        <div>
          <p className="font-medium">{transaction.description_display}</p>
          <p className="text-xs text-text-primary/60">
            {accountName}
            {category ? ` · ${category.icon} ${category.name}` : ` · ${t("transactions.uncategorizedOnly")}`}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <MoneyDisplay
          cents={transaction.amount_cents}
          className={
            transaction.amount_cents < 0
              ? "text-danger-600 dark:text-danger-400"
              : "text-success-600 dark:text-success-400"
          }
        />
        <RowActionLink onClick={() => onDelete(transaction.id)}>
          {t("common.delete")}
        </RowActionLink>
        <Link
          to={`/transactions/${transaction.id}/edit`}
          className="text-sm text-text-primary/70 underline-offset-2 hover:underline"
        >
          {t("common.edit")}
        </Link>
      </div>
    </Card>
  );

  if (!isMobile) return rowContent;

  if (mode === "confirmDelete") {
    return (
      <Card size="row" className="flex items-center justify-between gap-3 bg-danger-500/10">
        <p className="text-sm">{t("transactions.confirmDeleteInline")}</p>
        <div className="flex shrink-0 gap-2">
          <SecondaryButton
            className="min-h-9 px-3 py-1.5 text-xs"
            onClick={() => {
              onConfirmedDelete(transaction.id);
              setMode("idle");
            }}
          >
            {t("common.confirm")}
          </SecondaryButton>
          <SecondaryButton className="min-h-9 px-3 py-1.5 text-xs" onClick={() => setMode("idle")}>
            {t("common.cancel")}
          </SecondaryButton>
        </div>
      </Card>
    );
  }

  if (mode === "categorize") {
    return (
      <Card size="row" className="flex items-center gap-3 bg-green-500/10">
        <p className="shrink-0 text-sm">{t("transactions.swipeCategorizePrompt")}</p>
        <select
          autoFocus
          className="min-h-9 flex-1 rounded-lg border border-border/15 bg-surface-subtle px-2 text-sm"
          defaultValue=""
          onChange={(e) => {
            if (e.target.value) onSetCategory(transaction.id, e.target.value);
            setMode("idle");
          }}
          onBlur={() => setMode("idle")}
        >
          <option value="" disabled>
            {t("transactions.selectCategory")}
          </option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.icon} {c.name}
            </option>
          ))}
        </select>
      </Card>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-xl">
      <div className="absolute inset-0 flex items-center justify-between px-4 text-sm font-medium">
        <span className="text-danger-600 dark:text-danger-400">{t("common.delete")}</span>
        <span className="text-green-600 dark:text-green-400">{t("transactions.categorize")}</span>
      </div>
      <motion.div
        drag="x"
        dragConstraints={{ left: 0, right: 0 }}
        dragElastic={0.5}
        onDragEnd={(_event, info) => {
          if (info.offset.x <= -SWIPE_THRESHOLD) setMode("categorize");
          else if (info.offset.x >= SWIPE_THRESHOLD) setMode("confirmDelete");
        }}
        transition={prefersReducedMotion ? { duration: 0 } : undefined}
      >
        {rowContent}
      </motion.div>
    </div>
  );
}
