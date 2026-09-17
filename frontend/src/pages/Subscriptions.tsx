import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { api } from "../services/api";
import { Card, CategoryBadge, Spinner, NoData, PageHeader } from "../components/ui";
import { fmtUSD, fmtDate, cn } from "../lib/utils";

type Tab = "subscription" | "bill";

export default function Subscriptions() {
  const [tab, setTab] = useState<Tab>("subscription");
  const { data, isLoading } = useQuery({
    queryKey: ["subscriptions", tab],
    queryFn: () => api.subscriptions(tab),
  });

  const monthly = (data ?? [])
    .filter((s) => s.frequency === "monthly")
    .reduce((sum, s) => sum + s.amount, 0);

  return (
    <div>
      <PageHeader
        title="Recurring"
        subtitle="Subscriptions (streaming, gym) separated from bills (rent, utilities)."
      />

      <div className="mb-5 inline-flex rounded-xl border border-line bg-card p-1">
        {(["subscription", "bill"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "rounded-lg px-4 py-1.5 text-sm font-medium transition-colors",
              tab === t ? "grad text-white shadow-pop" : "text-muted hover:text-text",
            )}
          >
            {t === "subscription" ? "Subscriptions" : "Recurring bills"}
          </button>
        ))}
      </div>

      {isLoading ? (
        <Spinner />
      ) : !data || data.length === 0 ? (
        <NoData />
      ) : (
        <>
          <Card className="mb-5 p-4">
            <p className="text-sm text-muted">
              <b className="num text-text">{data.length}</b> {tab === "subscription" ? "subscriptions" : "bills"}
              {" · "}<b className="num text-text">{fmtUSD(monthly)}</b>/month
              {" · "}<b className="num text-text">{fmtUSD(monthly * 12)}</b>/year
            </p>
          </Card>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {data.map((s) => (
              <Card key={s.id} className="flex items-center justify-between gap-4 p-4">
                <div className="min-w-0">
                  <p className="flex items-center gap-2 font-medium text-text">
                    <RefreshCw className="h-4 w-4 shrink-0 text-accent-a" />
                    <span className="truncate">{s.merchant_normalized}</span>
                  </p>
                  <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
                    <CategoryBadge category={s.category} />
                    <span>{s.frequency} · last {fmtDate(s.last_charged)}</span>
                  </p>
                </div>
                <p className="num shrink-0 text-lg font-semibold text-text">{fmtUSD(s.amount)}</p>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
