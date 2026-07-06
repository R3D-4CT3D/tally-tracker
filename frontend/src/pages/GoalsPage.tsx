import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Card } from "../components/Card";
import { GoalCompleteAnimation } from "../components/board/GoalCompleteAnimation";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { MoneyDisplay } from "../components/MoneyDisplay";
import { PrimaryButton } from "../components/PrimaryButton";
import { ProgressBar } from "../components/ProgressBar";
import { PropertyCard } from "../components/PropertyCard";
import { RowActionLink } from "../components/RowActionLink";
import { SecondaryButton } from "../components/SecondaryButton";
import { useReducedMotion } from "../design-system/useReducedMotion";
import {
  useCreateGoalMutation,
  useDeleteGoalMutation,
  useGoals,
  useRecordContributionMutation,
  useUpdateGoalMutation,
} from "../features/goals/hooks";
import type { Goal } from "../features/goals/types";
import { errorMessage } from "../lib/errors";
import { formatCentsAsDollarsInput, parseDollarsToCents } from "../lib/money";

interface GoalFormState {
  name: string;
  targetDollars: string;
  targetDate: string;
  icon: string;
  color: string;
}

const EMPTY_FORM: GoalFormState = {
  name: "",
  targetDollars: "0.00",
  targetDate: "",
  icon: "🐷",
  color: "#059669",
};

function toFormState(goal: Goal): GoalFormState {
  return {
    name: goal.name,
    targetDollars: formatCentsAsDollarsInput(goal.target_cents),
    targetDate: goal.target_date ?? "",
    icon: goal.icon,
    color: goal.color,
  };
}

