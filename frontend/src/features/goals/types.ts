export interface Goal {
  id: string;
  name: string;
  target_cents: number;
  current_cents: number;
  target_date: string | null;
  icon: string;
  color: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface GoalCreateRequest {
  name: string;
  target_cents: number;
  current_cents?: number;
  target_date?: string | null;
  icon: string;
  color: string;
}

export interface GoalUpdateRequest {
  name?: string;
  target_cents?: number;
  target_date?: string | null;
  icon?: string;
  color?: string;
}

export interface GoalContributionCreateRequest {
  amount_cents: number;
  date: string;
  transaction_id?: string | null;
}

export interface GoalContribution {
  id: string;
  goal_id: string;
  transaction_id: string | null;
  amount_cents: number;
  date: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}
