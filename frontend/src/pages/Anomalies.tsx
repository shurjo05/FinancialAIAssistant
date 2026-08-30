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
            <Card
              key={a.id}
              className={severe ? "border-red-200 bg-red-50" : "border-amber-200 bg-amber-50"}
            >
              <div className="flex items-start gap-3">
                <AlertTriangle className={`mt-0.5 h-5 w-5 ${severe ? "text-red-500" : "text-amber-500"}`} />
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-700">{a.description}</p>
                  <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                    <CategoryBadge category={a.category} />
                    <span className="capitalize">{a.anomaly_type.replace("_", " ")}</span>
                    {a.z_score != null && <span>· z-score {a.z_score.toFixed(1)}</span>}
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
