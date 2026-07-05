import { useQuery } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { Transaction, TransactionListResponse } from "../transactions/types";

function localDateString(date: Date): string {
  // Local date components, not toISOString() -- see TransactionFormPage's
  // today() helper for why (toISOString() converts to UTC and silently
  // rolls the date forward for anyone west of UTC in the evening).
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function monthStart(): string {
  const now = new Date();
  return localDateString(new Date(now.getFullYear(), now.getMonth(), 1));
}

export function today(): string {
  return localDateString(new Date());
}

export function daysFromToday(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return localDateString(date);
}

export interface CategorySpending {
  categoryId: string | null;
  cents: number;
}

async function fetchAllTransactionsInRange(dateFrom: string, dateTo: string): Promise<Transaction[]> {
  const items: Transaction[] = [];
  let cursor: string | undefined;
  // Paginate until exhausted -- a month's transactions can exceed the
  // 100-row page cap for a high-volume household; silently truncating here
  // would under-report spend rather than just being slower.
  for (;;) {
    const qs = new URLSearchParams({ date_from: dateFrom, date_to: dateTo, limit: "100" });
    if (cursor) qs.set("cursor", cursor);
    const page = await api.get<TransactionListResponse>(`/transactions?${qs.toString()}`);
    items.push(...page.items);
    if (!page.next_cursor) break;
    cursor = page.next_cursor;
  }
  return items;
}

// This-month spending, grouped by category -- only spend (negative amounts)
// counts; income would skew a "spending" breakdown. Uncategorized rows get
// their own bucket (categoryId: null) rather than being dropped, so the
// donut's total still matches the month's actual spend.
export function useMonthSpendingByCategory() {
  const dateFrom = monthStart();
  const dateTo = today();
  return useQuery({
    queryKey: ["dashboard", "month-spending", dateFrom, dateTo] as const,
    queryFn: async (): Promise<CategorySpending[]> => {
      const items = await fetchAllTransactionsInRange(dateFrom, dateTo);
      const totals = new Map<string | null, number>();
      for (const item of items) {
        if (item.amount_cents >= 0) continue;
        const key = item.category_id;
        totals.set(key, (totals.get(key) ?? 0) + Math.abs(item.amount_cents));
      }
      return Array.from(totals.entries()).map(([categoryId, cents]) => ({ categoryId, cents }));
    },
  });
}

export interface GoalProjection {
  monthlyRateCents: number;
  projectedDate: string | null;
}

export function computeGoalProjection(
  contributions: { date: string; amount_cents: number }[],
  targetCents: number,
  currentCents: number,
): GoalProjection {
  const cutoff = daysFromToday(-90);
  const trailing90dTotal = contributions
    .filter((c) => c.date >= cutoff)
    .reduce((sum, c) => sum + c.amount_cents, 0);
  const monthlyRateCents = trailing90dTotal / 3;
  if (monthlyRateCents <= 0) {
    return { monthlyRateCents, projectedDate: null };
  }
  const remaining = targetCents - currentCents;
  const monthsToGo = Math.ceil(remaining / monthlyRateCents);
  const projected = new Date();
  projected.setMonth(projected.getMonth() + monthsToGo);
  return { monthlyRateCents, projectedDate: localDateString(projected) };
}

// Next calendar occurrence of a bill/debt's due_day (1-31) from today --
// there's no stored next_due_date on Debt, only Bill has one.
export function nextOccurrenceOfDay(dueDay: number): string {
  const now = new Date();
  const clampedDay = Math.min(dueDay, 28); // avoid rolling into the wrong month for short months
  let candidate = new Date(now.getFullYear(), now.getMonth(), clampedDay);
  if (candidate < new Date(now.getFullYear(), now.getMonth(), now.getDate())) {
    candidate = new Date(now.getFullYear(), now.getMonth() + 1, clampedDay);
  }
  return localDateString(candidate);
}
