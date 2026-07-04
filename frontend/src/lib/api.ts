const API_PREFIX = "/api/v1";
const CSRF_COOKIE_NAME = "tally_csrf";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function getCookie(name: string): string | null {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  // FormData bodies (file uploads) must NOT get an explicit Content-Type --
  // the browser sets multipart/form-data with the correct boundary itself
  // only when it's left unset.
  if (!(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // The one place CSRF gets wired in — every mutating call across the whole
  // app goes through this function, so nothing sets the header per-call.
  if (method !== "GET" && method !== "HEAD") {
    const csrfToken = getCookie(CSRF_COOKIE_NAME);
    if (csrfToken) {
      headers.set("X-CSRF-Token", csrfToken);
    }
  }

  const response = await fetch(`${API_PREFIX}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    const message =
      typeof body?.detail === "string" ? body.detail : "Something went wrong. Please try again.";
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string): Promise<T> => request<T>(path),
  post: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, {
      method: "PATCH",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  delete: <T>(path: string): Promise<T> => request<T>(path, { method: "DELETE" }),
  postForm: <T>(path: string, formData: FormData): Promise<T> =>
    request<T>(path, { method: "POST", body: formData }),
};
