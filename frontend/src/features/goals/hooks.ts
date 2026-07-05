import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type {
  Goal,
  GoalContribution,
  GoalContributionCreateRequest,
  GoalCreateRequest,
  GoalUpdateRequest,
} from "./types";

const goalsQueryOptions = {
  queryKey: ["goals"] as const,
  queryFn: () => api.get<Goal[]>("/goals"),
};

export function useGoals() {
  return useQuery(goalsQueryOptions);
}

export function useCreateGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: GoalCreateRequest) => api.post<Goal>("/goals", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useUpdateGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: GoalUpdateRequest }) =>
      api.patch<Goal>(`/goals/${id}`, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useDeleteGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/goals/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useRecordContributionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: GoalContributionCreateRequest }) =>
      api.post<GoalContribution>(`/goals/${id}/contributions`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["goals"] });
      queryClient.invalidateQueries({ queryKey: ["goal-contributions"] });
    },
  });
}

export function useGoalContributions(goalId: string | undefined) {
  return useQuery({
    queryKey: ["goal-contributions", goalId] as const,
    queryFn: () => api.get<GoalContribution[]>(`/goals/${goalId}/contributions`),
    enabled: goalId !== undefined,
  });
}
