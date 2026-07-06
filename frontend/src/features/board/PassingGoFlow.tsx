import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Card } from "../../components/Card";
import { ErrorBanner } from "../../components/ErrorBanner";
import { FormField } from "../../components/FormField";
import { PrimaryButton } from "../../components/PrimaryButton";
import { SecondaryButton } from "../../components/SecondaryButton";
import { SelectField } from "../../components/SelectField";
import { PassingGoAnimation } from "../../components/board/PassingGoAnimation";
import { useAccounts } from "../accounts/hooks";
import { errorMessage } from "../../lib/errors";
import { parseDollarsToCents } from "../../lib/money";
import { useRecordTaxReturnMutation } from "./hooks";

type Stage = "animation" | "prompt" | "amount";

// Rendered whenever useBoard()'s year_end_pending is true: the passing-GO
// celebration, then "did you get a tax return this year?" (yes creates a
// real income transaction via the chosen account, no just resolves the
// board with amount_cents=0) -- either answer unblocks next year's board.
export function PassingGoFlow() {
  const { t } = useTranslation();
  const accounts = useAccounts();
  const recordTaxReturn = useRecordTaxReturnMutation();
  const [stage, setStage] = useState<Stage>("animation");
  const [accountId, setAccountId] = useState("");
  const [amountDollars, setAmountDollars] = useState("");

  async function handleDecline() {
    await recordTaxReturn.mutateAsync({ amount_cents: 0 });
  }

  async function handleSubmitAmount() {
    await recordTaxReturn.mutateAsync({
      account_id: accountId,
      amount_cents: parseDollarsToCents(amountDollars),
    });
  }

  if (stage === "animation") {
    return <PassingGoAnimation open onComplete={() => setStage("prompt")} />;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/70 p-4">
      <Card size="form" className="w-full max-w-sm">
        {stage === "prompt" ? (
          <div className="flex flex-col gap-4">
            <h3 className="font-display text-lg font-semibold">{t("board.taxReturnPromptTitle")}</h3>
            <p className="text-sm text-text-primary/70">{t("board.taxReturnPromptBody")}</p>
            <ErrorBanner
              message={errorMessage(recordTaxReturn.error, t("common.genericError"))}
            />
            <div className="flex gap-3">
              <PrimaryButton
                type="button"
                className="px-4"
                onClick={() => setStage("amount")}
                disabled={recordTaxReturn.isPending}
              >
                {t("board.taxReturnYes")}
              </PrimaryButton>
              <SecondaryButton onClick={handleDecline} disabled={recordTaxReturn.isPending}>
                {t("board.taxReturnNo")}
              </SecondaryButton>
            </div>
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void handleSubmitAmount();
            }}
            className="flex flex-col gap-4"
          >
            <h3 className="font-display text-lg font-semibold">{t("board.taxReturnAmountTitle")}</h3>
            <SelectField
              label={t("board.taxReturnAccountLabel")}
              name="account_id"
              required
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
            >
              <option value="" disabled>
                {t("transactions.selectAccount")}
              </option>
              {(accounts.data ?? []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </SelectField>
            <FormField
              label={t("board.taxReturnAmountLabel")}
              name="amount"
              inputMode="decimal"
              required
              placeholder="500.00"
              value={amountDollars}
              onChange={(e) => setAmountDollars(e.target.value)}
            />
            <ErrorBanner
              message={errorMessage(recordTaxReturn.error, t("common.genericError"))}
            />
            <div className="flex gap-3">
              <PrimaryButton type="submit" className="px-4" disabled={recordTaxReturn.isPending}>
                {t("common.confirm")}
              </PrimaryButton>
              <SecondaryButton onClick={() => setStage("prompt")} disabled={recordTaxReturn.isPending}>
                {t("common.back")}
              </SecondaryButton>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}
