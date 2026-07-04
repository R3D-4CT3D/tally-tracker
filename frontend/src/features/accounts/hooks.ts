import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { Account, AccountCreateRequest, AccountUpdateRequest } from "./types";

const accountsQueryOptions = (includeArchived: boolean) => ({
  queryKey: ["accounts", { includeArchived }] as const,
  queryFn: () =>
    api.get<Account[]>(`/accounts${includeArchived ? "?include_archived=true" : ""}`),
});

export function useAccounts(includeArchived = false) {
  return useQuery(accountsQueryOptions(includeArchived));
}

export function useCreateAccountMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AccountCreateRequest) => api.post<Account>("/accounts", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["accounts"] }),
  });
}

export function useUpdateAccountMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: AccountUpdateRequest }) =>
      api.patch<Account>(`/accounts/${id}`, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["accounts"] }),
  });
}

export function useArchiveAccountMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Account>(`/accounts/${id}/archive`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["accounts"] }),
  });
}
