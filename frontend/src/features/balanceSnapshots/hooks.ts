import { useQuery } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { BalanceSnapshot } from "./types";

// Read-only: M5's dashboard sparklines are the real consumer of this, but
// the endpoint ships in M4 alongside the nightly job that populates it.
export function useBalanceSnapshots(dateFrom?: string, dateTo?: string) {
  const search = new URLSearchParams();
  if (dateFrom) search.set("date_from", dateFrom);
  if (dateTo) search.set("date_to", dateTo);
  const qs = search.toString();

  return useQuery({
    queryKey: ["balance-snapshots", { dateFrom, dateTo }] as const,
    queryFn: () => api.get<BalanceSnapshot[]>(`/balance-snapshots${qs ? `?${qs}` : ""}`),
  });
}
