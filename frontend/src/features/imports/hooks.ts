import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type {
  ColumnMapping,
  DateFormat,
  ImportBatch,
  ImportPreviewResponse,
  ImportUploadResponse,
} from "./types";

export function useUploadCsvMutation() {
  return useMutation({
    mutationFn: ({ file, profileId }: { file: File; profileId?: string }) => {
      const formData = new FormData();
      formData.append("file", file);
      if (profileId) formData.append("profile_id", profileId);
      return api.postForm<ImportUploadResponse>("/imports/upload", formData);
    },
  });
}

export function usePasteImportMutation() {
  return useMutation({
    mutationFn: (payload: { text: string; profileId?: string }) =>
      api.post<ImportUploadResponse>("/imports/paste", {
        text: payload.text,
        profile_id: payload.profileId ?? null,
      }),
  });
}

export function usePreviewImportMutation() {
  return useMutation({
    mutationFn: (params: {
      sessionId: string;
      columnMapping: ColumnMapping;
      dateFormat: DateFormat;
      accountId: string;
    }) =>
      api.post<ImportPreviewResponse>(`/imports/${params.sessionId}/preview`, {
        column_mapping: params.columnMapping,
        date_format: params.dateFormat,
        account_id: params.accountId,
      }),
  });
}

export function useCommitImportMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      sessionId: string;
      columnMapping: ColumnMapping;
      dateFormat: DateFormat;
      accountId: string;
      overrides?: Record<string, boolean>;
      saveProfileName?: string;
    }) =>
      api.post<ImportBatch>(`/imports/${params.sessionId}/commit`, {
        column_mapping: params.columnMapping,
        date_format: params.dateFormat,
        account_id: params.accountId,
        overrides: params.overrides ?? {},
        save_profile_name: params.saveProfileName || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["import-batches"] });
      queryClient.invalidateQueries({ queryKey: ["import-profiles"] });
    },
  });
}

const batchesQueryOptions = {
  queryKey: ["import-batches"] as const,
  queryFn: () => api.get<ImportBatch[]>("/imports/batches"),
};

export function useImportBatches() {
  return useQuery(batchesQueryOptions);
}

export function useUndoImportBatchMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (batchId: string) => api.delete<void>(`/imports/batches/${batchId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["import-batches"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
}
