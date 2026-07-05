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
    <li className="flex flex-col gap-2">
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
        <ul className="flex flex-col gap-4">
          {activeGoals.map((goal) => (
            <QuestCard key={goal.id} goal={goal} reduceMotion={prefersReducedMotion} />
          ))}
        </ul>
      )}
    </Card>
  );
}
