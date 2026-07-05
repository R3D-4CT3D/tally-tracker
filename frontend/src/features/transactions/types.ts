export interface Transaction {
  id: string;
  account_id: string;
  date: string;
  amount_cents: number;
  description_raw: string;
  description_display: string;
  category_id: string | null;
  notes: string | null;
  source: string;
  created_by: string;
  debt_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionCreateRequest {
  account_id: string;
  date: string;
  amount_cents: number;
  description: string;
  category_id?: string | null;
  notes?: string | null;
  debt_id?: string | null;
}

export interface TransactionUpdateRequest {
  account_id?: string;
  date?: string;
  amount_cents?: number;
  description?: string;
  category_id?: string | null;
  notes?: string | null;
  debt_id?: string | null;
}

export interface TransactionFilters {
  date_from?: string;
  date_to?: string;
  account_id?: string;
  category_id?: string;
  uncategorized?: boolean;
  debt_id?: string;
  search?: string;
}

export interface TransactionListParams extends TransactionFilters {
  cursor?: string;
  limit?: number;
}

export interface TransactionListResponse {
  items: Transaction[];
  next_cursor: string | null;
}
