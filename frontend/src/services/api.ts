// Typed API client. All backend calls live here; components never fetch directly.
// URLs are relative — the Vite dev server proxies /api to the FastAPI backend.

import type {
  Anomaly, MonthlyPoint, QueryResponse, Subscription, Summary,
  TransactionList, UploadResult,
} from "../types";

// --- Auth token (persisted so a refresh keeps you logged in) ---
const TOKEN_KEY = "finance_ai_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

async function http<T>(url: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(url, { ...init, headers });

  if (res.status === 401) {
    // Token missing/expired: drop it and bounce to login (unless already there).
    clearToken();
    if (!location.pathname.startsWith("/login")) location.assign("/login");
    throw new Error("Not authenticated");
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface TransactionFilters {
  page?: number;
  page_size?: number;
  category?: string;
  search?: string;
}

async function authRequest(url: string, init: RequestInit): Promise<Response> {
  // Auth endpoints bypass http()'s 401-redirect so errors surface on the form.
  const res = await fetch(url, init);
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Request failed: ${res.status}`);
  }
  return res;
}

export const api = {
  health: () => http<{ status: string }>("/api/health"),

  register: (email: string, password: string) =>
    authRequest("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),

  login: async (email: string, password: string) => {
    const res = await authRequest("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: email, password }),
    });
    const data = (await res.json()) as { access_token: string };
    setToken(data.access_token);
    return data;
  },

  summary: () => http<Summary>("/api/analytics/summary"),
  byCategory: () => http<{ by_category: Record<string, number> }>("/api/analytics/by-category"),
  monthly: () => http<MonthlyPoint[]>("/api/analytics/monthly"),

  transactions: (filters: TransactionFilters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && v !== null) params.set(k, String(v));
    });
    return http<TransactionList>(`/api/transactions?${params.toString()}`);
  },

  subscriptions: (kind?: "subscription" | "bill") =>
    http<Subscription[]>(`/api/subscriptions${kind ? `?kind=${kind}` : ""}`),

  anomalies: () => http<Anomaly[]>("/api/anomalies"),

  query: (question: string) =>
    http<QueryResponse>("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),

  uploadCsv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return http<UploadResult>("/api/upload", { method: "POST", body: form });
  },

  loadSample: () => http<UploadResult>("/api/load-sample", { method: "POST" }),
};