function today(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

interface ContributionFormState {
  amountDollars: string;
  date: string;
}

const EMPTY_CONTRIBUTION_FORM: ContributionFormState = { amountDollars: "", date: today() };

export function GoalsPage() {
  const { t } = useTranslation();
  const prefersReducedMotion = useReducedMotion();
  const goals = useGoals();
  const createGoal = useCreateGoalMutation();
  const updateGoal = useUpdateGoalMutation();
  const deleteGoal = useDeleteGoalMutation();
  const recordContribution = useRecordContributionMutation();

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<GoalFormState>(EMPTY_FORM);

  const [contributingId, setContributingId] = useState<string | null>(null);
  const [contributionForm, setContributionForm] =
    useState<ContributionFormState>(EMPTY_CONTRIBUTION_FORM);
  const [completionCelebration, setCompletionCelebration] = useState<Goal | null>(null);

  const activeMutation = editingId ? updateGoal : createGoal;

  function openCreateForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setIsFormOpen(true);
  }

  function openEditForm(goal: Goal) {
    setEditingId(goal.id);
    setForm(toFormState(goal));
    setIsFormOpen(true);
  }

  function closeForm() {
    setIsFormOpen(false);
    setEditingId(null);
    createGoal.reset();
    updateGoal.reset();
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const payload = {
      name: form.name,
      target_cents: parseDollarsToCents(form.targetDollars),
      target_date: form.targetDate || null,
      icon: form.icon,
      color: form.color,
    };
    try {
      if (editingId) {
        await updateGoal.mutateAsync({ id: editingId, payload });
      } else {
        await createGoal.mutateAsync(payload);
      }
      closeForm();
    } catch {
      // surfaced via activeMutation.error below
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm(t("goals.confirmDelete"))) return;
    await deleteGoal.mutateAsync(id);
  }

  function openContributionForm(goalId: string) {
    setContributingId(goalId);
    setContributionForm(EMPTY_CONTRIBUTION_FORM);
    recordContribution.reset();
  }

  function closeContributionForm() {
    setContributingId(null);
    recordContribution.reset();
  }

  async function handleRecordContribution(event: FormEvent, goalId: string) {
    event.preventDefault();
    const amountCents = parseDollarsToCents(contributionForm.amountDollars);
    const goal = goals.data?.find((g) => g.id === goalId);
    // Computed client-side from the same math the backend applies
    // (current_cents += amount_cents) rather than waiting on the goals
    // query to refetch after invalidation.
    const willComplete =
      goal !== undefined &&
      goal.completed_at === null &&
      goal.current_cents + amountCents >= goal.target_cents;
    try {
      await recordContribution.mutateAsync({
        id: goalId,
        payload: {
          amount_cents: amountCents,
          date: contributionForm.date,
        },
      });
      closeContributionForm();
      if (willComplete && goal) {
        setCompletionCelebration(goal);
      }
    } catch {
      // surfaced via recordContribution.error below
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-semibold">{t("goals.title")}</h2>
        <PrimaryButton type="button" className="px-4 py-2" onClick={openCreateForm}>
          {t("goals.addButton")}
        </PrimaryButton>
      </div>

      {isFormOpen ? (
        <Card size="form">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <FormField
              label={t("goals.nameLabel")}
              name="name"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <FormField
              label={t("goals.targetLabel")}
              name="target"
              inputMode="decimal"
              required
              value={form.targetDollars}
              onChange={(e) => setForm({ ...form, targetDollars: e.target.value })}
            />
            <FormField
              label={t("goals.targetDateLabel")}
              name="target_date"
              type="date"
              value={form.targetDate}
              onChange={(e) => setForm({ ...form, targetDate: e.target.value })}
            />
            <div className="grid grid-cols-2 gap-4">
              <FormField
                label={t("goals.iconLabel")}
                name="icon"
                required
                value={form.icon}
                onChange={(e) => setForm({ ...form, icon: e.target.value })}
              />
              <FormField
                label={t("goals.colorLabel")}
                name="color"
                type="color"
                value={form.color}
                onChange={(e) => setForm({ ...form, color: e.target.value })}
              />
            </div>
            <ErrorBanner message={errorMessage(activeMutation.error, t("common.genericError"))} />
            <div className="flex gap-3">
              <PrimaryButton type="submit" disabled={activeMutation.isPending} className="px-4">
                {editingId ? t("goals.saveButton") : t("goals.createButton")}
              </PrimaryButton>
              <SecondaryButton onClick={closeForm}>{t("common.cancel")}</SecondaryButton>
            </div>
          </form>
        </Card>
      ) : null}

      <ul className="flex flex-col gap-3">
        {goals.data?.map((goal) => {
          const pct = goal.target_cents > 0 ? (goal.current_cents / goal.target_cents) * 100 : 0;
          return (
            <li key={goal.id}>
              <PropertyCard
                color={goal.color}
                icon={goal.icon}
                name={goal.name}
                owned={goal.completed_at !== null}
                ownedLabel={t("goals.completedBadge")}
                amount={
                  <span className="flex items-baseline gap-1 text-base">
                    <MoneyDisplay cents={goal.current_cents} /> /{" "}
                    <MoneyDisplay cents={goal.target_cents} />
                  </span>
                }
              >
                <ProgressBar
                  pct={pct}
                  milestones={[25, 50, 75]}
                  reduceMotion={prefersReducedMotion}
                />
                <div className="flex items-center gap-4">
                  <RowActionLink onClick={() => openContributionForm(goal.id)}>
                    {t("goals.logContributionButton")}
                  </RowActionLink>
                  <RowActionLink onClick={() => openEditForm(goal)}>
                    {t("common.edit")}
                  </RowActionLink>
                  <RowActionLink onClick={() => handleDelete(goal.id)}>
                    {t("common.delete")}
                  </RowActionLink>
                </div>

                {contributingId === goal.id ? (
                  <form
                    onSubmit={(e) => handleRecordContribution(e, goal.id)}
                    className="flex flex-col gap-3 rounded-lg border border-border/10 p-3"
                  >
                    <div className="grid grid-cols-2 gap-3">
                      <FormField
                        label={t("goals.contributionAmountLabel")}
                        name="contribution_amount"
                        inputMode="decimal"
                        required
                        placeholder="50.00"
                        value={contributionForm.amountDollars}
                        onChange={(e) =>
                          setContributionForm({ ...contributionForm, amountDollars: e.target.value })
                        }
                      />
                      <FormField
                        label={t("goals.contributionDateLabel")}
                        name="contribution_date"
                        type="date"
                        required
                        value={contributionForm.date}
                        onChange={(e) =>
                          setContributionForm({ ...contributionForm, date: e.target.value })
                        }
                      />
                    </div>
                    <ErrorBanner
                      message={errorMessage(recordContribution.error, t("common.genericError"))}
                    />
                    <div className="flex gap-3">
                      <PrimaryButton
                        type="submit"
                        disabled={recordContribution.isPending}
                        className="px-4"
                      >
                        {t("goals.submitContributionButton")}
                      </PrimaryButton>
                      <SecondaryButton onClick={closeContributionForm}>
                        {t("common.cancel")}
                      </SecondaryButton>
                    </div>
                  </form>
                ) : null}
              </PropertyCard>
            </li>
          );
        })}
      </ul>
      {goals.data?.length === 0 ? <EmptyState message={t("goals.empty")} /> : null}
      <GoalCompleteAnimation
        open={completionCelebration !== null}
        goalName={completionCelebration?.name ?? ""}
        goalIcon={completionCelebration?.icon ?? ""}
        goalColor={completionCelebration?.color ?? "#1B7A3E"}
        onDismiss={() => setCompletionCelebration(null)}
      />
    </div>
  );
}
