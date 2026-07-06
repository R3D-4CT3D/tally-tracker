export type TileKind =
  | "go"
  | "property"
  | "mortgage"
  | "chest"
  | "chance"
  | "tax"
  | "jail"
  | "free_parking"
  | "plain";

export interface BoardTile {
  index: number;
  kind: TileKind;
  label: string;
  color: string | null;
  icon: string | null;
  amount_cents: number | null;
  owned: boolean;
  is_current: boolean;
  ref_id: string | null;
}

export interface BoardStreak {
  current_weeks: number;
  best_weeks: number;
  freezes_banked: number;
}

export interface Board {
  year_start_date: string;
  current_week: number;
  board_size: number;
  tiles: BoardTile[];
  streak: BoardStreak;
  year_end_pending: boolean;
}
