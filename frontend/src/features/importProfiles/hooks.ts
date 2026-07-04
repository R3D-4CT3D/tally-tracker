import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { ImportProfile, ImportProfileCreateRequest } from "./types";

const profilesQueryOptions = {
  queryKey: ["import-profiles"] as const,
  queryFn: () => api.get<ImportProfile[]>("/import-profiles"),
};

export function useImportProfiles() {
  return useQuery(profilesQueryOptions);
}

export function useCreateImportProfileMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ImportProfileCreateRequest) =>
      api.post<ImportProfile>("/import-profiles", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["import-profiles"] }),
  });
}

export function useDeleteImportProfileMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/import-profiles/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["import-profiles"] }),
  });
}
