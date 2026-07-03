import { ApiError } from "./api";

export function errorMessage(error: unknown, fallback: string): string | null {
  if (!error) return null;
  if (error instanceof ApiError) return error.message;
  return fallback;
}
