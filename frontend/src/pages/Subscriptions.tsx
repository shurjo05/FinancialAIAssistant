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

      <div className="mb-4 inline-flex rounded-lg border border-slate-200 bg-white p-1">
        {(["subscription", "bill"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "rounded-md px-4 py-1.5 text-sm font-medium capitalize transition-colors",
              tab === t ? "bg-brand-600 text-white" : "text-slate-500 hover:text-slate-700",
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
          <Card className="mb-4 bg-brand-50">
            <p className="text-sm text-slate-600">
              <b>{data.length}</b> {tab === "subscription" ? "subscriptions" : "bills"} ·{" "}
              <b>{fmtUSD(monthly)}</b>/month · <b>{fmtUSD(monthly * 12)}</b>/year
            </p>
          </Card>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {data.map((s) => (
              <Card key={s.id} className="flex items-center justify-between">
                <div>
                  <p className="flex items-center gap-2 font-medium text-slate-700">
                    <RefreshCw className="h-4 w-4 text-brand-500" />
                    {s.merchant_normalized}
                  </p>
                  <p className="mt-1 flex items-center gap-2 text-xs text-slate-400">
                    <CategoryBadge category={s.category} />
                    {s.frequency} · last {fmtDate(s.last_charged)}
                  </p>
                </div>
                <p className="font-semibold text-slate-700">{fmtUSD(s.amount)}</p>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
