export type Grade = "A" | "B" | "C" | "D";

export interface MonthlyCloseSnapshot {
  uncategorized_count: number;
  income_cents: number;
  spend_cents: number;
  prior_income_cents: number | null;
  prior_spend_cents: number | null;
  debt_payments_cents: number;
  total_debt_cents: number;
  start_of_month_debt_cents: number | null;
  goal_contributions_cents: number;
  goals_completed: string[];
  net_worth_cents: number | null;
  prior_net_worth_cents: number | null;
  grade: Grade;
  highlight: string;
}

export interface MonthlyClose {
  id: string;
  month: string;
  completed_by: string;
  completed_at: string;
  grade: Grade;
  snapshot: MonthlyCloseSnapshot;
}
