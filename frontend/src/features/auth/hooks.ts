import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type {
  InviteAcceptRequest,
  LoginRequest,
  MeResponse,
  SetupRequest,
  SetupStatus,
  StatusResponse,
} from "./types";

const setupStatusQueryOptions = {
  queryKey: ["setup-status"] as const,
  queryFn: () => api.get<SetupStatus>("/setup/status"),
};

const meQueryOptions = {
  queryKey: ["me"] as const,
  queryFn: () => api.get<MeResponse>("/auth/me"),
};

export function useSetupStatus() {
  return useQuery(setupStatusQueryOptions);
}

export function useMe() {
  return useQuery(meQueryOptions);
}

/**
 * Setup/login/invite-accept all log the caller in as a side effect, but
 * their responses are just `{status: "ok"}` — not a MeResponse body. This
 * explicitly (re)fetches `me` into the cache (rather than just invalidating,
 * which only refetches *actively observed* queries) so RequireAuth sees a
 * populated cache the instant the page navigates to a protected route,
 * instead of racing a fresh 401 in flight.
 */
async function refreshMe(queryClient: ReturnType<typeof useQueryClient>): Promise<void> {
  await queryClient.fetchQuery(meQueryOptions);
}

export function useSetupMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SetupRequest) => api.post<StatusResponse>("/setup", payload),
    onSuccess: async () => {
      queryClient.setQueryData(setupStatusQueryOptions.queryKey, { is_setup: true });
      await refreshMe(queryClient);
    },
  });
}

export function useLoginMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LoginRequest) => api.post<StatusResponse>("/auth/login", payload),
    onSuccess: () => refreshMe(queryClient),
  });
}

export function useLogoutMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<StatusResponse>("/auth/logout"),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: meQueryOptions.queryKey });
    },
  });
}

export function useAcceptInviteMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: InviteAcceptRequest) =>
      api.post<StatusResponse>("/invites/accept", payload),
    onSuccess: () => refreshMe(queryClient),
  });
}
