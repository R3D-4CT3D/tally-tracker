import { useTranslation } from "react-i18next";

import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { CategoryDonut } from "../../components/charts/CategoryDonut";
import type { DonutSlice } from "../../components/charts/CategoryDonut";
import { color } from "../../design-system/tokens";
import { useReducedMotion } from "../../design-system/useReducedMotion";
import { useCategories } from "../categories/hooks";
import { useMonthSpendingByCategory } from "./hooks";

export function MonthSpendingDonut() {
  const { t } = useTranslation();
  const prefersReducedMotion = useReducedMotion();
  const categories = useCategories();
  const spending = useMonthSpendingByCategory();

  const categoryById = new Map((categories.data ?? []).map((c) => [c.id, c]));
  const slices: DonutSlice[] = (spending.data ?? [])
    .filter((s) => s.cents > 0)
    .map((s) => {
      const category = s.categoryId ? categoryById.get(s.categoryId) : undefined;
      return {
        key: s.categoryId ?? "uncategorized",
        label: category ? `${category.icon} ${category.name}` : t("transactions.uncategorizedOnly"),
        cents: s.cents,
        color: category?.color ?? color.navy[400],
      };
    })
    .sort((a, b) => b.cents - a.cents);

  return (
    <Card size="form" className="flex flex-col gap-4">
      <h3 className="font-display text-lg font-semibold">{t("dashboard.monthSpendingTitle")}</h3>
      {slices.length === 0 ? (
        <EmptyState
          message={t("dashboard.noSpendingYet")}
          ctaLabel={t("dashboard.importCta")}
          ctaTo="/import"
        />
      ) : (
        <CategoryDonut slices={slices} reduceMotion={prefersReducedMotion} />
      )}
    </Card>
  );
}
