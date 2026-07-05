export type BillFrequency = "monthly" | "quarterly" | "annual" | "custom";

export const BILL_FREQUENCIES: BillFrequency[] = ["monthly", "quarterly", "annual", "custom"];

export interface Bill {
  id: string;
  name: string;
  amount_cents: number | null;
  is_variable: boolean;
  frequency: BillFrequency;
  due_day: number;
  custom_interval_days: number | null;
  account_id: string | null;
  category_id: string | null;
  autopay: boolean;
  next_due_date: string;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface BillCreateRequest {
  name: string;
  amount_cents?: number | null;
  is_variable?: boolean;
  frequency: BillFrequency;
  due_day: number;
  custom_interval_days?: number | null;
  account_id?: string | null;
  category_id?: string | null;
  autopay?: boolean;
  next_due_date: string;
}

export interface BillUpdateRequest {
  name?: string;
  amount_cents?: number | null;
  is_variable?: boolean;
  frequency?: BillFrequency;
  due_day?: number;
  custom_interval_days?: number | null;
  account_id?: string | null;
  category_id?: string | null;
  autopay?: boolean;
  next_due_date?: string;
}

export interface BillMarkPaidRequest {
  transaction_id?: string;
  account_id?: string;
  amount_cents?: number;
  date?: string;
  category_id?: string | null;
  notes?: string | null;
}

export type BillPaymentStatus = "pending" | "paid" | "skipped";

export interface BillPayment {
  id: string;
  bill_id: string;
  transaction_id: string | null;
  due_date: string;
  paid_date: string | null;
  amount_cents: number;
  status: BillPaymentStatus;
  created_at: string;
  updated_at: string;
}
