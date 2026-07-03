import { useTranslation } from "react-i18next";

import { useMe } from "../features/auth/hooks";

/** Placeholder only — real dashboard content (hero metrics, debt bosses,
 * quests, streaks) is M5/M6 scope. This exists to prove the authenticated
 * route tree and shell work end to end. */
export function DashboardPage() {
  const { t } = useTranslation();
  const me = useMe();

  return (
    <div className="mx-auto max-w-2xl rounded-2xl border border-charcoal/10 bg-white/60 p-8 dark:border-linen/10 dark:bg-white/[0.03]">
      <h2 className="font-display text-xl font-semibold">
        {me.data ? t("dashboard.welcome", { name: me.data.display_name }) : t("dashboard.title")}
      </h2>
      <p className="mt-2 text-sm text-charcoal/60 dark:text-linen/60">{t("dashboard.comingSoon")}</p>
    </div>
  );
}
