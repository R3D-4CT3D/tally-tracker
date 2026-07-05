import { useSyncExternalStore } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

function subscribe(callback: () => void): () => void {
  const media = window.matchMedia(QUERY);
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}

function getSnapshot(): boolean {
  return window.matchMedia(QUERY).matches;
}

/**
 * Hand-rolled (not framer-motion's own useReducedMotion) since several
 * consumers are plain CSS transitions or Recharts' `isAnimationActive` prop,
 * not Framer animations -- a stable local import path means the underlying
 * implementation can change later without touching call sites.
 */
export function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot);
}
