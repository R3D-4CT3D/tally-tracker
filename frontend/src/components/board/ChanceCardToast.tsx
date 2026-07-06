import { useTranslation } from "react-i18next";

const MESSAGE_COUNT = 4;

interface ChanceCardToastProps {
  currentWeek: number;
  currentStreakWeeks: number;
}

// Flavor-only inline banner for landing on a Chance tile with an active
// streak -- no real $ credited, just a positive nudge (per
// docs/product-principles.md's "no shame mechanics" stance, the reverse
// also holds: no fake rewards). A stable-per-week (not per-render) message
// pick keeps it from flickering between options on re-fetch.
export function ChanceCardToast({ currentWeek, currentStreakWeeks }: ChanceCardToastProps) {
  const { t } = useTranslation();
  const messageKey = `board.chanceMessage${(currentWeek % MESSAGE_COUNT) + 1}`;

  return (
    <p className="rounded-lg bg-green-100 px-3 py-2 text-sm text-green-800 dark:bg-green-900 dark:text-green-100">
      {t(messageKey, { count: currentStreakWeeks })}
    </p>
  );
}
