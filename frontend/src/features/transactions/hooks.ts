import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type {
  Transaction,
  TransactionCountResponse,
  TransactionCreateRequest,
  TransactionFilters,
  TransactionListParams,
  TransactionListResponse,
  TransactionUpdateRequest,
} from "./types";

function buildFilterParams(filters: TransactionFilters): URLSearchParams {
  const search = new URLSearchParams();
  if (filters.date_from) search.set("date_from", filters.date_from);
  if (filters.date_to) search.set("date_to", filters.date_to);
  if (filters.account_id) search.set("account_id", filters.account_id);
  if (filters.category_id) search.set("category_id", filters.category_id);
  if (filters.uncategorized) search.set("uncategorized", "true");
  if (filters.debt_id) search.set("debt_id", filters.debt_id);
  if (filters.created_after) search.set("created_after", filters.created_after);
  if (filters.search) search.set("search", filters.search);
  return search;
}

function buildQueryString(params: TransactionListParams): string {
  const search = buildFilterParams(params);
  if (params.cursor) search.set("cursor", params.cursor);
  if (params.limit) search.set("limit", String(params.limit));
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

const transactionsQueryOptions = (params: TransactionListParams) => ({
  queryKey: ["transactions", params] as const,
  queryFn: () =>
    api.get<TransactionListResponse>(`/transactions${buildQueryString(params)}`),
});

export function useTransactions(params: TransactionListParams) {
  return useQuery({
    ...transactionsQueryOptions(params),
    // Cursor pagination: keep the previous page's rows on screen while the
    // next page loads instead of flashing to a loading state, since the
    // query key changes on every cursor/filter change.
    placeholderData: (previous) => previous,
  });
}

export function useTransaction(id: string | undefined) {
  return useQuery({
    queryKey: ["transaction", id] as const,
    queryFn: () => api.get<Transaction>(`/transactions/${id}`),
    enabled: id !== undefined,
  });
}

export function useCreateTransactionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TransactionCreateRequest) =>
      api.post<Transaction>("/transactions", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["transactions"] }),
  });
}

export function useUpdateTransactionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: TransactionUpdateRequest }) =>
      api.patch<Transaction>(`/transactions/${id}`, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["transactions"] }),
  });
}

export function useDeleteTransactionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/transactions/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["transactions"] }),
  });
}

export function useTransactionCount(filters: TransactionFilters, enabled = true) {
  const qs = buildFilterParams(filters).toString();
  return useQuery({
    queryKey: ["transaction-count", filters] as const,
    queryFn: () => api.get<TransactionCountResponse>(`/transactions/count${qs ? `?${qs}` : ""}`),
    enabled,
  });
}

export function useUncategorizedCount() {
  return useQuery({
    queryKey: ["uncategorized-count"] as const,
    queryFn: () => api.get<TransactionCountResponse>("/transactions/uncategorized-count"),
  });
}
