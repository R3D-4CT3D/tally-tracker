import { useTranslation } from "react-i18next";

import { Card } from "../../components/Card";
import { EmptyState } from "../../components/EmptyState";
import { MoneyDisplay } from "../../components/MoneyDisplay";
import { ProgressBar } from "../../components/ProgressBar";
import { useReducedMotion } from "../../design-system/useReducedMotion";
import { useGoalContributions, useGoals } from "../goals/hooks";
import type { Goal } from "../goals/types";
import { computeGoalProjection } from "./hooks";

function QuestCard({ goal, reduceMotion }: { goal: Goal; reduceMotion: boolean }) {
  const { t } = useTranslation();
  const contributions = useGoalContributions(goal.id);
  const pct = goal.target_cents > 0 ? (goal.current_cents / goal.target_cents) * 100 : 0;
  const projection = computeGoalProjection(
    contributions.data ?? [],
    goal.target_cents,
    goal.current_cents,
  );

  return (
    <li className="flex w-64 shrink-0 snap-start flex-col gap-2 rounded-xl border border-border/10 bg-surface-subtle p-3 md:w-auto md:shrink md:border-0 md:bg-transparent md:p-0">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span aria-hidden>{goal.icon}</span>
          <p className="font-medium">{goal.name}</p>
        </div>
        <span className="text-sm">
          <MoneyDisplay cents={goal.current_cents} /> / <MoneyDisplay cents={goal.target_cents} />
        </span>
      </div>
      <ProgressBar pct={pct} milestones={[25, 50, 75]} reduceMotion={reduceMotion} />
      <p className="text-xs text-text-primary/60">
        {projection.projectedDate
          ? t("dashboard.projectedCompletion", { date: projection.projectedDate })
          : t("dashboard.noProjectionYet")}
      </p>
    </li>
  );
}

export function QuestsStrip() {
  const { t } = useTranslation();
  const prefersReducedMotion = useReducedMotion();
  const goals = useGoals();
  const activeGoals = (goals.data ?? []).filter((g) => g.completed_at === null);

  return (
    <Card size="form" className="flex flex-col gap-4">
      <h3 className="font-display text-lg font-semibold">{t("dashboard.questsTitle")}</h3>
      {activeGoals.length === 0 ? (
        <EmptyState message={t("dashboard.noGoals")} ctaLabel={t("dashboard.addGoalCta")} ctaTo="/goals" />
      ) : (
        <ul className="flex snap-x snap-mandatory gap-4 overflow-x-auto pb-1 md:flex-col md:overflow-visible md:pb-0">
          {activeGoals.map((goal) => (
            <QuestCard key={goal.id} goal={goal} reduceMotion={prefersReducedMotion} />
          ))}
        </ul>
      )}
    </Card>
  );
}
