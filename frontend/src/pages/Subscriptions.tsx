import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { api } from "../services/api";
import { Card, CategoryBadge, EmptyState, PageHeader, Skeleton } from "../components/ui";
import { capitalize, cn, fmtDate, fmtUSD, titleCase } from "../lib/utils";

type Tab = "subscription" | "bill";

const TABS: { id: Tab; label: string; empty: string }[] = [
  { id: "subscription", label: "Subscriptions", empty: "No subscriptions found. Streaming, gyms, and software show up here once they’ve charged you three times." },
  { id: "bill", label: "Bills", empty: "No recurring bills found. Rent, utilities, and insurance show up here once they repeat." },
];

export default function Subscriptions() {
  const [tab, setTab] = useState<Tab>("subscription");
  const { data, isLoading } = useQuery({
    queryKey: ["subscriptions", tab],
    queryFn: () => api.subscriptions(tab),
  });

  const monthly = (data ?? [])
    .filter((s) => s.frequency === "monthly")
    .reduce((sum, s) => sum + s.amount, 0);
  const current = TABS.find((t) => t.id === tab)!;

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title="Subscriptions" subtitle="Recurring charges, found from their timing and amounts." />

      <div role="tablist" aria-label="Recurring charge type" className="mb-5 inline-flex rounded-xl border border-line bg-card p-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "min-h-10 rounded-lg px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60",
              tab === t.id ? "bg-accent-a/[0.14] text-text" : "text-muted hover:text-text",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-3" aria-busy="true">
          <Skeleton className="h-24" /><Skeleton className="h-20" /><Skeleton className="h-20" />
        </div>
      ) : !data || data.length === 0 ? (
        <EmptyState title={`No ${current.label.toLowerCase()} yet`} message={current.empty} />
      ) : (
        <>
          <Card className="mb-4 p-4 sm:p-5">
            <dl className="grid grid-cols-3 gap-3">
              {[
                ["Active", String(data.length)],
                ["Per month", fmtUSD(monthly)],
                ["Per year", fmtUSD(monthly * 12)],
              ].map(([k, v]) => (
                <div key={k} className="flex min-w-0 flex-col-reverse">
                  <dt className="mt-0.5 text-sm text-muted">{k}</dt>
                  <dd className="num truncate text-[clamp(1.05rem,5vw,1.5rem)] font-bold text-text">{v}</dd>
                </div>
              ))}
            </dl>
          </Card>

          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {data.map((s) => (
              <li key={s.id}>
                <Card className="flex items-center justify-between gap-4 p-4">
                  <div className="min-w-0">
                    <p className="flex items-center gap-2 font-medium text-text">
                      <RefreshCw className="h-4 w-4 shrink-0 text-accent-a" aria-hidden />
                      <span className="truncate">{titleCase(s.merchant_normalized)}</span>
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
                      <CategoryBadge category={s.category} />
                      <span>{capitalize(s.frequency)}, last charged {fmtDate(s.last_charged)}</span>
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="num text-lg font-semibold text-text">{fmtUSD(s.amount)}</p>
                    <p className="text-xs text-muted">{s.occurrence_count} charges</p>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
