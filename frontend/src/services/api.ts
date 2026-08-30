// Typed API client. All backend calls live here; components never fetch directly.
// URLs are relative — the Vite dev server proxies /api to the FastAPI backend.

import type {
  Anomaly, MonthlyPoint, QueryResponse, Subscription, Summary,
  TransactionList, UploadResult,
} from "../types";

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
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

export const api = {
  health: () => http<{ status: string }>("/api/health"),

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
