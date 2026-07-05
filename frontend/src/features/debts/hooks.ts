import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { Debt, DebtCreateRequest, DebtUpdateRequest } from "./types";

const debtsQueryOptions = (includeArchived: boolean) => ({
  queryKey: ["debts", { includeArchived }] as const,
  queryFn: () => api.get<Debt[]>(`/debts${includeArchived ? "?include_archived=true" : ""}`),
});

export function useDebts(includeArchived = false) {
  return useQuery(debtsQueryOptions(includeArchived));
}

export function useCreateDebtMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DebtCreateRequest) => api.post<Debt>("/debts", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["debts"] }),
  });
}

export function useUpdateDebtMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: DebtUpdateRequest }) =>
      api.patch<Debt>(`/debts/${id}`, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["debts"] }),
  });
}

export function useArchiveDebtMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Debt>(`/debts/${id}/archive`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["debts"] }),
  });
}

// A debt payment is just a Transaction with debt_id set -- logging one
// invalidates both transactions and debts (the debt's current_balance_cents
// changes server-side as a result).
export function useLogDebtPaymentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      debt_id: string;
      account_id: string;
      amount_cents: number;
      date: string;
    }) =>
      api.post("/transactions", {
        account_id: payload.account_id,
        date: payload.date,
        amount_cents: payload.amount_cents,
        description: "Debt payment",
        debt_id: payload.debt_id,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["debts"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
}
