// Typed API client. All backend calls live here; components never fetch directly.
// URLs are relative — the Vite dev server proxies /api to the FastAPI backend.

import type {
  Anomaly, ChatMessage, ChatStyle, ConversationDetail, ConversationSummary,
  Correction, LinkTokenResponse, MonthlyPoint, PlaidItemResult, PlaidStatus,
  PlaidSyncResult, QueryResponse, SendResult, Subscription, Summary,
  Transaction, TransactionList, UploadResult,
} from "../types";

// --- Auth token (persisted so a refresh keeps you logged in) ---
const TOKEN_KEY = "finance_ai_token";
// Marks the shared demo session, which uses the stateless (unsaved) chat path.
const DEMO_KEY = "finance_ai_demo";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(DEMO_KEY);
};
export const isDemo = () => localStorage.getItem(DEMO_KEY) === "1";

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
  if (res.status === 204) return undefined as T;  // no content (e.g. DELETE)
  return res.json() as Promise<T>;
}

export interface TransactionFilters {
  page?: number;
  page_size?: number;
  category?: string;
  search?: string;
  low_confidence?: boolean;
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

  register: (email: string, password: string, turnstileToken?: string) =>
    authRequest("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, turnstile_token: turnstileToken }),
    }),

  login: async (email: string, password: string) => {
    const res = await authRequest("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: email, password }),
    });
    const data = (await res.json()) as { access_token: string };
    localStorage.removeItem(DEMO_KEY);
    setToken(data.access_token);
    return data;
  },

  // Enter the shared demo account (sample data) — no signup. Marks the session
  // as demo so the chat uses the stateless, unsaved path.
  demo: async () => {
    const res = await authRequest("/api/auth/demo", { method: "POST" });
    const data = (await res.json()) as { access_token: string };
    setToken(data.access_token);
    localStorage.setItem(DEMO_KEY, "1");
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

  updateCategory: (id: number, category: string) =>
    http<Transaction>(`/api/transactions/${id}/category`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category }),
    }),

  corrections: () => http<Correction[]>("/api/corrections"),

  logoutAll: () => http<{ detail: string }>("/api/auth/logout-all", { method: "POST" }),

  changePassword: (current_password: string, new_password: string) =>
    http<{ detail: string }>("/api/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password, new_password }),
    }),

  subscriptions: (kind?: "subscription" | "bill") =>
    http<Subscription[]>(`/api/subscriptions${kind ? `?kind=${kind}` : ""}`),

  anomalies: () => http<Anomaly[]>("/api/anomalies"),

  // Stateless chat (demo / ephemeral): the client supplies recent turns as
  // context; nothing is saved server-side.
  query: (question: string, history: ChatMessage[] = [], style: ChatStyle = "friendly") =>
    http<QueryResponse>("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        style,
        history: history.map((m) => ({ role: m.role, content: m.content })),
      }),
    }),

  // Persisted chat (real users): durable, resumable threads.
  listConversations: () => http<ConversationSummary[]>("/api/conversations"),

  getConversation: (id: number) => http<ConversationDetail>(`/api/conversations/${id}`),

  sendMessage: (question: string, conversationId: number | null, style: ChatStyle = "friendly") =>
    http<SendResult>("/api/conversations/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, style, conversation_id: conversationId }),
    }),

  deleteConversation: (id: number) =>
    http<void>(`/api/conversations/${id}`, { method: "DELETE" }),

  uploadCsv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return http<UploadResult>("/api/upload", { method: "POST", body: form });
  },

  loadSample: () => http<UploadResult>("/api/load-sample", { method: "POST" }),

  clearData: () =>
    http<{ transactions_deleted: number }>("/api/account/clear-data", { method: "POST" }),

  // --- Plaid (sandbox) ---
  plaidStatus: () => http<PlaidStatus>("/api/plaid/status"),
  plaidLinkToken: () => http<LinkTokenResponse>("/api/plaid/link-token", { method: "POST" }),
  plaidExchange: (public_token: string) =>
    http<PlaidItemResult>("/api/plaid/exchange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ public_token }),
    }),
  plaidSync: () => http<PlaidSyncResult>("/api/plaid/sync", { method: "POST" }),
};
