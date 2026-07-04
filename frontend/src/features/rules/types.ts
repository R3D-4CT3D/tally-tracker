export type MatchType = "contains" | "starts_with" | "regex";

export interface Rule {
  id: string;
  priority: number;
  match_type: MatchType;
  match_value: string;
  amount_min: number | null;
  amount_max: number | null;
  account_id: string | null;
  set_category_id: string;
  set_display_name: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface RuleCreateRequest {
  priority?: number | null;
  match_type: MatchType;
  match_value: string;
  amount_min?: number | null;
  amount_max?: number | null;
  account_id?: string | null;
  set_category_id: string;
  set_display_name?: string | null;
  enabled?: boolean;
}

export interface RuleUpdateRequest {
  priority?: number;
  match_type?: MatchType;
  match_value?: string;
  amount_min?: number | null;
  amount_max?: number | null;
  account_id?: string | null;
  set_category_id?: string;
  set_display_name?: string | null;
  enabled?: boolean;
}
