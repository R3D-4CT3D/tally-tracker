import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type {
  Transaction,
  TransactionCreateRequest,
  TransactionListParams,
  TransactionListResponse,
  TransactionUpdateRequest,
} from "./types";

function buildQueryString(params: TransactionListParams): string {
  const search = new URLSearchParams();
  if (params.date_from) search.set("date_from", params.date_from);
  if (params.date_to) search.set("date_to", params.date_to);
  if (params.account_id) search.set("account_id", params.account_id);
  if (params.category_id) search.set("category_id", params.category_id);
  if (params.uncategorized) search.set("uncategorized", "true");
  if (params.debt_id) search.set("debt_id", params.debt_id);
  if (params.search) search.set("search", params.search);
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
