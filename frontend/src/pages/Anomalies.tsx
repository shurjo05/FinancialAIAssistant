import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { api } from "../services/api";
import { Card, CategoryBadge, Spinner, EmptyState, PageHeader } from "../components/ui";

export default function Anomalies() {
  const { data, isLoading } = useQuery({ queryKey: ["anomalies"], queryFn: api.anomalies });

  if (isLoading) return <Spinner />;
  if (!data || data.length === 0)
    return (
      <div>
        <PageHeader title="Anomalies" />
        <EmptyState title="No anomalies found" message="Nothing unusual in your spending — nice." />
      </div>
    );

  return (
    <div>
      <PageHeader title="Anomalies" subtitle={`${data.length} unusual transactions flagged`} />
      <div className="space-y-3">
        {data.map((a) => {
          const severe = (a.z_score ?? 0) >= 3;
          return (
            <Card key={a.id} className="flex items-start gap-3 p-4">
              {/* Severity stripe — red for extreme, amber otherwise */}
              <span className={`mt-0.5 h-9 w-1 shrink-0 rounded-full ${severe ? "bg-down" : "bg-amber-400"}`} />
              <AlertTriangle className={`mt-0.5 h-5 w-5 shrink-0 ${severe ? "text-down" : "text-amber-400"}`} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-text">{a.description}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
                  <CategoryBadge category={a.category} />
                  <span className="capitalize">{a.anomaly_type.replace("_", " ")}</span>
                  {a.z_score != null && <span>· z-score {a.z_score.toFixed(1)}</span>}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
