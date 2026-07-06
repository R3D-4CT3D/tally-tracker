import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";

import { useReducedMotion } from "../../design-system/useReducedMotion";
import { PrimaryButton } from "../PrimaryButton";

interface GoalCompleteAnimationProps {
  open: boolean;
  goalName: string;
  goalIcon: string;
  goalColor: string;
  onDismiss: () => void;
}

// Full-screen celebration for a goal's property tile flipping to "owned"
// (Goal.completed_at newly set). Mirrors DebtPayoffAnimation's structure
// (user-dismissed, reduced-motion-aware) but themed with the goal's own
// icon/color, matching its PropertyCard styling elsewhere in the app.
export function GoalCompleteAnimation({
  open,
  goalName,
  goalIcon,
  goalColor,
  onDismiss,
}: GoalCompleteAnimationProps) {
  const { t } = useTranslation();
  const prefersReducedMotion = useReducedMotion();

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/90 p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: prefersReducedMotion ? 0 : 0.3 }}
          role="dialog"
          aria-label={t("board.goalCompleteTitle")}
        >
          <div className="flex flex-col items-center gap-6 text-center">
            <motion.div
              className="flex h-24 w-24 items-center justify-center rounded-2xl text-5xl shadow-lg"
              style={{ backgroundColor: goalColor }}
              initial={{ scale: prefersReducedMotion ? 1 : 0.4 }}
              animate={{ scale: [1, 1.15, 1] }}
              transition={{ duration: prefersReducedMotion ? 0 : 0.6, ease: "easeOut" }}
              aria-hidden
            >
              {goalIcon}
            </motion.div>
            <motion.h2
              className="font-display text-3xl font-bold text-cream-50"
              initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: prefersReducedMotion ? 0 : 0.4, delay: prefersReducedMotion ? 0 : 0.2 }}
            >
              {t("board.goalCompleteTitle")}
            </motion.h2>
            <p className="max-w-sm text-cream-50/80">
              {t("board.goalCompleteBody", { name: goalName })}
            </p>
            <PrimaryButton type="button" className="px-6" onClick={onDismiss}>
              {t("board.animationDismiss")}
            </PrimaryButton>
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
