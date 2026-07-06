import { useSyncExternalStore } from "react";

const QUERY = "(max-width: 767px)";

function subscribe(callback: () => void): () => void {
  const media = window.matchMedia(QUERY);
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}

function getSnapshot(): boolean {
  return window.matchMedia(QUERY).matches;
}

/** Matches Tailwind's md: breakpoint (768px) -- used to gate touch-only
 * interactions (swipe gestures) that shouldn't also trigger on desktop
 * mouse-drag. */
export function useIsMobile(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot);
}
