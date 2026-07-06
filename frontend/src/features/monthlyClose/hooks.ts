import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { MonthlyClose, MonthlyCloseSnapshot } from "./types";

export function useMonthlyClosePreview(month: string, enabled = true) {
  return useQuery({
    queryKey: ["monthlyClosePreview", month] as const,
    queryFn: () => api.get<MonthlyCloseSnapshot>(`/monthly-close/preview?month=${month}`),
    enabled,
  });
}

export function useMonthlyClose(month: string, enabled = true) {
  return useQuery({
    queryKey: ["monthlyClose", month] as const,
    queryFn: () => api.get<MonthlyClose>(`/monthly-close/${month}`),
    enabled,
    retry: false,
  });
}

export function useMonthlyCloseHistory() {
  return useQuery({
    queryKey: ["monthlyCloseHistory"] as const,
    queryFn: () => api.get<MonthlyClose[]>("/monthly-close"),
  });
}

export function useCompleteMonthlyCloseMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (month: string) =>
      api.post<MonthlyClose>("/monthly-close/complete", { month }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monthlyCloseHistory"] });
      queryClient.invalidateQueries({ queryKey: ["monthlyClose"] });
      queryClient.invalidateQueries({ queryKey: ["board"] });
    },
  });
}
