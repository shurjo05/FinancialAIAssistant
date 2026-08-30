import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { RefreshCw, AlertTriangle } from "lucide-react";
import { api } from "../services/api";
import { CategoryBadge, Card, Spinner, PageHeader } from "../components/ui";
import { fmtUSD, fmtDate, CATEGORY_COLORS } from "../lib/utils";

const PAGE_SIZE = 25;
const CATEGORIES = Object.keys(CATEGORY_COLORS);

export default function Transactions() {
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["transactions", page, category, search],
    queryFn: () => api.transactions({ page, page_size: PAGE_SIZE, category, search }),
    placeholderData: keepPreviousData,
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <PageHeader title="Transactions" subtitle={data ? `${data.total} transactions` : undefined} />

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search merchant…"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
        />
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(1); }}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm capitalize focus:border-brand-500 focus:outline-none"
        >
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <Card className="p-0">
        {isLoading ? (
          <Spinner />
        ) : !data || data.items.length === 0 ? (
          <p className="py-16 text-center text-sm text-slate-400">No transactions match your filters.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase text-slate-400">
                <th className="px-5 py-3 font-medium">Date</th>
                <th className="px-5 py-3 font-medium">Merchant</th>
                <th className="px-5 py-3 font-medium">Category</th>
                <th className="px-5 py-3 text-right font-medium">Amount</th>
                <th className="px-5 py-3 font-medium">Flags</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((t) => (
                <tr key={t.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                  <td className="whitespace-nowrap px-5 py-3 text-slate-500">{fmtDate(t.date)}</td>
                  <td className="px-5 py-3 font-medium text-slate-700">{t.merchant_normalized}</td>
                  <td className="px-5 py-3"><CategoryBadge category={t.category} /></td>
                  <td className={`px-5 py-3 text-right font-medium ${t.amount < 0 ? "text-green-600" : "text-slate-700"}`}>
                    {t.amount < 0 ? `+${fmtUSD(-t.amount)}` : fmtUSD(t.amount)}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex gap-1.5 text-slate-400">
                      {t.is_recurring && <RefreshCw className="h-4 w-4 text-brand-500" aria-label="recurring" />}
                      {t.is_anomaly && <AlertTriangle className="h-4 w-4 text-amber-500" aria-label="anomaly" />}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {data && data.total > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-slate-500">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-lg border border-slate-300 px-3 py-1.5 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
