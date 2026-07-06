import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Card } from "../Card";
import { ErrorBanner } from "../ErrorBanner";
import { PrimaryButton } from "../PrimaryButton";
import { SecondaryButton } from "../SecondaryButton";
import { useReducedMotion } from "../../design-system/useReducedMotion";
import { useCompleteMonthlyCloseMutation, useMonthlyClosePreview } from "../../features/monthlyClose/hooks";
import { errorMessage } from "../../lib/errors";
import { formatCentsDisplay } from "../../lib/money";

interface CommunityChestModalProps {
  /** First-of-month date string, e.g. "2026-03-01". */
  month: string;
  onClose: () => void;
}

const STEP_COUNT = 6;

function deltaLabel(current: number, prior: number | null): string | null {
  if (prior === null) return null;
  const diff = current - prior;
  if (diff === 0) return null;
  const sign = diff > 0 ? "+" : "";
  return `${sign}${formatCentsDisplay(diff)} vs last month`;
}

// The Community Chest ceremony: a 6-step guided recap (resolve
// uncategorized, income/spend, debt damage, quest progress, net worth,
// grade + highlight) presented as a sequence of drawn cards, wrapping
// app/services/monthly_close.py's brand-new backend logic -- this flow
// never existed in any prior milestone.
export function CommunityChestModal({ month, onClose }: CommunityChestModalProps) {
  const { t } = useTranslation();
  const prefersReducedMotion = useReducedMotion();
  const preview = useMonthlyClosePreview(month);
  const completeClose = useCompleteMonthlyCloseMutation();
  const [step, setStep] = useState(0);
  const [done, setDone] = useState(false);

  async function handleComplete() {
    try {
      await completeClose.mutateAsync(month);
      setDone(true);
    } catch {
      // surfaced via completeClose.error below
    }
  }

  const snapshot = preview.data;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/70 p-4">
      <Card size="form" className="w-full max-w-lg">
        {!snapshot ? (
          <p className="text-sm text-text-primary/60">{t("common.loading")}</p>
        ) : done ? (
          <div className="flex flex-col items-center gap-4 py-4 text-center">
            <p className="font-display text-3xl font-bold text-green-600 dark:text-green-400">
              {snapshot.grade}
            </p>
            <p className="text-sm text-text-primary/70">{snapshot.highlight}</p>
            <PrimaryButton type="button" className="px-6" onClick={onClose}>
              {t("monthlyClose.done")}
            </PrimaryButton>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="font-display text-lg font-semibold">{t("monthlyClose.title")}</h3>
              <span className="text-xs text-text-primary/60">
                {t("monthlyClose.stepProgress", { current: step + 1, total: STEP_COUNT })}
              </span>
            </div>

            <AnimatePresence mode="wait">
              <motion.div
                key={step}
                initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: prefersReducedMotion ? 0 : -8 }}
                transition={{ duration: prefersReducedMotion ? 0 : 0.2 }}
                className="min-h-[120px] rounded-lg border border-border/10 bg-surface-subtle p-4"
              >
                {step === 0 ? (
                  <div className="flex flex-col gap-2">
                    <h4 className="font-medium">{t("monthlyClose.step1Title")}</h4>
                    {snapshot.uncategorized_count > 0 ? (
                      <>
                        <p className="text-sm text-text-primary/70">
                          {t("monthlyClose.uncategorizedCount", {
                            count: snapshot.uncategorized_count,
                          })}
                        </p>
                        <Link
                          to="/transactions?uncategorized=true"
                          className="text-sm text-green-600 underline-offset-2 hover:underline dark:text-green-400"
                        >
                          {t("monthlyClose.resolveNow")}
                        </Link>
                      </>
                    ) : (
                      <p className="text-sm text-text-primary/70">{t("monthlyClose.allCategorized")}</p>
                    )}
                  </div>
                ) : null}

                {step === 1 ? (
                  <div className="flex flex-col gap-2">
                    <h4 className="font-medium">{t("monthlyClose.step2Title")}</h4>
                    <p className="text-sm">
                      {t("monthlyClose.income")}: {formatCentsDisplay(snapshot.income_cents)}
                    </p>
                    <p className="text-sm">
                      {t("monthlyClose.spend")}: {formatCentsDisplay(snapshot.spend_cents)}
                    </p>
                    {deltaLabel(snapshot.spend_cents, snapshot.prior_spend_cents) ? (
                      <p className="text-xs text-text-primary/60">
                        {deltaLabel(snapshot.spend_cents, snapshot.prior_spend_cents)}
                      </p>
                    ) : null}
                  </div>
                ) : null}

                {step === 2 ? (
                  <div className="flex flex-col gap-2">
                    <h4 className="font-medium">{t("monthlyClose.step3Title")}</h4>
                    <p className="text-sm">
                      {t("monthlyClose.debtPayments")}:{" "}
                      {formatCentsDisplay(snapshot.debt_payments_cents)}
                    </p>
                    <p className="text-sm">
                      {t("monthlyClose.totalDebt")}: {formatCentsDisplay(snapshot.total_debt_cents)}
                    </p>
                    {deltaLabel(snapshot.total_debt_cents, snapshot.start_of_month_debt_cents) ? (
                      <p className="text-xs text-text-primary/60">
                        {deltaLabel(snapshot.total_debt_cents, snapshot.start_of_month_debt_cents)}
                      </p>
                    ) : null}
                  </div>
                ) : null}

                {step === 3 ? (
                  <div className="flex flex-col gap-2">
                    <h4 className="font-medium">{t("monthlyClose.step4Title")}</h4>
                    <p className="text-sm">
                      {t("monthlyClose.goalContributions")}:{" "}
                      {formatCentsDisplay(snapshot.goal_contributions_cents)}
                    </p>
                    {snapshot.goals_completed.length > 0 ? (
                      <p className="text-sm text-green-700 dark:text-green-400">
                        {t("monthlyClose.goalsCompleted", {
                          names: snapshot.goals_completed.join(", "),
                        })}
                      </p>
                    ) : null}
                  </div>
                ) : null}

                {step === 4 ? (
                  <div className="flex flex-col gap-2">
                    <h4 className="font-medium">{t("monthlyClose.step5Title")}</h4>
                    {snapshot.net_worth_cents !== null ? (
                      <>
                        <p className="text-sm">
                          {t("monthlyClose.netWorth")}: {formatCentsDisplay(snapshot.net_worth_cents)}
                        </p>
                        {deltaLabel(snapshot.net_worth_cents, snapshot.prior_net_worth_cents) ? (
                          <p className="text-xs text-text-primary/60">
                            {deltaLabel(snapshot.net_worth_cents, snapshot.prior_net_worth_cents)}
                          </p>
                        ) : null}
                      </>
                    ) : (
                      <p className="text-sm text-text-primary/60">{t("monthlyClose.noSnapshotYet")}</p>
                    )}
                  </div>
                ) : null}

                {step === 5 ? (
                  <div className="flex flex-col items-center gap-2 text-center">
                    <h4 className="font-medium">{t("monthlyClose.step6Title")}</h4>
                    <p className="font-display text-4xl font-bold text-green-600 dark:text-green-400">
                      {snapshot.grade}
                    </p>
                    <p className="text-sm text-text-primary/70">{snapshot.highlight}</p>
                  </div>
                ) : null}
              </motion.div>
            </AnimatePresence>

            <ErrorBanner message={errorMessage(completeClose.error, t("common.genericError"))} />

            <div className="flex justify-between gap-3">
              <SecondaryButton onClick={step === 0 ? onClose : () => setStep((s) => s - 1)}>
                {step === 0 ? t("common.cancel") : t("common.back")}
              </SecondaryButton>
              {step < STEP_COUNT - 1 ? (
                <PrimaryButton type="button" className="px-4" onClick={() => setStep((s) => s + 1)}>
                  {t("common.next")}
                </PrimaryButton>
              ) : (
                <PrimaryButton
                  type="button"
                  className="px-4"
                  disabled={completeClose.isPending}
                  onClick={handleComplete}
                >
                  {t("monthlyClose.completeButton")}
                </PrimaryButton>
              )}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
