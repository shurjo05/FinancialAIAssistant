import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Cell, Tooltip,
} from "recharts";
import { api } from "../services/api";
import { Card, Spinner, NoData, PageHeader } from "../components/ui";
import { fmtUSD, colorFor } from "../lib/utils";

export default function Categories() {
  const { data, isLoading } = useQuery({ queryKey: ["byCategory"], queryFn: api.byCategory });

  if (isLoading) return <Spinner />;
  const entries = Object.entries(data?.by_category ?? {});
  if (entries.length === 0) return <NoData />;

  const total = entries.reduce((sum, [, v]) => sum + v, 0);
  const rows = entries
    .map(([name, value]) => ({ name, value, pct: (value / total) * 100 }))
    .sort((a, b) => b.value - a.value);

  return (
    <div>
      <PageHeader title="Categories" subtitle={`${fmtUSD(total)} total spending`} />

      <Card>
        <ResponsiveContainer width="100%" height={Math.max(240, rows.length * 38)}>
          <BarChart data={rows} layout="vertical" margin={{ left: 24 }}>
            <XAxis type="number" tickFormatter={(v) => `$${v / 1000}k`} fontSize={12} />
            <YAxis type="category" dataKey="name" width={90} fontSize={12} tickFormatter={(v) => v} />
            <Tooltip formatter={(v) => fmtUSD(Number(v))} cursor={{ fill: "#f1f5f9" }} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {rows.map((r) => <Cell key={r.name} fill={colorFor(r.name)} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-3">
        {rows.map((r) => (
          <Card key={r.name} className="flex items-center justify-between">
            <div>
              <p className="font-medium capitalize text-slate-700">{r.name}</p>
              <p className="text-xs text-slate-400">{r.pct.toFixed(1)}% of spending</p>
            </div>
            <p className="font-semibold" style={{ color: colorFor(r.name) }}>{fmtUSD(r.value)}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
