import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { Board } from "./types";

export function useBoard() {
  return useQuery({
    queryKey: ["board"] as const,
    queryFn: () => api.get<Board>("/board"),
  });
}

interface TaxReturnRequest {
  account_id?: string | null;
  amount_cents: number;
}

export function useRecordTaxReturnMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TaxReturnRequest) => api.post<Board>("/board/tax-return", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["board"] }),
  });
}
