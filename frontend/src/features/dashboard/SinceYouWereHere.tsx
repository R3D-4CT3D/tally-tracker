import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Card } from "../../components/Card";
import { useMe } from "../auth/hooks";
import { useBills } from "../bills/hooks";
import { useTransactionCount, useUncategorizedCount } from "../transactions/hooks";
import { daysFromToday, today } from "./hooks";

export function SinceYouWereHere() {
  const { t } = useTranslation();
  const me = useMe();
  const bills = useBills();
  const uncategorized = useUncategorizedCount();

  // last_login_at is the *previous* login, baked into the session at login
  // time (see backend app/services/auth.py's record_login) -- null means
  // this is the user's first-ever real login, so there's nothing "since"
  // to report yet rather than dumping the household's entire history.
  const sinceIso = me.data?.last_login_at ? new Date(me.data.last_login_at).toISOString() : null;
  const newTransactions = useTransactionCount(
    { created_after: sinceIso ?? undefined },
    sinceIso !== null,
  );

  const upcomingBills = (bills.data ?? []).filter(
    (bill) => !bill.archived && bill.next_due_date >= today() && bill.next_due_date <= daysFromToday(14),
  );

  const newTransactionsCount = sinceIso ? (newTransactions.data?.count ?? 0) : 0;
  const uncategorizedCount = uncategorized.data?.count ?? 0;
  const nothingNew = newTransactionsCount === 0 && upcomingBills.length === 0 && uncategorizedCount === 0;

  return (
    <Card size="form" className="flex flex-col gap-3">
      <h3 className="font-display text-lg font-semibold">{t("dashboard.sinceYouWereHere")}</h3>
      {nothingNew ? (
        <p className="text-sm text-text-primary/60">{t("dashboard.allCaughtUp")}</p>
      ) : (
        <ul className="flex flex-col gap-2 text-sm">
          {newTransactionsCount > 0 ? (
            <li>
              <Link to="/transactions" className="underline-offset-2 hover:underline">
                {t("dashboard.newTransactionsCount", { count: newTransactionsCount })}
              </Link>
            </li>
          ) : null}
          {upcomingBills.length > 0 ? (
            <li>
              <Link to="/bills" className="underline-offset-2 hover:underline">
                {t("dashboard.upcomingBillsCount", { count: upcomingBills.length })}
              </Link>
            </li>
          ) : null}
          {uncategorizedCount > 0 ? (
            <li>
              <Link to="/transactions?uncategorized=true" className="underline-offset-2 hover:underline">
                {t("dashboard.uncategorizedCount", { count: uncategorizedCount })}
              </Link>
            </li>
          ) : null}
        </ul>
      )}
    </Card>
  );
}
