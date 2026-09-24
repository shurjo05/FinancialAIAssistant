import { useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ChevronLeft, ChevronRight, RefreshCw, Search } from "lucide-react";
import { api } from "../services/api";
import { Card, EmptyState, PageHeader, Skeleton } from "../components/ui";
import { capitalize, cn, CATEGORY_COLORS, fmtDate, fmtUSD, titleCase } from "../lib/utils";
import type { Transaction } from "../types";

const PAGE_SIZE = 25;
const CATEGORIES = Object.keys(CATEGORY_COLORS);
const LOW_CONFIDENCE = 0.5;

const control =
  "min-h-11 rounded-xl border border-line bg-card px-3 text-base text-text focus:border-accent-a focus:outline-none focus:ring-2 focus:ring-accent-a/25 sm:text-sm";

function Amount({ t, className }: { t: Transaction; className?: string }) {
  const incoming = t.amount < 0;
  return (
    <span className={cn("num font-semibold", incoming ? "text-up" : "text-text", className)}>
      {incoming ? `+${fmtUSD(-t.amount)}` : fmtUSD(t.amount)}
    </span>
  );
}

function Flags({ t }: { t: Transaction }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      {t.is_recurring && (
        <span title="Recurring payment" className="inline-flex">
          <RefreshCw className="h-4 w-4 text-accent-a" aria-label="Recurring payment" />
        </span>
      )}
      {t.is_anomaly && (
        <span title="Flagged as unusual" className="inline-flex">
          <AlertTriangle className="h-4 w-4 text-warn" aria-label="Flagged as unusual" />
        </span>
      )}
    </span>
  );
}

/** Correcting a category records a training signal for the model. */
function CategorySelect({ t, onChange }: { t: Transaction; onChange: (cat: string) => void }) {
  const unsure = t.category_confidence < LOW_CONFIDENCE;
  return (
    <span className="inline-flex items-center gap-2">
      <select
        value={t.category}
        onChange={(e) => onChange(e.target.value)}
        aria-label={`Category for ${titleCase(t.merchant_normalized)}`}
        className={cn(
          "min-h-9 rounded-lg border bg-card px-2 text-sm text-text focus:border-accent-a focus:outline-none focus:ring-2 focus:ring-accent-a/25",
          unsure ? "border-warn/60" : "border-line",
        )}
      >
        {CATEGORIES.map((c) => <option key={c} value={c}>{capitalize(c)}</option>)}
      </select>
      {unsure && <span className="text-xs font-medium text-warn">Check this</span>}
    </span>
  );
}

export default function Transactions() {
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [needsReview, setNeedsReview] = useState(false);

  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["transactions", page, category, search, needsReview],
    queryFn: () =>
      api.transactions({
        page, page_size: PAGE_SIZE, category, search,
        low_confidence: needsReview || undefined,
      }),
    placeholderData: keepPreviousData,
  });

  const correctCategory = useMutation({
    mutationFn: ({ id, cat }: { id: number; cat: string }) => api.updateCategory(id, cat),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["transactions"] }),
  });
  const setCat = (t: Transaction) => (cat: string) => correctCategory.mutate({ id: t.id, cat });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const filtered = Boolean(search || category || needsReview);

  return (
    <div>
      <PageHeader title="Transactions" subtitle={data ? `${data.total} ${filtered ? "matching" : "in total"}` : undefined} />

      <div className="mb-4 grid grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:gap-3">
        <label className="relative col-span-2 sm:w-72">
          <span className="sr-only">Search merchants</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
          <input
            type="search"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search merchants"
            className={cn(control, "w-full pl-9 placeholder:text-muted")}
          />
        </label>
        <label className="min-w-0">
          <span className="sr-only">Filter by category</span>
          <select
            value={category}
            onChange={(e) => { setCategory(e.target.value); setPage(1); }}
            className={cn(control, "w-full")}
          >
            <option value="">All categories</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{capitalize(c)}</option>)}
          </select>
        </label>
        <button
          onClick={() => { setNeedsReview((v) => !v); setPage(1); }}
          aria-pressed={needsReview}
          title="Show transactions the model was less than 50% sure about"
          className={cn(
            "min-h-11 rounded-xl border px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60",
            needsReview ? "border-warn/60 bg-warn/10 text-warn" : "border-line bg-card text-muted hover:text-text",
          )}
        >
          Needs review
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-2" aria-busy="true">
          {Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-16" />)}
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title={filtered ? "Nothing matches" : "No transactions yet"}
          message={filtered ? "Try a different search or category, or turn off Needs review." : "Upload a CSV or connect a bank to get started."}
        />
      ) : (
        <>
          {/* Phones: one card per transaction */}
          <ul className="space-y-2 md:hidden">
            {data.items.map((t) => (
              <li key={t.id}>
                <Card className="p-3.5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-text">{titleCase(t.merchant_normalized)}</p>
                      <p className="mt-0.5 flex items-center gap-2 text-xs text-muted">
                        {fmtDate(t.date)} <Flags t={t} />
                      </p>
                    </div>
                    <Amount t={t} className="shrink-0 text-base" />
                  </div>
                  <div className="mt-2.5">
                    <CategorySelect t={t} onChange={setCat(t)} />
                  </div>
                </Card>
              </li>
            ))}
          </ul>

          {/* Wider screens: a table */}
          <Card className="hidden overflow-hidden p-0 md:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs text-muted">
                  <th className="px-5 py-3 font-medium">Date</th>
                  <th className="px-5 py-3 font-medium">Merchant</th>
                  <th className="px-5 py-3 font-medium">Category</th>
                  <th className="px-5 py-3 text-right font-medium">Amount</th>
                  <th className="px-5 py-3 font-medium"><span className="sr-only">Flags</span></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((t) => (
                  <tr key={t.id} className="border-b border-line-soft last:border-0 hover:bg-line-soft/60">
                    <td className="whitespace-nowrap px-5 py-2.5 text-muted">{fmtDate(t.date)}</td>
                    <td className="px-5 py-2.5 font-medium text-text">{titleCase(t.merchant_normalized)}</td>
                    <td className="px-5 py-2.5"><CategorySelect t={t} onChange={setCat(t)} /></td>
                    <td className="px-5 py-2.5 text-right"><Amount t={t} /></td>
                    <td className="px-5 py-2.5"><Flags t={t} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}

      {data && data.total > PAGE_SIZE && (
        <nav aria-label="Pages" className="mt-4 flex items-center justify-between gap-3 text-sm">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="inline-flex min-h-11 items-center gap-1 rounded-xl border border-line bg-card px-3 font-medium text-text disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60"
          >
            <ChevronLeft className="h-4 w-4" /> Previous
          </button>
          <span className="text-muted">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="inline-flex min-h-11 items-center gap-1 rounded-xl border border-line bg-card px-3 font-medium text-text disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60"
          >
            Next <ChevronRight className="h-4 w-4" />
          </button>
        </nav>
      )}
    </div>
  );
}
