import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { Category, CategoryCreateRequest, CategoryUpdateRequest } from "./types";

const categoriesQueryOptions = {
  queryKey: ["categories"] as const,
  queryFn: () => api.get<Category[]>("/categories"),
};

export function useCategories() {
  return useQuery(categoriesQueryOptions);
}

export function useCreateCategoryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CategoryCreateRequest) => api.post<Category>("/categories", payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categories"] }),
  });
}

export function useUpdateCategoryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CategoryUpdateRequest }) =>
      api.patch<Category>(`/categories/${id}`, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categories"] }),
  });
}
