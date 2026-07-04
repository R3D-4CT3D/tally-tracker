import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { Rule, RuleCreateRequest, RuleUpdateRequest } from "./types";

const rulesQueryOptions = {
  queryKey: ["rules"] as const,
  queryFn: () => api.get<Rule[]>("/rules"),
};

export function useRules() {
  return useQuery(rulesQueryOptions);
}

export function useCreateRuleMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RuleCreateRequest) => api.post<Rule>("/rules", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useUpdateRuleMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: RuleUpdateRequest }) =>
      api.patch<Rule>(`/rules/${id}`, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useDeleteRuleMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/rules/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useReorderRulesMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (orderedIds: string[]) =>
      api.post<Rule[]>("/rules/reorder", { ordered_ids: orderedIds }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["rules"] }),
  });
}
