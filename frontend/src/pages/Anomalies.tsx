import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { api } from "../services/api";
import { Card, CategoryBadge, EmptyState, PageHeader, Skeleton } from "../components/ui";
import { cn } from "../lib/utils";

// The detector's description ends with "(z-score N)"; we explain that in words instead.
const stripZ = (d: string) => d.replace(/\s*\(z-score [^)]*\)\s*$/, "");

const TYPE_LABEL: Record<string, string> = {
  large_single: "Unusually large charge",
  spike: "Higher than usual",
};

export default function Anomalies() {
  const { data, isLoading } = useQuery({ queryKey: ["anomalies"], queryFn: api.anomalies });

  const intro = (
    <p className="mb-5 max-w-[65ch] text-sm leading-relaxed text-muted">
      An IsolationForest looks for charges that don’t fit your pattern, skipping income, transfers, and
      rent, and only flags spending that’s unusually high.{" "}
      <Link to="/how-it-works" className="font-medium text-accent-ink hover:underline">How it works</Link>
    </p>
  );

  if (isLoading) {
    return (
      <div aria-busy="true">
        <Skeleton className="h-8 w-40" />
        <div className="mt-6 space-y-3"><Skeleton className="h-24" /><Skeleton className="h-24" /></div>
      </div>
    );
  }

  if (!data || data.length === 0)
    return (
      <div className="mx-auto max-w-3xl">
        <PageHeader title="Anomalies" />
        {intro}
        <EmptyState title="Nothing unusual" message="No charge stood out from your normal spending." />
      </div>
    );

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="Anomalies" subtitle={`${data.length} unusual ${data.length === 1 ? "charge" : "charges"} flagged`} />
      {intro}
      <ul className="space-y-3">
        {data.map((a) => {
          const z = a.z_score ?? 0;
          const severe = z >= 3;
          return (
            <li key={a.id}>
              <Card className="flex items-start gap-3 p-4">
                <span
                  className={cn(
                    "grid h-10 w-10 shrink-0 place-items-center rounded-xl",
                    severe ? "bg-down/10 text-down" : "bg-warn/10 text-warn",
                  )}
                >
                  <AlertTriangle className="h-5 w-5" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-text">{TYPE_LABEL[a.anomaly_type] ?? "Unusual charge"}</p>
                  <p className="mt-0.5 text-[15px] leading-relaxed text-text">{stripZ(a.description)}.</p>
                  <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
                    <CategoryBadge category={a.category} />
                    {a.z_score != null && (
                      <span>{z.toFixed(1)} standard deviations above your typical {a.category} charge</span>
                    )}
                  </div>
                </div>
              </Card>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
