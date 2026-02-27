import { useAuthStore } from "../store/authStore";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

type Json = Record<string, unknown> | unknown[] | string | number | boolean | null;

async function request<T>(
  path: string,
  init: RequestInit = {},
  retryOn401 = true,
): Promise<T> {
  const token = useAuthStore.getState().accessToken;
  const headers = new Headers(init.headers ?? {});
  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  const isAuthRefreshRequest = path === "/auth/refresh";
  if (response.status === 401 && retryOn401 && !isAuthRefreshRequest) {
    const refreshed = await useAuthStore.getState().refreshSession();
    if (refreshed) {
      return request<T>(path, init, false);
    }
  }

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const errBody = await response.json();
      detail = (errBody as { message?: string; detail?: string }).message || (errBody as { detail?: string }).detail || detail;
    } catch {
      // Ignore JSON parse failure for error responses.
    }
    throw new Error(detail);
  }

  if (response.status === 204) return undefined as T;
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const apiClient = {
  request,
  get: <T,>(path: string) => request<T>(path, { method: "GET" }),
  post: <T,>(path: string, body?: Json | FormData) =>
    request<T>(path, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body ?? {}) }),
  put: <T,>(path: string, body?: Json | FormData) =>
    request<T>(path, { method: "PUT", body: body instanceof FormData ? body : JSON.stringify(body ?? {}) }),
  patch: <T,>(path: string, body?: Json) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body ?? {}) }),
  delete: <T,>(path: string) => request<T>(path, { method: "DELETE" }),
  async postForm<T>(path: string, formData: FormData): Promise<T> {
    return request<T>(path, { method: "POST", body: formData });
  },
  baseUrl: API_BASE_URL,
};
