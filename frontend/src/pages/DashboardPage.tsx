import { useTranslation } from "react-i18next";

import { useMe } from "../features/auth/hooks";
import { DebtBossesStrip } from "../features/dashboard/DebtBossesStrip";
import { HeroRow } from "../features/dashboard/HeroRow";
import { MonthSpendingDonut } from "../features/dashboard/MonthSpendingDonut";
import { QuestsStrip } from "../features/dashboard/QuestsStrip";
import { SinceYouWereHere } from "../features/dashboard/SinceYouWereHere";

// Each section fetches and renders independently (no shared waterfall) so
// one slow query doesn't block the rest of the glanceable dashboard --
// spec's "answers in 5 seconds" requirement.
export function DashboardPage() {
  const { t } = useTranslation();
  const me = useMe();

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      {me.data ? (
        <h2 className="font-display text-xl font-semibold">
          {t("dashboard.welcome", { name: me.data.display_name })}
        </h2>
      ) : null}
      <HeroRow />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SinceYouWereHere />
        <MonthSpendingDonut />
      </div>
      <DebtBossesStrip />
      <QuestsStrip />
    </div>
  );
}

export default DashboardPage;
