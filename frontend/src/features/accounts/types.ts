export type AccountType = "checking" | "savings" | "credit_card" | "loan" | "cash";

export const ACCOUNT_TYPES: AccountType[] = [
  "checking",
  "savings",
  "credit_card",
  "loan",
  "cash",
];

export interface Account {
  id: string;
  name: string;
  type: AccountType;
  institution: string | null;
  balance_cents: number;
  color: string;
  icon: string;
  archived: boolean;
  last_four: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountCreateRequest {
  name: string;
  type: AccountType;
  institution?: string | null;
  balance_cents: number;
  color: string;
  icon: string;
  last_four?: string | null;
}

export interface AccountUpdateRequest {
  name?: string;
  type?: AccountType;
  institution?: string | null;
  balance_cents?: number;
  color?: string;
  icon?: string;
  last_four?: string | null;
}
