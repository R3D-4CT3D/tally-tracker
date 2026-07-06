import { motion } from "framer-motion";

import { useReducedMotion } from "../../design-system/useReducedMotion";
import type { BoardTile, TileKind } from "../../features/board/types";
import { formatCentsDisplay } from "../../lib/money";
import { TILE_VISUALS } from "./tileVisuals";

type NonEntityTileKind = Exclude<TileKind, "property" | "mortgage">;

interface BoardTileSquareProps {
  tile: BoardTile;
  className?: string;
  /** true (default): fixed 64px, for BoardTrack's horizontal scroll where
   * viewport width isn't a constraint. false: sized by the ancestor's
   * --tile-size CSS var instead, for BoardGrid's responsive fixed-track
   * layout (see BoardGrid.tsx). */
  sized?: boolean;
}

// One square on the board -- used by both the mobile linear BoardTrack and
// the desktop perimeter BoardGrid. Property/mortgage tiles get a colored
// header band (the entity's own color, mirroring PropertyCard); every other
// kind gets a fixed flavor look from tileVisuals.ts.
export function BoardTileSquare({ tile, className = "", sized = true }: BoardTileSquareProps) {
  const prefersReducedMotion = useReducedMotion();
  const isEntityTile = tile.kind === "property" || tile.kind === "mortgage";

  return (
    <div
      className={`relative flex shrink-0 flex-col overflow-hidden rounded-md border text-[10px] ${
        sized ? "h-16 w-16" : "h-[var(--tile-size)] w-[var(--tile-size)]"
      } ${tile.is_current ? "border-green-500 ring-2 ring-green-500" : "border-border/15"} ${className}`}
    >
      {isEntityTile ? (
        <>
          <div
            className="h-4 w-full shrink-0"
            style={{ backgroundColor: tile.color ?? "#2c3463" }}
            aria-hidden
          />
          <div className="flex flex-1 flex-col items-center justify-center gap-0.5 bg-cream-50 px-0.5 text-center dark:bg-surface-card">
            <span aria-hidden>{tile.icon}</span>
            <span className="w-full truncate leading-tight text-navy-950 dark:text-text-primary">
              {tile.label}
            </span>
            {tile.amount_cents !== null ? (
              <span className="text-text-primary/60">{formatCentsDisplay(tile.amount_cents)}</span>
            ) : null}
            {tile.owned ? <span aria-hidden>✅</span> : null}
          </div>
        </>
      ) : (
        <div
          className={`flex h-full w-full flex-col items-center justify-center gap-0.5 text-center ${TILE_VISUALS[tile.kind as NonEntityTileKind].bgClassName}`}
        >
          <span aria-hidden className="text-base">
            {TILE_VISUALS[tile.kind as NonEntityTileKind].icon}
          </span>
          <span className="w-full truncate px-0.5 leading-tight">{tile.label}</span>
        </div>
      )}
      {tile.is_current ? (
        <motion.span
          className="absolute -top-2 left-1/2 -translate-x-1/2 text-lg"
          aria-hidden
          initial={{ y: prefersReducedMotion ? 0 : -4 }}
          animate={{ y: prefersReducedMotion ? 0 : [0, -4, 0] }}
          transition={{ duration: 1.2, repeat: prefersReducedMotion ? 0 : Infinity }}
        >
          🧑
        </motion.span>
      ) : null}
    </div>
  );
}
