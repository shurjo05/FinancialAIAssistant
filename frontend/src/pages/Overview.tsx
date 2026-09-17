import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer, PieChart, Pie, Cell, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
} from "recharts";
import { api } from "../services/api";
import { Card, StatCard, Spinner, NoData, PageHeader } from "../components/ui";
import { fmtUSD, colorFor } from "../lib/utils";

const INCOME = "#22c55e";
const SPENDING = "#8b5cf6";

const tooltipStyle = {
  background: "rgb(var(--card))",
  border: "1px solid rgb(var(--line))",
  borderRadius: 12,
  color: "rgb(var(--text))",
  fontSize: 13,
};

export default function Overview() {
  const summary = useQuery({ queryKey: ["summary"], queryFn: api.summary });
  const byCat = useQuery({ queryKey: ["byCategory"], queryFn: api.byCategory });
  const monthly = useQuery({ queryKey: ["monthly"], queryFn: api.monthly });

  if (summary.isLoading) return <Spinner label="Loading your dashboard…" />;
  if (!summary.data || summary.data.transaction_count === 0) return <NoData />;

  const s = summary.data;
  const pieData = Object.entries(byCat.data?.by_category ?? {}).map(([name, value]) => ({ name, value }));

  return (
    <div>
      <PageHeader
        title="Overview"
        subtitle={s.date_range.start ? `${s.date_range.start} → ${s.date_range.end}` : undefined}
      />

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatCard label="Total spending" value={fmtUSD(s.total_spending)} />
        <StatCard label="Total income" value={fmtUSD(s.total_income)} tone="up" />
        <StatCard label="Net" value={fmtUSD(s.net)} tone={s.net >= 0 ? "up" : "down"} hero />
        <StatCard label="Savings rate" value={`${s.savings_rate}%`} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="p-5 text-faint">
          <h3 className="mb-2 font-display font-semibold text-muted">Spending by category</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={100} paddingAngle={2} isAnimationActive={false}>
                {pieData.map((d) => <Cell key={d.name} fill={colorFor(d.name)} stroke="rgb(var(--card))" />)}
              </Pie>
              <Tooltip formatter={(v) => fmtUSD(Number(v))} contentStyle={tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5 text-faint">
          <h3 className="mb-2 font-display font-semibold text-muted">Monthly trend</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={monthly.data ?? []}>
              <CartesianGrid stroke="currentColor" strokeOpacity={0.15} vertical={false} />
              <XAxis dataKey="month" fontSize={12} tick={{ fill: "currentColor" }} axisLine={false} tickLine={false} />
              <YAxis fontSize={12} tickFormatter={(v) => `$${v / 1000}k`} tick={{ fill: "currentColor" }} axisLine={false} tickLine={false} />
              <Tooltip formatter={(v) => fmtUSD(Number(v))} cursor={{ fill: "rgb(var(--text) / 0.04)" }} contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ color: "rgb(var(--muted))", fontSize: 12 }} />
              <Bar dataKey="income" fill={INCOME} radius={[4, 4, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="spending" fill={SPENDING} radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          label="Top merchant"
          value={s.top_merchant?.merchant ?? "—"}
          sub={s.top_merchant ? fmtUSD(s.top_merchant.total) : undefined}
        />
        <StatCard
          label="Largest transaction"
          value={s.largest_transaction ? fmtUSD(s.largest_transaction.amount) : "—"}
          sub={s.largest_transaction?.merchant}
        />
        <StatCard
          label="Flags"
          value={`${s.anomaly_count} anomalies`}
          sub={`${s.subscription_count} subscriptions · ${s.bill_count} bills`}
        />
      </div>
    </div>
  );
}
