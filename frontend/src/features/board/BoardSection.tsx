import { useState } from "react";
import { useTranslation } from "react-i18next";

import { BoardGrid } from "../../components/board/BoardGrid";
import { BoardTrack } from "../../components/board/BoardTrack";
import { ChanceCardToast } from "../../components/board/ChanceCardToast";
import { CommunityChestModal } from "../../components/board/CommunityChestModal";
import { Card } from "../../components/Card";
import { PrimaryButton } from "../../components/PrimaryButton";
import { useBoard } from "./hooks";
import { PassingGoFlow } from "./PassingGoFlow";

// Local date components, not toISOString() -- see TransactionFormPage's
// today() for why (UTC conversion rolls the date forward in the evening
// for anyone west of UTC).
function currentMonthFirstDay(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}-01`;
}

// Prominent dashboard section (not a bottom-nav tab -- that's capped at the
// 5 requested tabs): mobile gets the linear scrollable BoardTrack, desktop
// gets the full square BoardGrid. Both already show all 52 tiles, so
// neither needs a separate "expand" step -- what you see here already is
// the full board.
export function BoardSection() {
  const { t } = useTranslation();
  const board = useBoard();
  const [chestOpen, setChestOpen] = useState(false);

  if (!board.data) return null;

  if (board.data.year_end_pending) {
    return <PassingGoFlow />;
  }

  const currentTile = board.data.tiles.find((tile) => tile.is_current);
  const showChanceMessage =
    currentTile?.kind === "chance" && board.data.streak.current_weeks > 0;
  const showChestPrompt = currentTile?.kind === "chest";

  return (
    <Card size="form" className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <h3 className="font-display text-lg font-semibold">{t("board.title")}</h3>
        <span className="text-xs text-text-primary/60">
          {t("board.weekProgress", {
            current: board.data.current_week,
            total: board.data.board_size,
          })}
        </span>
      </div>
      {showChanceMessage ? (
        <ChanceCardToast
          currentWeek={board.data.current_week}
          currentStreakWeeks={board.data.streak.current_weeks}
        />
      ) : null}
      {showChestPrompt ? (
        <div className="flex items-center justify-between rounded-lg bg-cream-200 px-3 py-2 dark:bg-navy-700">
          <span className="text-sm text-navy-950 dark:text-cream-50">
            {t("board.chestPrompt")}
          </span>
          <PrimaryButton type="button" className="px-3 py-1.5 text-xs" onClick={() => setChestOpen(true)}>
            {t("board.chestOpenButton")}
          </PrimaryButton>
        </div>
      ) : null}
      <BoardTrack tiles={board.data.tiles} />
      <BoardGrid
        tiles={board.data.tiles}
        centerContent={
          <div className="flex flex-col items-center gap-3 text-center">
            <p className="font-display text-2xl font-bold tracking-wide text-green-600 dark:text-green-400">
              {t("app.title")}
            </p>
            <p className="text-sm text-text-primary/70">
              {t("board.weekProgress", {
                current: board.data.current_week,
                total: board.data.board_size,
              })}
            </p>
            <div className="flex gap-4 text-xs text-text-primary/60">
              <span>{t("board.currentStreak", { count: board.data.streak.current_weeks })}</span>
              <span>{t("board.bestStreak", { count: board.data.streak.best_weeks })}</span>
              <span>{t("board.freezesBanked", { count: board.data.streak.freezes_banked })}</span>
            </div>
          </div>
        }
      />
      {chestOpen ? (
        <CommunityChestModal month={currentMonthFirstDay()} onClose={() => setChestOpen(false)} />
      ) : null}
    </Card>
  );
}
