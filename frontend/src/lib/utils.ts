import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge conditional Tailwind class names, resolving conflicts. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a number as US dollars. */
export const fmtUSD = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

/** Format an ISO date (YYYY-MM-DD) as e.g. "Mar 15, 2024". */
export const fmtDate = (iso: string) =>
  new Date(iso + "T00:00:00").toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });

/** Consistent colors per category across every chart and badge. */
export const CATEGORY_COLORS: Record<string, string> = {
  income: "#16a34a", rent: "#7c3aed", groceries: "#059669",
  restaurants: "#f97316", subscriptions: "#4f46e5", transport: "#0891b2",
  utilities: "#ca8a04", entertainment: "#db2777", shopping: "#2563eb",
  health: "#dc2626", fees: "#64748b", transfers: "#0d9488", other: "#94a3b8",
};

export const colorFor = (category: string) => CATEGORY_COLORS[category] ?? "#94a3b8";
