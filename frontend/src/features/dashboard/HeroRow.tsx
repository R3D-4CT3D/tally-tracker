import { useTranslation } from "react-i18next";

import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { MoneyDisplay } from "../../components/MoneyDisplay";
import { Sparkline } from "../../components/charts/Sparkline";
import type { SparklinePoint } from "../../components/charts/Sparkline";
import { color } from "../../design-system/tokens";
import { useReducedMotion } from "../../design-system/useReducedMotion";
import { useBalanceSnapshots } from "../balanceSnapshots/hooks";
import { daysFromToday, today } from "./hooks";

function toPoints(
  snapshots: { date: string; cash_cents: number; debt_cents: number }[],
  pick: "cash" | "debt" | "net",
): SparklinePoint[] {
  // list_balance_snapshots orders newest-first; a left-to-right sparkline
  // needs chronological (ascending) order.
  return [...snapshots]
    .reverse()
    .map((s) => ({
      date: s.date,
      value: pick === "cash" ? s.cash_cents : pick === "debt" ? s.debt_cents : s.cash_cents - s.debt_cents,
    }));
}

export function HeroRow() {
  const { t } = useTranslation();
  const prefersReducedMotion = useReducedMotion();
  const snapshots = useBalanceSnapshots(daysFromToday(-90), today());

  const data = snapshots.data ?? [];
  const hasEnoughData = data.length >= 2;
  const latest = data[0];

  const metrics = [
    {
      key: "cash",
      label: t("dashboard.cashLabel"),
      cents: latest?.cash_cents ?? 0,
      points: toPoints(data, "cash"),
      lineColor: color.success[500],
    },
    {
      key: "debt",
      label: t("dashboard.debtLabel"),
      cents: latest?.debt_cents ?? 0,
      points: toPoints(data, "debt"),
      lineColor: color.danger[500],
    },
    {
      key: "net",
      label: t("dashboard.netLabel"),
      cents: (latest?.cash_cents ?? 0) - (latest?.debt_cents ?? 0),
      points: toPoints(data, "net"),
      lineColor: color.ember[500],
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {metrics.map((metric) => (
        <Card key={metric.key} size="form" className="flex flex-col gap-2">
          <p className="text-sm font-medium text-text-primary/70">{metric.label}</p>
          {hasEnoughData ? (
            <>
              <MoneyDisplay cents={metric.cents} variant="hero" />
              <Sparkline
                data={metric.points}
                color={metric.lineColor}
                reduceMotion={prefersReducedMotion}
              />
            </>
          ) : (
            <EmptyState message={t("dashboard.noSnapshotsYet")} />
          )}
        </Card>
      ))}
    </div>
  );
}
