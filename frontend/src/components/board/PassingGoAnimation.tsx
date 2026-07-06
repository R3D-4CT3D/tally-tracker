import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTranslation } from "react-i18next";

import { useReducedMotion } from "../../design-system/useReducedMotion";

interface PassingGoAnimationProps {
  open: boolean;
  /** Called once the sequence finishes (or immediately, skipped to the end,
   * when the user prefers reduced motion) -- the caller advances to the
   * tax-return prompt from here, not from inside this component. */
  onComplete: () => void;
}

// Full-screen "passing GO" celebration: a die roll, a token sliding across a
// short track, then a bold banner. Purely a design/motion piece -- wired to
// the board's actual year-rollover trigger in a later phase. Reduced-motion
// users get the end state immediately rather than a skippable animation,
// consistent with the rest of the app's useReducedMotion gating.
export function PassingGoAnimation({ open, onComplete }: PassingGoAnimationProps) {
  const { t } = useTranslation();
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    if (!open) return;
    const delay = prefersReducedMotion ? 400 : 2600;
    const timer = setTimeout(onComplete, delay);
    return () => clearTimeout(timer);
  }, [open, prefersReducedMotion, onComplete]);

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/90"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: prefersReducedMotion ? 0 : 0.3 }}
          role="dialog"
          aria-label={t("board.passingGoTitle")}
        >
          <div className="flex flex-col items-center gap-8 px-6 text-center">
            <motion.div
              className="flex h-16 w-16 items-center justify-center rounded-xl bg-cream-50 text-3xl"
              initial={{ rotate: 0 }}
              animate={prefersReducedMotion ? { rotate: 0 } : { rotate: [0, 90, 180, 270, 360, 720] }}
              transition={{ duration: 1.2, ease: "easeOut" }}
              aria-hidden
            >
              🎲
            </motion.div>

            <div className="relative h-3 w-64 overflow-hidden rounded-full bg-cream-50/20">
              <motion.div
                className="absolute top-1/2 h-6 w-6 -translate-y-1/2 rounded-full bg-green-500 shadow-lg"
                initial={{ left: 0 }}
                animate={{ left: prefersReducedMotion ? "calc(100% - 24px)" : "calc(100% - 24px)" }}
                transition={{ duration: prefersReducedMotion ? 0 : 1.4, delay: prefersReducedMotion ? 0 : 1.2, ease: "easeInOut" }}
              />
            </div>

            <motion.h2
              className="font-display text-4xl font-bold text-cream-50"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{
                duration: prefersReducedMotion ? 0 : 0.5,
                delay: prefersReducedMotion ? 0 : 2.4,
              }}
            >
              {t("board.passingGoTitle")}
            </motion.h2>
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
