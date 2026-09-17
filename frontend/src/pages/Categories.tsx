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

      <Card className="p-4 text-muted">
        <ResponsiveContainer width="100%" height={Math.max(240, rows.length * 40)}>
          <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
            <XAxis
              type="number"
              tickFormatter={(v) => `$${v / 1000}k`}
              fontSize={12}
              tick={{ fill: "currentColor" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={92}
              fontSize={12}
              tick={{ fill: "currentColor" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              formatter={(v) => fmtUSD(Number(v))}
              cursor={{ fill: "rgb(var(--text) / 0.04)" }}
              contentStyle={{
                background: "rgb(var(--card))",
                border: "1px solid rgb(var(--line))",
                borderRadius: 12,
                color: "rgb(var(--text))",
                fontSize: 13,
              }}
              labelStyle={{ color: "rgb(var(--text))" }}
            />
            <Bar dataKey="value" radius={[0, 6, 6, 0]} isAnimationActive={false}>
              {rows.map((r) => <Cell key={r.name} fill={colorFor(r.name)} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map((r) => (
          <Card key={r.name} className="flex items-center justify-between gap-3 p-4">
            <div className="min-w-0">
              <p className="truncate font-medium capitalize text-text">{r.name}</p>
              <p className="mt-0.5 text-xs text-faint">{r.pct.toFixed(1)}% of spending</p>
            </div>
            <p className="num shrink-0 text-lg font-semibold" style={{ color: colorFor(r.name) }}>
              {fmtUSD(r.value)}
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}
