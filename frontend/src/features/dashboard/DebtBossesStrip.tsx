import { useTranslation } from "react-i18next";

import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { MoneyDisplay } from "../../components/MoneyDisplay";
import { ProgressBar } from "../../components/ProgressBar";
import { useReducedMotion } from "../../design-system/useReducedMotion";
import { useDebts } from "../debts/hooks";
import { formatBpsAsPercentDisplay } from "../../lib/money";
import { nextOccurrenceOfDay } from "./hooks";

export function DebtBossesStrip() {
  const { t } = useTranslation();
  const prefersReducedMotion = useReducedMotion();
  const debts = useDebts();

  const activeDebts = (debts.data ?? []).filter((d) => !d.archived && d.paid_off_at === null);

  return (
    <Card size="form" className="flex flex-col gap-4">
      <h3 className="font-display text-lg font-semibold">{t("dashboard.debtBossesTitle")}</h3>
      {activeDebts.length === 0 ? (
        <EmptyState message={t("dashboard.noDebts")} ctaLabel={t("dashboard.addDebtCta")} ctaTo="/debts" />
      ) : (
        <ul className="flex flex-col gap-4">
          {activeDebts.map((debt) => {
            const pct =
              debt.original_balance_cents > 0
                ? (debt.current_balance_cents / debt.original_balance_cents) * 100
                : 0;
            return (
              <li key={debt.id} className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{debt.name}</p>
                    <p className="text-xs text-text-primary/60">
                      {formatBpsAsPercentDisplay(debt.apr_bps)} {t("debts.aprSuffix")} ·{" "}
                      {t("dashboard.nextDueValue", { date: nextOccurrenceOfDay(debt.due_day) })}
                    </p>
                  </div>
                  <MoneyDisplay cents={debt.current_balance_cents} />
                </div>
                <ProgressBar pct={pct} variant="boss" reduceMotion={prefersReducedMotion} />
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
