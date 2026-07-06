import type { ReactNode } from "react";

import type { BoardTile } from "../../features/board/types";
import { BoardTileSquare } from "./BoardTileSquare";

interface BoardGridProps {
  tiles: BoardTile[];
  /** Rendered centered in the board's empty interior -- a real Monopoly
   * board has board art there; this app puts the streak summary instead
   * of leaving it fully blank. */
  centerContent?: ReactNode;
}

const GRID_SIDE = 14; // 4 * (14 - 1) == 52 tiles, corners shared between sides.

// Maps a 0..51 tile index to a {row, col} cell in a 14x14 CSS grid, walking
// the perimeter counter-clockwise starting at the bottom-right corner (GO),
// the same convention a real Monopoly board uses. Each of the 4 sides holds
// `m` tiles (m = GRID_SIDE - 1 = 13); each side's *last* tile lands exactly
// on the shared corner with the next side, so 4 * m == 52 with no overlap
// and no gap.
function gridPosition(index: number): { row: number; col: number } {
  const n = GRID_SIDE;
  const m = n - 1;
  if (index <= m - 1) {
    // Bottom row, right to left: col 14..2, row 14.
    return { row: n, col: n - index };
  }
  if (index <= 2 * m - 1) {
    // Left column, bottom to top: row 14..2, col 1.
    return { row: n - (index - m), col: 1 };
  }
  if (index <= 3 * m - 1) {
    // Top row, left to right: col 1..13, row 1.
    return { row: 1, col: 1 + (index - 2 * m) };
  }
  // Right column, top to bottom: row 1..13, col 14.
  return { row: 1 + (index - 3 * m), col: n };
}

// Desktop: the full square board, tiles arranged around the perimeter of a
// 14x14 grid. --tile-size is set responsively (44px at md, 64px at lg+) so
// the fixed-track grid (14 * tile size) never exceeds the viewport at
// exactly 768px -- a real overflow bug at that width, caught by the phase 8
// mobile-viewport audit, before this fix.
export function BoardGrid({ tiles, centerContent }: BoardGridProps) {
  return (
    <div
      className="mx-auto hidden [--tile-size:44px] md:grid md:gap-1 lg:[--tile-size:64px]"
      style={{
        gridTemplateColumns: `repeat(${GRID_SIDE}, var(--tile-size))`,
        gridTemplateRows: `repeat(${GRID_SIDE}, var(--tile-size))`,
      }}
    >
      {tiles.map((tile) => {
        const { row, col } = gridPosition(tile.index);
        return (
          <div key={tile.index} style={{ gridRow: row, gridColumn: col }}>
            <BoardTileSquare tile={tile} sized={false} />
          </div>
        );
      })}
      {centerContent ? (
        <div
          className="flex items-center justify-center"
          style={{ gridRow: "2 / -2", gridColumn: "2 / -2" }}
        >
          {centerContent}
        </div>
      ) : null}
    </div>
  );
}
