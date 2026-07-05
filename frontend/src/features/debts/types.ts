export type DebtType = "credit_card" | "auto_loan" | "student_loan" | "personal";

export const DEBT_TYPES: DebtType[] = ["credit_card", "auto_loan", "student_loan", "personal"];

export interface Debt {
  id: string;
  name: string;
  type: DebtType;
  original_balance_cents: number;
  current_balance_cents: number;
  apr_bps: number;
  min_payment_cents: number;
  due_day: number;
  paid_off_at: string | null;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface DebtCreateRequest {
  name: string;
  type: DebtType;
  original_balance_cents: number;
  current_balance_cents: number;
  apr_bps: number;
  min_payment_cents: number;
  due_day: number;
}

export interface DebtUpdateRequest {
  name?: string;
  type?: DebtType;
  original_balance_cents?: number;
  current_balance_cents?: number;
  apr_bps?: number;
  min_payment_cents?: number;
  due_day?: number;
}
