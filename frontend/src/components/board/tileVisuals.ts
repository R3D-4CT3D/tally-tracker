import type { TileKind } from "../../features/board/types";

interface TileVisual {
  icon: string;
  bgClassName: string;
}

// Flavor styling per tile kind -- property/mortgage tiles use the entity's
// own color instead (see BoardTile.tsx), everything else gets a fixed look.
export const TILE_VISUALS: Record<Exclude<TileKind, "property" | "mortgage">, TileVisual> = {
  go: { icon: "➡️", bgClassName: "bg-green-500 text-white" },
  chest: { icon: "🎁", bgClassName: "bg-cream-200 text-navy-950 dark:bg-navy-700 dark:text-cream-50" },
  chance: { icon: "❓", bgClassName: "bg-cream-200 text-navy-950 dark:bg-navy-700 dark:text-cream-50" },
  tax: { icon: "🧾", bgClassName: "bg-danger-100 text-danger-700 dark:bg-danger-900 dark:text-danger-200" },
  jail: { icon: "🚧", bgClassName: "bg-surface-subtle text-text-primary/70" },
  free_parking: { icon: "🅿️", bgClassName: "bg-surface-subtle text-text-primary/70" },
  plain: { icon: "", bgClassName: "bg-surface-subtle text-text-primary/50" },
};
