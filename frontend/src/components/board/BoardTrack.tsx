import { useEffect, useRef } from "react";

import type { BoardTile } from "../../features/board/types";
import { BoardTileSquare } from "./BoardTileSquare";

interface BoardTrackProps {
  tiles: BoardTile[];
}

// Mobile: a horizontally scrollable linear strip of all 52 tiles in order,
// auto-scrolled so the current tile starts centered in view on mount.
export function BoardTrack({ tiles }: BoardTrackProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const currentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    currentRef.current?.scrollIntoView({ inline: "center", block: "nearest" });
  }, []);

  return (
    <div ref={scrollRef} className="flex gap-2 overflow-x-auto pb-2 pt-3 md:hidden">
      {tiles.map((tile) => (
        <div key={tile.index} ref={tile.is_current ? currentRef : undefined}>
          <BoardTileSquare tile={tile} />
        </div>
      ))}
    </div>
  );
}
