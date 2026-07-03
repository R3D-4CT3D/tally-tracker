import { QueryClient } from "@tanstack/react-query";

// retry: false — a 401 from /auth/me or /setup/status is meaningful
// "not authenticated" / "not set up" state for the route guards to act on,
// not a transient failure worth retrying.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});
