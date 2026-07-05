import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type {
  Bill,
  BillCreateRequest,
  BillMarkPaidRequest,
  BillPayment,
  BillUpdateRequest,
} from "./types";

const billsQueryOptions = (includeArchived: boolean) => ({
  queryKey: ["bills", { includeArchived }] as const,
  queryFn: () => api.get<Bill[]>(`/bills${includeArchived ? "?include_archived=true" : ""}`),
});

export function useBills(includeArchived = false) {
  return useQuery(billsQueryOptions(includeArchived));
}

export function useCreateBillMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BillCreateRequest) => api.post<Bill>("/bills", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bills"] }),
  });
}

export function useUpdateBillMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: BillUpdateRequest }) =>
      api.patch<Bill>(`/bills/${id}`, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bills"] }),
  });
}

export function useArchiveBillMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Bill>(`/bills/${id}/archive`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bills"] }),
  });
}

export function useMarkBillPaidMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: BillMarkPaidRequest }) =>
      api.post<BillPayment>(`/bills/${id}/mark-paid`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bills"] });
      queryClient.invalidateQueries({ queryKey: ["bill-payments"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
}

export function useBillPayments(billId: string | undefined) {
  return useQuery({
    queryKey: ["bill-payments", billId] as const,
    queryFn: () => api.get<BillPayment[]>(`/bills/${billId}/payments`),
    enabled: billId !== undefined,
  });
}
