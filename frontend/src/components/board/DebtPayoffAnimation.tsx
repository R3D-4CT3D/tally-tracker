import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";

import { useReducedMotion } from "../../design-system/useReducedMotion";
import { PrimaryButton } from "../PrimaryButton";

interface DebtPayoffAnimationProps {
  open: boolean;
  debtName: string;
  onDismiss: () => void;
}

// Full-screen celebration for a debt's mortgage/railroad tile flipping to
// "paid off" (Debt.paid_off_at newly set). User-dismissed (not a timer)
// since this is a genuine milestone worth letting them savor, unlike
// PassingGoAnimation's automatic year-rollover sequence.
export function DebtPayoffAnimation({ open, debtName, onDismiss }: DebtPayoffAnimationProps) {
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
          aria-label={t("board.debtPayoffTitle")}
        >
          <div className="flex flex-col items-center gap-6 text-center">
            <motion.div
              className="text-6xl"
              initial={{ scale: prefersReducedMotion ? 1 : 0.4, rotate: 0 }}
              animate={{ scale: 1, rotate: prefersReducedMotion ? 0 : [0, -8, 8, -4, 0] }}
              transition={{ duration: prefersReducedMotion ? 0 : 0.7, ease: "easeOut" }}
              aria-hidden
            >
              🎉
            </motion.div>
            <motion.h2
              className="font-display text-3xl font-bold text-cream-50"
              initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: prefersReducedMotion ? 0 : 0.4, delay: prefersReducedMotion ? 0 : 0.2 }}
            >
              {t("board.debtPayoffTitle")}
            </motion.h2>
            <p className="max-w-sm text-cream-50/80">
              {t("board.debtPayoffBody", { name: debtName })}
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
